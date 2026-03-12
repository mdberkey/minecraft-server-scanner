"""Integration tests for scanner service and database."""
import unittest
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scanner.scanner_service import ScannerService
from app.db.models import MinecraftServer, get_engine, get_session, Base


class TestScannerService(unittest.TestCase):
    
    def setUp(self):
        # Create temp database with unique name
        self.db_path = os.path.join(tempfile.gettempdir(), f'test_scanner_{uuid.uuid4().hex}.db')
        
        self.scanner = ScannerService(
            db_path=self.db_path,
            masscan_path='masscan',
            exclude_file='exclude.conf',
            scan_output='test_scan.json',
            scan_rate=20000
        )
    
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_database_initialization(self):
        """Test that database tables are created."""
        engine = get_engine(self.db_path)
        session = get_session(engine)
        
        # Check table exists using SQLAlchemy reflection
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        self.assertIn('minecraft_servers', tables)
        session.close()
    
    def test_save_to_database_new_server(self):
        """Test saving a new server to database."""
        server_data = [{
            'ip': '192.168.1.100',
            'port': 25565,
            'favicon': 'data:image/png;base64,test',
            'whitelist': 'Unknown',
            'motd': 'Test Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 50,
            'players_max': 100,
        }]
        
        self.scanner._save_to_database(server_data)
        
        # Verify
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='192.168.1.100').first()
        
        self.assertIsNotNone(server)
        self.assertEqual(server.motd, 'Test Server')
        self.assertEqual(server.version, '1.20.4')
        self.assertEqual(server.players_online, 50)
        self.assertEqual(server.whitelist, 'Unknown')
        self.assertFalse(server.is_modded)
        session.close()
    
    def test_save_to_database_update_existing(self):
        """Test updating an existing server (whitelist should NOT change)."""
        # First save
        server_data = [{
            'ip': '10.0.0.1',
            'port': 25565,
            'favicon': 'icon1',
            'whitelist': 'Unknown',
            'motd': 'Original MOTD',
            'version': '1.20.1',
            'is_modded': False,
            'players_online': 10,
            'players_max': 50,
        }]
        self.scanner._save_to_database(server_data)
        
        # Set whitelist to Yes manually
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='10.0.0.1').first()
        server.whitelist = 'Yes'
        session.commit()
        session.close()
        
        # Second save (update)
        server_data = [{
            'ip': '10.0.0.1',
            'port': 25565,
            'favicon': 'icon2',
            'whitelist': 'Unknown',  # Should NOT update
            'motd': 'Updated MOTD',
            'version': '1.20.4',
            'is_modded': True,  # Should update
            'players_online': 25,
            'players_max': 60,
        }]
        self.scanner._save_to_database(server_data)
        
        # Verify whitelist unchanged, other fields updated
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='10.0.0.1').first()
        
        self.assertEqual(server.whitelist, 'Yes')  # Unchanged
        self.assertEqual(server.motd, 'Updated MOTD')  # Updated
        self.assertEqual(server.version, '1.20.4')  # Updated
        self.assertTrue(server.is_modded)  # Updated
        self.assertEqual(server.players_online, 25)  # Updated
        session.close()
    
    def test_save_to_database_players_ever_tracking(self):
        """Test that players_max_ever and players_min_ever are tracked correctly."""
        # First save
        server_data = [{
            'ip': '172.16.0.1',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 50,
            'players_max': 100,
        }]
        self.scanner._save_to_database(server_data)
        
        # Second save with more players
        server_data = [{
            'ip': '172.16.0.1',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 80,  # More than before
            'players_max': 100,
        }]
        self.scanner._save_to_database(server_data)
        
        # Third save with fewer players
        server_data = [{
            'ip': '172.16.0.1',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 5,  # Less than before
            'players_max': 100,
        }]
        self.scanner._save_to_database(server_data)
        
        # Verify tracking
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='172.16.0.1').first()
        
        self.assertEqual(server.players_max_ever, 80)  # Peak was 80
        self.assertEqual(server.players_min_ever, 5)  # Low was 5
        session.close()
    
    def test_to_dict(self):
        """Test MinecraftServer.to_dict() method."""
        engine = get_engine(self.db_path)
        session = get_session(engine)
        
        server = MinecraftServer(
            ip='1.2.3.4',
            port=25565,
            motd='Test',
            version='1.20.4',
            players_online=10,
            players_max_ever=50,
            players_min_ever=5,
            is_modded=True,
            whitelist='No',
            favicon='data:test',
        )
        session.add(server)
        session.commit()
        
        # Get from DB and test to_dict
        saved = session.query(MinecraftServer).first()
        data = saved.to_dict()
        
        self.assertEqual(data['ip'], '1.2.3.4')
        self.assertEqual(data['port'], 25565)
        self.assertEqual(data['motd'], 'Test')
        self.assertEqual(data['version'], '1.20.4')
        self.assertEqual(data['players_online'], 10)
        self.assertEqual(data['players_max_ever'], 50)
        self.assertEqual(data['players_min_ever'], 5)
        self.assertEqual(data['is_modded'], True)
        self.assertEqual(data['whitelist'], 'No')
        self.assertEqual(data['favicon'], 'data:test')
        self.assertIn('date_added', data)
        self.assertIn('last_updated', data)
        
        session.close()


if __name__ == '__main__':
    unittest.main()
