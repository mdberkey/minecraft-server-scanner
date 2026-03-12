import os
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.models import MinecraftServer, get_engine, get_session, Base
from app.scanner.masscan_runner import MasscanRunner


class ScannerService:
    def __init__(self, db_path='servers.db', masscan_path='masscan/bin/masscan',
                 exclude_file='masscan/data/exclude.conf', scan_output='scan_results.json',
                 scan_rate=20000):
        self.db_path = db_path
        self.masscan_path = masscan_path
        self.exclude_file = exclude_file
        self.scan_output = scan_output
        self.scan_rate = scan_rate

        self.engine = get_engine(db_path)
        Base.metadata.create_all(self.engine)

    def run_full_scan(self):
        runner = MasscanRunner(self.masscan_path, self.exclude_file, self.scan_output, self.scan_rate)

        if not runner.run_scan():
            print("Scan failed!")
            return

        results = runner.parse_results()
        print(f"Found {len(results)} Minecraft servers with valid status responses")
        self._save_to_database(results)

    def _save_to_database(self, servers_data):
        if not servers_data:
            return

        engine = get_engine(self.db_path)
        Base.metadata.create_all(engine)
        session = get_session(engine)

        # Optimize SQLite for bulk insert
        session.execute(text("PRAGMA journal_mode=WAL"))
        session.execute(text("PRAGMA synchronous=NORMAL"))
        session.execute(text("PRAGMA temp_store=MEMORY"))
        session.execute(text("PRAGMA busy_timeout=5000"))

        # Bulk fetch existing servers by IP
        existing_servers = session.query(MinecraftServer).filter(
            MinecraftServer.ip.in_({d['ip'] for d in servers_data})
        ).all()
        existing_keys = {(s.ip, s.port): s for s in existing_servers}

        servers_to_insert = []
        servers_to_update = []

        for data in servers_data:
            key = (data['ip'], data['port'])
            if key in existing_keys:
                servers_to_update.append((data, existing_keys[key]))
            else:
                servers_to_insert.append(data)

        # Bulk insert new servers
        if servers_to_insert:
            session.bulk_insert_mappings(MinecraftServer, [
                {
                    'ip': d['ip'],
                    'port': d['port'],
                    'favicon': d['favicon'],
                    'whitelist': 'Unknown',
                    'motd': d['motd'],
                    'version': d['version'],
                    'is_modded': d['is_modded'],
                    'players_online': d['players_online'],
                    'players_max_ever': d['players_online'],
                    'players_min_ever': d['players_online'],
                    'date_added': datetime.now(timezone.utc),
                    'last_updated': datetime.now(timezone.utc),
                }
                for d in servers_to_insert
            ])

        # Update existing servers
        for data, existing in servers_to_update:
            existing.favicon = data['favicon']
            existing.motd = data['motd']
            existing.version = data['version']
            existing.is_modded = data['is_modded']
            existing.players_online = data['players_online']

            if data['players_online'] > existing.players_max_ever:
                existing.players_max_ever = data['players_online']

            if existing.players_min_ever != 0 and data['players_online'] < existing.players_min_ever:
                existing.players_min_ever = data['players_online']

            existing.last_updated = datetime.now(timezone.utc)

        session.commit()
        session.close()
        print(f"Saved {len(servers_data)} servers to database")
