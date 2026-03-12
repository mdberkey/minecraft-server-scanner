import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models import MinecraftServer, get_engine, get_session
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
        from app.db.models import Base
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
        session = get_session(self.engine)

        for data in servers_data:
            existing = session.query(MinecraftServer).filter_by(
                ip=data['ip'], port=data['port']
            ).first()

            if existing:
                existing.favicon = data['favicon']
                existing.motd = data['motd']
                existing.version = data['version']
                existing.is_modded = data['is_modded']
                existing.players_online = data['players_online']

                if data['players_online'] > existing.players_max_ever:
                    existing.players_max_ever = data['players_online']
                
                # Update players_min_ever:
                # - If new value is lower than current min, update
                # - If min is 0, keep it (0 is the lowest possible player count)
                if existing.players_min_ever != 0 and data['players_online'] < existing.players_min_ever:
                    existing.players_min_ever = data['players_online']

                existing.last_updated = datetime.now(timezone.utc)
            else:
                server = MinecraftServer(
                    ip=data['ip'],
                    port=data['port'],
                    favicon=data['favicon'],
                    whitelist='Unknown',
                    motd=data['motd'],
                    version=data['version'],
                    is_modded=data['is_modded'],
                    players_online=data['players_online'],
                    players_max_ever=data['players_online'],  # Initialize with first observed
                    players_min_ever=data['players_online'],  # Initialize with first observed
                    date_added=datetime.now(timezone.utc)
                )
                session.add(server)

        session.commit()
        session.close()
        print(f"Saved {len(servers_data)} servers to database")
