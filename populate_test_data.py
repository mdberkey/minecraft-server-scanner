from datetime import datetime, timedelta
import random

from app.db.models import MinecraftServer, get_engine, get_session, Base


def populate_test_data(db_path='servers.db', count=50):
    engine = get_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    session = get_session(engine)

    session.query(MinecraftServer).delete()
    session.commit()
    
    sample_data = []

    versions = ['1.20.4', '1.20.2', '1.20.1', '1.19.4', '1.19.2', '1.18.2', '1.16.5 Forge', '1.12.2 Forge', '1.8.9']
    modded_versions = ['1.20.1 Forge', '1.19.2 Fabric', '1.16.5 Forge', '1.12.2 Forge']

    for i in range(count):
        if i < len(sample_data):
            data = sample_data[i]
        else:
            data = {
                'ip': f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}',
                'port': random.choice([25565, 25566, 25567, 25568]),
                'motd': f'Minecraft Server #{i+1}',
                'version': random.choice(versions),
                'players': random.randint(0, 500),
                'is_modded': random.random() < 0.2,
                'whitelist': random.choice(['Unknown', 'Unknown', 'Unknown', 'Yes', 'No']),
            }
        
        if data.get('is_modded'):
            data['version'] = random.choice(modded_versions)
        
        existing = session.query(MinecraftServer).filter_by(ip=data['ip'], port=data['port']).first()
        if not existing:
            players_min = random.randint(0, min(10, data['players']))
            players_max = random.randint(data['players'], data['players'] + 100)

            server = MinecraftServer(
                ip=data['ip'],
                port=data['port'],
                motd=data['motd'],
                version=data['version'],
                players_online=data['players'],
                players_min_ever=players_min,
                players_max_ever=players_max,
                is_modded=data['is_modded'],
                whitelist=data['whitelist'],
                date_added=datetime.now() - timedelta(days=random.randint(1, 30)),
                last_updated=datetime.now(),
            )
            session.add(server)
            print(f"Added: {data['ip']}:{data['port']}")
    
    session.commit()
    session.close()
    print(f"\nInserted {count} test servers into {db_path}")

if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    populate_test_data(count=count)
