import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models import MinecraftServer, get_engine, get_session
from app.scanner.masscan_runner import MasscanRunner
from app.scanner.minecraft_query import MinecraftQuery


class ScannerService:
    def __init__(self, db_path='servers.db', masscan_path='masscan/bin/masscan',
                 exclude_file='masscan/data/exclude.conf', scan_output='scan_results.json',
                 scan_rate=20000):
        self.db_path = db_path
        self.masscan_path = masscan_path
        self.exclude_file = exclude_file
        self.scan_output = scan_output
        self.scan_rate = scan_rate
        
        self.engine = get_engine(f'sqlite:///{db_path}')
        from app.db.models import Base
        Base.metadata.create_all(self.engine)

    def run_full_scan(self, max_workers=100):
        runner = MasscanRunner(self.masscan_path, self.exclude_file, self.scan_output, self.scan_rate)
        
        if not runner.run_scan():
            print("Scan failed!")
            return
        
        results = runner.parse_results()
        print(f"Found {len(results)} potential servers from masscan")
        
        servers_data = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(MinecraftQuery.ping_server, r['ip'], 25565): r 
                for r in results
            }
            
            for i, future in enumerate(as_completed(future_to_ip)):
                result = future_to_ip[future]
                try:
                    data = future.result()
                    if data:
                        servers_data.append(data)
                        if i % 100 == 0:
                            print(f"Queried {i}/{len(results)} servers...")
                except Exception as e:
                    print(f"Error querying {result['ip']}: {e}")
        
        print(f"Successfully queried {len(servers_data)} servers")
        self._save_to_database(servers_data)

    def _save_to_database(self, servers_data):
        session = get_session(self.engine)
        
        for data in servers_data:
            existing = session.query(MinecraftServer).filter_by(
                ip=data['ip'], port=data['port']
            ).first()
            
            if existing:
                existing.favicon = data['favicon']
                existing.whitelist = data['whitelist']
                existing.motd = data['motd']
                existing.version = data['version']
                existing.is_modded = data['is_modded']
                existing.players_online = data['players_online']
                
                if data['players_online'] > existing.players_max_ever:
                    existing.players_max_ever = data['players_online']
                if existing.players_min_ever == 0 or data['players_online'] < existing.players_min_ever:
                    existing.players_min_ever = data['players_online']
                
                existing.last_updated = datetime.utcnow()
            else:
                server = MinecraftServer(
                    ip=data['ip'],
                    port=data['port'],
                    favicon=data['favicon'],
                    whitelist=data['whitelist'],
                    motd=data['motd'],
                    version=data['version'],
                    is_modded=data['is_modded'],
                    players_online=data['players_online'],
                    players_max_ever=0,
                    players_min_ever=0,
                    date_added=datetime.utcnow()
                )
                session.add(server)
        
        session.commit()
        session.close()
        print(f"Saved {len(servers_data)} servers to database")
