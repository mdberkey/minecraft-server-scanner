import os
import sqlite3
from datetime import datetime, timezone
import orjson


def get_config():
    return {
        'db_path': os.environ.get('DB_PATH', 'servers.db'),
        'scan_output': os.environ.get('SCAN_OUTPUT', 'scan_results.ndjson'),
        'batch_size': int(os.environ.get('BATCH_SIZE', '5000')),
    }


def parse_chat(chat_obj):
    if isinstance(chat_obj, str):
        return chat_obj
    if not isinstance(chat_obj, dict):
        return str(chat_obj) if chat_obj is not None else ''

    text = str(chat_obj.get('text', '') or '')
    for item in chat_obj.get('extra', []):
        text += parse_chat(item)
    return text


def parse_banner(banner_str):
    try:
        res = orjson.loads(banner_str)
    except orjson.JSONDecodeError:
        return None

    if not isinstance(res, dict) or 'description' not in res:
        return None

    desc = res['description']
    if desc is None:
        return None

    motd = parse_chat(desc) if isinstance(desc, (dict, list)) else str(desc)
    ver = res.get('version', {})
    v_name = str(ver.get('name', 'Unknown'))

    is_modded = any(kw in v_name.lower() for kw in ('forge', 'fabric', 'mod'))
    if res.get('modinfo', {}).get('type') == 'FML':
        is_modded = True

    players = res.get('players', {})

    return {
        'motd': motd,
        'version': v_name,
        'is_modded': 1 if is_modded else 0,
        'players_online': players.get('online', 0) or 0,
        'players_max': players.get('max', 0) or 0,
        'favicon': res.get('favicon'),
    }


def extract_records(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in ('#', '[', ']', ','):
                continue
            try:
                server = orjson.loads(line.rstrip(','))
                ports = server.get('ports', [])
                if not ports:
                    continue

                port = ports[0].get('port', 25565)
                banner = ports[0].get('service', {}).get('banner')
                if banner:
                    yield (server['ip'], port, banner)
            except (orjson.JSONDecodeError, IndexError):
                continue


def import_to_db(config):
    db_path = config['db_path']
    log_path = config['scan_output']

    if not os.path.exists(log_path):
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            ip TEXT PRIMARY KEY,
            port INTEGER DEFAULT 25565,
            json TEXT,
            motd TEXT,
            version TEXT,
            is_modded INTEGER,
            players_online INTEGER,
            players_max INTEGER,
            players_min_ever INTEGER DEFAULT 0,
            players_max_ever INTEGER DEFAULT 0,
            favicon TEXT,
            whitelist TEXT,
            last_updated TEXT,
            date_added TEXT
        )
    """)

    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA temp_store=MEMORY")

    upsert_sql = """
        INSERT INTO servers (ip, port, json, motd, version, is_modded, players_online, players_max, players_min_ever, players_max_ever, favicon, whitelist, last_updated, date_added)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ip) DO UPDATE SET
            port=excluded.port, json=excluded.json, motd=excluded.motd, version=excluded.version,
            is_modded=excluded.is_modded, players_online=excluded.players_online,
            players_max=excluded.players_max, players_min_ever=excluded.players_min_ever,
            players_max_ever=excluded.players_max_ever, favicon=excluded.favicon,
            whitelist=excluded.whitelist, last_updated=excluded.last_updated
    """

    batch = []
    count = 0
    batch_time = datetime.now(timezone.utc).isoformat()
    for ip, port, banner_str in extract_records(log_path):
        p = parse_banner(banner_str)
        if not p:
            continue

        whitelist = 'Unknown'

        batch.append((
            ip, port, banner_str, p['motd'], p['version'], p['is_modded'],
            p['players_online'], p['players_max'], p['players_online'], p['players_max'],
            p['favicon'], whitelist, batch_time, batch_time
        ))
        count += 1

        if len(batch) >= config['batch_size']:
            cur.executemany(upsert_sql, batch)
            conn.commit()
            batch = []

    if batch:
        cur.executemany(upsert_sql, batch)
        conn.commit()

    conn.close()
    return count


if __name__ == '__main__':
    import_to_db(get_config())
