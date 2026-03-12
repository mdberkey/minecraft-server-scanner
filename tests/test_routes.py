"""Tests for API routes."""
import unittest
import tempfile
import os
import json
import uuid
from datetime import datetime, timezone

from app.main import create_app
from app.db.models import Server, get_engine, get_session, Base


class TestAPIRoutes(unittest.TestCase):

    def setUp(self):
        self.db_path = os.path.join(tempfile.gettempdir(), f'test_api_{uuid.uuid4().hex}.db')
        os.environ['DB_PATH'] = self.db_path

        engine = get_engine(self.db_path)
        Base.metadata.create_all(engine)
        session = get_session(engine)

        now = datetime.now(timezone.utc)
        test_servers = [
            Server(ip='192.168.1.100', json='{}', motd='Hypixel', version='1.8-1.20',
                   players_online=50000, is_modded=False, players_max=100000, whitelist=1, last_updated=now),
            Server(ip='10.0.0.50', json='{}', motd='Survival Server', version='Paper 1.20.4',
                   players_online=25, is_modded=False, players_max=100, whitelist=0, last_updated=now),
            Server(ip='172.16.0.1', json='{}', motd='Modded', version='1.19.2 Forge',
                   players_online=10, is_modded=True, players_max=50, whitelist=None, last_updated=now),
            Server(ip='8.8.8.8', json='{}', motd='Test Server', version='1.20.1',
                   players_online=0, is_modded=False, players_max=20, whitelist=None, last_updated=now),
        ]

        for server in test_servers:
            session.add(server)
        session.commit()
        session.close()

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

    def test_get_servers_pagination(self):
        """Test pagination."""
        response = self.client.get('/api/servers?page=1&per_page=2')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 2)
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['per_page'], 2)

    def test_get_servers_search(self):
        """Test search functionality."""
        response = self.client.get('/api/servers?search=Hypixel')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['motd'], 'Hypixel')

    def test_get_servers_filter_version(self):
        """Test version filter."""
        response = self.client.get('/api/servers?version=1.19.2')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 1)

    def test_get_servers_filter_min_players(self):
        """Test min_players filter."""
        response = self.client.get('/api/servers?min_players=20')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 2)

    def test_get_servers_filter_max_players(self):
        """Test max_players filter."""
        response = self.client.get('/api/servers?max_players=25')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 3)

    def test_get_servers_filter_player_range(self):
        """Test player range filter with min and max."""
        response = self.client.get('/api/servers?min_players=10&max_players=50')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 2)

    def test_get_servers_filter_vanilla_only(self):
        """Test vanilla_only filter excludes modded servers."""
        response = self.client.get('/api/servers?vanilla_only=true')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 3)
        for server in data['servers']:
            self.assertFalse(server['is_modded'])

    def test_get_servers_filter_modded_only(self):
        """Test modded only filter."""
        response = self.client.get('/api/servers?modded_only=true')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 1)
        self.assertTrue(data['servers'][0]['is_modded'])

    def test_get_servers_filter_whitelist_enabled(self):
        """Test whitelist filter for enabled whitelist."""
        response = self.client.get('/api/servers?whitelist=true')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['whitelist'], 1)

    def test_get_servers_filter_no_whitelist(self):
        """Test whitelist filter for disabled whitelist."""
        response = self.client.get('/api/servers?no_whitelist=true')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 1)
        self.assertEqual(data['servers'][0]['whitelist'], 0)

    def test_get_servers_filter_unknown_whitelist(self):
        """Test whitelist filter for unknown whitelist status."""
        response = self.client.get('/api/servers?unknown_whitelist=true')
        data = json.loads(response.data)

        self.assertEqual(len(data['servers']), 2)
        for server in data['servers']:
            self.assertIsNone(server['whitelist'])

    def test_get_servers_sort_by_players(self):
        """Test sorting by players."""
        response = self.client.get('/api/servers?sort_by=players_online&sort_order=desc')
        data = json.loads(response.data)

        self.assertEqual(data['servers'][0]['ip'], '192.168.1.100')

    def test_get_server_by_ip(self):
        """Test getting a single server by IP."""
        response = self.client.get('/api/servers/192.168.1.100')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['ip'], '192.168.1.100')
        self.assertEqual(data['motd'], 'Hypixel')

    def test_get_server_not_found(self):
        """Test getting a non-existent server."""
        response = self.client.get('/api/servers/999.999.999.999')
        self.assertEqual(response.status_code, 404)

    def test_get_stats(self):
        """Test stats endpoint."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['total_servers'], 4)
        self.assertEqual(data['modded_servers'], 1)
        self.assertEqual(data['total_players'], 50035)

    def test_get_filters(self):
        """Test filters endpoint."""
        response = self.client.get('/api/filters')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('versions', data)
        self.assertIsInstance(data['versions'], list)

    # Edge cases

    def test_pagination_page_zero(self):
        """Test pagination with page=0."""
        response = self.client.get('/api/servers?page=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_pagination_zero_per_page(self):
        """Test pagination with per_page=0."""
        response = self.client.get('/api/servers?per_page=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('servers', data)

    def test_pagination_page_beyond_total(self):
        """Test pagination with page beyond total pages."""
        response = self.client.get('/api/servers?page=9999')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 0)

    def test_search_empty_string(self):
        """Test search with empty string."""
        response = self.client.get('/api/servers?search=')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 4)

    def test_filter_min_players_greater_than_max(self):
        """Test min_players > max_players returns empty."""
        response = self.client.get('/api/servers?min_players=100&max_players=5')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 0)

    def test_stats_empty_database(self):
        """Test stats endpoint with empty database."""
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

        os.unlink(empty_db_path)

    def test_null_motd_handling(self):
        """Test handling servers with null MOTD."""
        engine = get_engine(self.db_path)
        session = get_session(engine)
        server = Server(
            ip='192.168.99.99',
            json='{}',
            motd=None,
            version=None,
            players_online=0,
            is_modded=False,
            players_max=0,
        )
        session.add(server)
        session.commit()
        session.close()

        response = self.client.get('/api/servers?search=192.168.99.99')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['servers']), 1)
        self.assertIsNone(data['servers'][0]['motd'])


if __name__ == '__main__':
    unittest.main()
