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

    # ==================== EDGE CASES ====================

    def test_pagination_page_zero(self):
        """Test pagination with page=0 returns empty or first page."""
        response = self.client.get('/api/servers?page=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Page 0 should either return first page or empty results
        self.assertIn('servers', data)

    def test_pagination_negative_page(self):
        """Test pagination with negative page."""
        response = self.client.get('/api/servers?page=-1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_pagination_zero_per_page(self):
        """Test pagination with per_page=0."""
        response = self.client.get('/api/servers?per_page=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should handle gracefully - either return default or empty
        self.assertIn('servers', data)

    def test_pagination_negative_per_page(self):
        """Test pagination with negative per_page."""
        response = self.client.get('/api/servers?per_page=-5')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_pagination_excessive_per_page(self):
        """Test pagination with very large per_page value."""
        response = self.client.get('/api/servers?per_page=999999')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should return all servers without error
        self.assertEqual(len(data['servers']), 4)

    def test_pagination_page_beyond_total(self):
        """Test pagination with page beyond total pages."""
        response = self.client.get('/api/servers?page=9999')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 0)
        self.assertEqual(data['pagination']['total'], 4)

    def test_sort_invalid_column(self):
        """Test sorting by invalid column falls back to default."""
        response = self.client.get('/api/servers?sort_by=invalid_column')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 4)

    def test_sort_invalid_order(self):
        """Test sorting with invalid order falls back to default."""
        response = self.client.get('/api/servers?sort_order=invalid')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 4)

    def test_search_special_characters(self):
        """Test search with SQL special characters."""
        response = self.client.get('/api/servers?search=%_test')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_search_sql_injection_attempt(self):
        """Test search is safe from SQL injection."""
        response = self.client.get("/api/servers?search='; DROP TABLE minecraft_servers; --")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should not crash and table should still exist
        self.assertIn('servers', data)

    def test_search_unicode(self):
        """Test search with unicode characters."""
        response = self.client.get('/api/servers?search=你好')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_search_empty_string(self):
        """Test search with empty string returns all results."""
        response = self.client.get('/api/servers?search=')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 4)

    def test_filter_combined_filters(self):
        """Test combining multiple filters."""
        response = self.client.get('/api/servers?modded_only=true&min_players=5')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        for server in data['servers']:
            self.assertTrue(server['is_modded'])
            self.assertGreaterEqual(server['players_online'], 5)

    def test_filter_min_players_greater_than_max(self):
        """Test min_players > max_players returns empty."""
        response = self.client.get('/api/servers?min_players=100&max_players=10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 0)

    def test_filter_negative_players(self):
        """Test negative player filters."""
        response = self.client.get('/api/servers?min_players=-10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should return all servers since all have >= 0 players
        self.assertGreater(len(data['servers']), 0)

    def test_filter_conflicting_whitelist_options(self):
        """Test conflicting whitelist filters."""
        response = self.client.get('/api/servers?whitelist=true&no_whitelist=true')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should return empty since can't be both Yes and No
        self.assertEqual(len(data['servers']), 0)

    def test_get_server_not_found(self):
        """Test getting non-existent server returns 404."""
        response = self.client.get('/api/servers/999999999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_get_server_invalid_id(self):
        """Test getting server with invalid ID format."""
        response = self.client.get('/api/servers/abc')
        self.assertEqual(response.status_code, 404)  # Flask handles invalid int

    def test_stats_empty_database(self):
        """Test stats endpoint with empty database."""
        # Create new empty db
        empty_db_path = os.path.join(tempfile.gettempdir(), f'test_empty_{uuid.uuid4().hex}.db')
        os.environ['DB_PATH'] = empty_db_path
        engine = get_engine(empty_db_path)
        Base.metadata.create_all(engine)

        empty_app = create_app()
        empty_app.config['TESTING'] = True
        client = empty_app.test_client()

        response = client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_servers'], 0)
        self.assertEqual(data['total_players'], 0)
        self.assertEqual(data['modded_servers'], 0)
        self.assertEqual(data['whitelist_servers'], 0)

        os.unlink(empty_db_path)

    def test_filters_empty_database(self):
        """Test filters endpoint with empty database."""
        empty_db_path = os.path.join(tempfile.gettempdir(), f'test_empty2_{uuid.uuid4().hex}.db')
        os.environ['DB_PATH'] = empty_db_path
        engine = get_engine(empty_db_path)
        Base.metadata.create_all(engine)

        empty_app = create_app()
        empty_app.config['TESTING'] = True
        client = empty_app.test_client()

        response = client.get('/api/filters')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('versions', data)
        self.assertEqual(data['versions'], [])

        os.unlink(empty_db_path)

    def test_null_motd_handling(self):
        """Test handling servers with null MOTD."""
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = MinecraftServer(
            ip='192.168.99.99',
            port=25565,
            motd=None,
            version=None,
            players_online=0,
            is_modded=False,
            whitelist='Unknown'
        )
        session.add(server)
        session.commit()
        session.close()

        response = self.client.get('/api/servers?search=192.168.99.99')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 1)
        self.assertIsNone(data['servers'][0]['motd'])

    def test_to_dict_with_null_dates(self):
        """Test to_dict handles null dates gracefully."""
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = session.query(MinecraftServer).first()
        # Manually set date to None to test edge case
        original_date = server.date_added
        server.date_added = None
        session.commit()

        data = server.to_dict()
        self.assertIsNone(data['date_added'])

        # Restore
        server.date_added = original_date
        session.commit()
        session.close()

    def test_concurrent_filter_and_search(self):
        """Test combining search with all filters."""
        response = self.client.get(
            '/api/servers?search=Server&version=1.20&min_players=0&max_players=100'
            '&modded_only=false&whitelist=false&no_whitelist=false&unknown_whitelist=true'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)


if __name__ == '__main__':
    unittest.main()
