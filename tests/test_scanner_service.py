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

    # ==================== EDGE CASES ====================

    def test_save_to_database_empty_list(self):
        """Test saving empty server list."""
        self.scanner._save_to_database([])
        # Should not raise any errors
        engine = get_engine(self.db_path)
        session = get_session(engine)
        count = session.query(MinecraftServer).count()
        self.assertEqual(count, 0)
        session.close()

    def test_save_to_database_null_values(self):
        """Test saving server with null/None values."""
        server_data = [{
            'ip': '192.168.1.1',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': None,
            'version': None,
            'is_modded': False,
            'players_online': 0,
            'players_max': 0,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).first()

        self.assertIsNotNone(server)
        self.assertIsNone(server.motd)
        self.assertIsNone(server.version)
        self.assertIsNone(server.favicon)
        session.close()

    def test_save_to_database_empty_strings(self):
        """Test saving server with empty string values."""
        server_data = [{
            'ip': '192.168.1.2',
            'port': 25565,
            'favicon': '',
            'whitelist': 'Unknown',
            'motd': '',
            'version': '',
            'is_modded': False,
            'players_online': 0,
            'players_max': 0,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='192.168.1.2').first()

        self.assertIsNotNone(server)
        self.assertEqual(server.motd, '')
        self.assertEqual(server.version, '')
        session.close()

    def test_save_to_database_very_long_motd(self):
        """Test saving server with very long MOTD (beyond column limit)."""
        long_motd = 'A' * 1000  # Exceeds 512 char limit

        server_data = [{
            'ip': '192.168.1.3',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': long_motd,
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 0,
            'players_max': 20,
        }]

        # Should handle gracefully - either truncate or raise appropriate error
        try:
            self.scanner._save_to_database(server_data)
        except Exception as e:
            # If it fails, it should be a data error, not crash unexpectedly
            self.assertIn('DataError', type(e).__name__)

    def test_save_to_database_very_long_version(self):
        """Test saving server with very long version string."""
        long_version = 'Paper ' + '1.20.' + 'A' * 200

        server_data = [{
            'ip': '192.168.1.4',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Test',
            'version': long_version,
            'is_modded': False,
            'players_online': 0,
            'players_max': 20,
        }]

        try:
            self.scanner._save_to_database(server_data)
        except Exception as e:
            self.assertIn('DataError', type(e).__name__)

    def test_save_to_database_invalid_ip(self):
        """Test saving server with invalid IP format."""
        server_data = [{
            'ip': 'not-an-ip',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Test',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 0,
            'players_max': 20,
        }]

        # Should still save (IP is just a string in DB)
        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='not-an-ip').first()
        self.assertIsNotNone(server)
        session.close()

    def test_save_to_database_ipv6(self):
        """Test saving server with IPv6 address."""
        server_data = [{
            'ip': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'IPv6 Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 5,
            'players_max': 20,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(
            ip='2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        ).first()
        self.assertIsNotNone(server)
        self.assertEqual(server.motd, 'IPv6 Server')
        session.close()

    def test_save_to_database_negative_players(self):
        """Test saving server with negative player count."""
        server_data = [{
            'ip': '192.168.1.5',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Test',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': -5,
            'players_max': 20,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='192.168.1.5').first()
        # Should save but value may be negative or clamped
        self.assertIsNotNone(server)
        session.close()

    def test_save_to_database_very_large_player_count(self):
        """Test saving server with extremely large player count."""
        server_data = [{
            'ip': '192.168.1.6',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Test',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 999999999,
            'players_max': 999999999,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='192.168.1.6').first()
        self.assertIsNotNone(server)
        self.assertEqual(server.players_online, 999999999)
        session.close()

    def test_save_to_database_zero_max_players(self):
        """Test saving server with zero max players."""
        server_data = [{
            'ip': '192.168.1.7',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Test',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 0,
            'players_max': 0,
        }]

        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='192.168.1.7').first()
        self.assertIsNotNone(server)
        session.close()

    def test_players_ever_tracking_zero_initial(self):
        """Test players_min_ever tracking when starting from 0."""
        # First save with 0 players
        server_data = [{
            'ip': '172.16.0.2',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 0,
            'players_max': 20,
        }]
        self.scanner._save_to_database(server_data)

        # Second save with 10 players
        server_data = [{
            'ip': '172.16.0.2',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 10,
            'players_max': 20,
        }]
        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='172.16.0.2').first()

        # players_min_ever should be 0 (the initial value)
        self.assertEqual(server.players_min_ever, 0)
        self.assertEqual(server.players_max_ever, 10)
        session.close()

    def test_players_ever_tracking_same_value(self):
        """Test players_ever tracking with same values."""
        server_data = [{
            'ip': '172.16.0.3',
            'port': 25565,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': 'Server',
            'version': '1.20.4',
            'is_modded': False,
            'players_online': 25,
            'players_max': 50,
        }]
        self.scanner._save_to_database(server_data)

        # Same values again
        self.scanner._save_to_database(server_data)

        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).filter_by(ip='172.16.0.3').first()

        self.assertEqual(server.players_max_ever, 25)
        self.assertEqual(server.players_min_ever, 25)
        session.close()

    def test_to_dict_null_fields(self):
        """Test to_dict with nullable fields set to None (motd, version, favicon)."""
        engine = get_engine(self.db_path)
        session = get_session(engine)

        server = MinecraftServer(
            ip='5.5.5.5',
            port=25565,
            motd=None,
            version=None,
            players_online=0,
            players_max_ever=0,
            players_min_ever=0,
            is_modded=False,
            whitelist='Unknown',
            favicon=None,
            # Note: date_added and last_updated have defaults, so they won't be None
        )
        session.add(server)
        session.commit()

        data = server.to_dict()
        self.assertIsNone(data['motd'])
        self.assertIsNone(data['version'])
        self.assertIsNone(data['favicon'])
        # Dates are auto-populated by SQLAlchemy defaults
        self.assertIsNotNone(data['date_added'])
        self.assertIsNotNone(data['last_updated'])

        session.close()

    def test_scanner_service_initialization_creates_tables(self):
        """Test that ScannerService creates tables on init."""
        new_db_path = os.path.join(tempfile.gettempdir(), f'test_init_{uuid.uuid4().hex}.db')
        try:
            scanner = ScannerService(db_path=new_db_path)

            engine = get_engine(new_db_path)
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            self.assertIn('minecraft_servers', tables)
        finally:
            if os.path.exists(new_db_path):
                os.unlink(new_db_path)


if __name__ == '__main__':
    unittest.main()
