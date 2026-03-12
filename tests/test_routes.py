"""Tests for API routes."""
import unittest
import tempfile
import os
import sys
import json
import uuid
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import create_app
from app.db.models import MinecraftServer, get_engine, get_session, Base


class TestAPIRoutes(unittest.TestCase):
    
    def setUp(self):
        # Create temp database with unique name
        self.db_path = os.path.join(tempfile.gettempdir(), f'test_api_{uuid.uuid4().hex}.db')
        
        # Set environment variable for database path BEFORE creating app
        os.environ['DB_PATH'] = self.db_path
        
        # Initialize database with test data
        engine = get_engine(self.db_path)
        Base.metadata.create_all(engine)
        session = get_session(engine)
        
        # Add test servers
        now = datetime.now(timezone.utc)
        test_servers = [
            MinecraftServer(ip='192.168.1.100', port=25565, motd='Hypixel', version='1.8-1.20', 
                          players_online=50000, is_modded=False, whitelist='No', 
                          players_max_ever=100000, players_min_ever=1000, date_added=now, last_updated=now),
            MinecraftServer(ip='10.0.0.50', port=25565, motd='Survival Server', version='Paper 1.20.4', 
                          players_online=25, is_modded=False, whitelist='Unknown',
                          players_max_ever=100, players_min_ever=5, date_added=now, last_updated=now),
            MinecraftServer(ip='172.16.0.1', port=25565, motd='Modded', version='1.19.2 Forge', 
                          players_online=10, is_modded=True, whitelist='Yes',
                          players_max_ever=50, players_min_ever=2, date_added=now, last_updated=now),
            MinecraftServer(ip='8.8.8.8', port=25565, motd='Test Server', version='1.20.1', 
                          players_online=0, is_modded=False, whitelist='Unknown',
                          players_max_ever=20, players_min_ever=0, date_added=now, last_updated=now),
        ]
        
        for server in test_servers:
            session.add(server)
        session.commit()
        session.close()
        
        # Create test client (reads DB_PATH from env)
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_get_servers_basic(self):
        """Test basic server list endpoint."""
        response = self.client.get('/api/servers')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('servers', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['servers']), 4)
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['per_page'], 20)
        self.assertEqual(data['pagination']['total'], 4)
    
    def test_get_servers_pagination(self):
        """Test pagination."""
        response = self.client.get('/api/servers?page=1&per_page=2')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 2)
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['per_page'], 2)
        self.assertEqual(data['pagination']['total'], 4)
        self.assertEqual(data['pagination']['pages'], 2)
    
    def test_get_servers_search(self):
        """Test search functionality."""
        response = self.client.get('/api/servers?search=Hypixel')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['motd'], 'Hypixel')
    
    def test_get_servers_search_version(self):
        """Test search by version."""
        response = self.client.get('/api/servers?search=1.20')
        data = json.loads(response.data)
        
        # Should match multiple servers with 1.20 in version
        self.assertGreater(len(data['servers']), 0)
        for server in data['servers']:
            self.assertIn('1.20', server['version'])
    
    def test_get_servers_filter_version(self):
        """Test version filter."""
        response = self.client.get('/api/servers?version=1.19.2')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['version'], '1.19.2 Forge')
    
    def test_get_servers_filter_min_players(self):
        """Test min players filter."""
        response = self.client.get('/api/servers?min_players=20')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 2)  # Hypixel (50000) and Survival (25)
        for server in data['servers']:
            self.assertGreaterEqual(server['players_online'], 20)
    
    def test_get_servers_filter_max_players(self):
        """Test max players filter."""
        response = self.client.get('/api/servers?max_players=50')
        data = json.loads(response.data)
        
        # Should exclude Hypixel (50000 players)
        for server in data['servers']:
            self.assertLessEqual(server['players_online'], 50)
    
    def test_get_servers_filter_modded_only(self):
        """Test modded only filter."""
        response = self.client.get('/api/servers?modded_only=true')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 1)
        self.assertTrue(data['servers'][0]['is_modded'])
    
    def test_get_servers_filter_whitelist_yes(self):
        """Test whitelist=yes filter."""
        response = self.client.get('/api/servers?whitelist=true')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['whitelist'], 'Yes')
    
    def test_get_servers_filter_whitelist_no(self):
        """Test whitelist=no filter."""
        response = self.client.get('/api/servers?no_whitelist=true')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['whitelist'], 'No')
    
    def test_get_servers_filter_whitelist_unknown(self):
        """Test whitelist=unknown filter."""
        response = self.client.get('/api/servers?unknown_whitelist=true')
        data = json.loads(response.data)
        
        self.assertEqual(len(data['servers']), 2)
        for server in data['servers']:
            self.assertEqual(server['whitelist'], 'Unknown')
    
    def test_get_servers_sort_by_players(self):
        """Test sorting by players."""
        response = self.client.get('/api/servers?sort_by=players_online&sort_order=desc')
        data = json.loads(response.data)
        
        # First should have most players
        self.assertEqual(data['servers'][0]['motd'], 'Hypixel')
    
    def test_get_servers_sort_by_players_asc(self):
        """Test sorting by players ascending."""
        response = self.client.get('/api/servers?sort_by=players_online&sort_order=asc')
        data = json.loads(response.data)
        
        # Last should have most players
        self.assertEqual(data['servers'][-1]['motd'], 'Hypixel')
    
    def test_get_single_server(self):
        """Test getting a single server by ID."""
        # First get the list to find an ID
        response = self.client.get('/api/servers')
        data = json.loads(response.data)
        server_id = data['servers'][0]['id']
        
        # Get single server
        response = self.client.get(f'/api/servers/{server_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['id'], server_id)
        self.assertIn('ip', data)
        self.assertIn('motd', data)
    
    def test_get_single_server_not_found(self):
        """Test getting a non-existent server."""
        response = self.client.get('/api/servers/99999')
        self.assertEqual(response.status_code, 404)
    
    def test_get_stats(self):
        """Test stats endpoint."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['total_servers'], 4)
        self.assertEqual(data['modded_servers'], 1)
        self.assertEqual(data['whitelist_servers'], 1)  # Only 1 with 'Yes'
        self.assertIn('total_players', data)
    
    def test_get_filters(self):
        """Test filters endpoint."""
        response = self.client.get('/api/filters')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('versions', data)
        self.assertIsInstance(data['versions'], list)
        self.assertGreater(len(data['versions']), 0)


if __name__ == '__main__':
    unittest.main()
