"""Tests for import_db.py script."""
import unittest
import os
import tempfile
import json
import sqlite3

import orjson


class TestImportDB(unittest.TestCase):

    def test_parse_banner_basic(self):
        """Test parsing a basic Minecraft banner."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "Test Server",
            "players": {"online": 5, "max": 20},
            "version": {"name": "1.20.4"}
        })

        result = parse_banner(banner)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], 'Test Server')
        self.assertEqual(result['version'], '1.20.4')
        self.assertEqual(result['players_online'], 5)
        self.assertFalse(result['is_modded'])

    def test_parse_banner_with_chat_json(self):
        """Test parsing MOTD with JSON chat formatting."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": {"text": "Hypixel", "extra": [{"text": " [1.8-1.20]"}]},
            "players": {"online": 50000, "max": 100000},
            "version": {"name": "Requires MC 1.8 / 1.20"}
        })

        result = parse_banner(banner)

        self.assertEqual(result['motd'], 'Hypixel [1.8-1.20]')
        self.assertEqual(result['players_online'], 50000)

    def test_parse_banner_forge_modded(self):
        """Test detecting Forge modded servers."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "Modded Server",
            "players": {"online": 10, "max": 50},
            "version": {"name": "1.20.1 Forge"}
        })

        result = parse_banner(banner)
        self.assertTrue(result['is_modded'])

    def test_parse_banner_fabric_modded(self):
        """Test detecting Fabric modded servers."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "Fabric Server",
            "players": {"online": 5, "max": 20},
            "version": {"name": "1.19.2 Fabric"}
        })

        result = parse_banner(banner)
        self.assertTrue(result['is_modded'])

    def test_parse_banner_fml_modinfo(self):
        """Test detecting FML modded servers."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "FML Server",
            "players": {"online": 3, "max": 10},
            "version": {"name": "1.12.2"},
            "modinfo": {"type": "FML"}
        })

        result = parse_banner(banner)
        self.assertTrue(result['is_modded'])

    def test_parse_banner_invalid_json(self):
        """Test handling of invalid JSON."""
        from import_db import parse_banner

        result = parse_banner('not valid json')
        self.assertIsNone(result)

    def test_parse_banner_empty(self):
        """Test handling of empty banner."""
        from import_db import parse_banner

        self.assertIsNone(parse_banner(''))
        self.assertIsNone(parse_banner(None))

    def test_parse_banner_missing_description(self):
        """Test handling of banner without description."""
        from import_db import parse_banner

        banner = json.dumps({
            "players": {"online": 0, "max": 20},
            "version": {"name": "1.20.4"}
        })

        result = parse_banner(banner)
        self.assertIsNone(result)

    def test_parse_banner_null_description(self):
        """Test handling of null description."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": None,
            "players": {"online": 5, "max": 20},
            "version": {"name": "1.20.4"}
        })

        result = parse_banner(banner)
        self.assertIsNone(result)

    def test_parse_banner_with_favicon(self):
        """Test parsing banner with favicon."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "Test",
            "players": {"online": 0, "max": 20},
            "version": {"name": "1.20.4"},
            "favicon": "data:image/png;base64,test123"
        })

        result = parse_banner(banner)
        self.assertEqual(result['favicon'], 'data:image/png;base64,test123')

    def test_parse_banner_null_players(self):
        """Test handling of null player counts."""
        from import_db import parse_banner

        banner = json.dumps({
            "description": "Test",
            "players": {"online": None, "max": None},
            "version": {"name": "1.20.4"}
        })

        result = parse_banner(banner)
        self.assertEqual(result['players_online'], 0)
        self.assertEqual(result['players_max'], 0)

    def test_parse_chat_nested(self):
        """Test parsing deeply nested chat JSON."""
        from import_db import parse_chat

        chat = {
            "text": "Server",
            "extra": [
                {"text": " - ", "color": "gray"},
                {"text": "Survival", "extra": [{"text": " [VIP]"}]}
            ]
        }

        result = parse_chat(chat)
        self.assertEqual(result, 'Server - Survival [VIP]')

    def test_parse_chat_null_text(self):
        """Test parsing chat with null text."""
        from import_db import parse_chat

        chat = {"text": None, "extra": []}
        result = parse_chat(chat)
        self.assertEqual(result, '')

    def test_parse_chat_integer_text(self):
        """Test parsing chat with integer text."""
        from import_db import parse_chat

        chat = {"text": 123, "extra": []}
        result = parse_chat(chat)
        self.assertEqual(result, '123')

    def test_extract_records_basic(self):
        """Test extracting records from NDJSON file."""
        from import_db import extract_records

        test_data = [
            {"ip": "192.168.1.1", "ports": [{"service": {"banner": json.dumps({"description": "Test", "players": {"online": 5}, "version": {"name": "1.20.4"}})}}]},
            {"ip": "192.168.1.2", "ports": [{"service": {"banner": json.dumps({"description": "Test2", "players": {"online": 10}, "version": {"name": "1.20.4"}})}}]},
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as f:
            for entry in test_data:
                f.write(json.dumps(entry) + '\n')
            temp_file = f.name

        try:
            records = list(extract_records(temp_file))
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0][0], '192.168.1.1')
            self.assertEqual(records[1][0], '192.168.1.2')
        finally:
            os.unlink(temp_file)

    def test_extract_records_skips_invalid_lines(self):
        """Test that invalid lines are skipped."""
        from import_db import extract_records

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as f:
            f.write('not valid json\n')
            f.write('{"ip": "1.2.3.4", "ports": [{"service": {"banner": "{}"}}]}\n')
            f.write('{broken\n')
            temp_file = f.name

        try:
            records = list(extract_records(temp_file))
            # Should have 1 valid record
            self.assertEqual(len(records), 1)
        finally:
            os.unlink(temp_file)

    def test_extract_records_skips_array_brackets(self):
        """Test that JSON array brackets are skipped."""
        from import_db import extract_records

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as f:
            f.write('[\n')
            f.write('{"ip": "1.2.3.4", "ports": [{"service": {"banner": "{}"}}]}\n')
            f.write(']\n')
            temp_file = f.name

        try:
            records = list(extract_records(temp_file))
            self.assertEqual(len(records), 1)
        finally:
            os.unlink(temp_file)

    def test_import_to_db_basic(self):
        """Test basic import to database."""
        from import_db import import_to_db, get_config

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as db_f:
            db_path = db_f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as ndjson_f:
            ndjson_f.write(json.dumps({
                "ip": "192.168.1.1",
                "ports": [{"service": {"banner": json.dumps({
                    "description": "Test Server",
                    "players": {"online": 5, "max": 20},
                    "version": {"name": "1.20.4"}
                })}}]
            }) + '\n')
            ndjson_path = ndjson_f.name

        config = {
            'db_path': db_path,
            'scan_output': ndjson_path,
            'batch_size': 100,
        }

        try:
            count = import_to_db(config)
            self.assertEqual(count, 1)

            # Verify database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT ip, motd, version, players_online, whitelist FROM servers")
            row = cursor.fetchone()
            conn.close()

            self.assertEqual(row[0], '192.168.1.1')
            self.assertEqual(row[1], 'Test Server')
            self.assertEqual(row[2], '1.20.4')
            self.assertEqual(row[3], 5)
            self.assertEqual(row[4], None)  # whitelist placeholder
        finally:
            os.unlink(db_path)
            os.unlink(ndjson_path)

    def test_import_to_db_updates_existing(self):
        """Test that import updates existing servers."""
        from import_db import import_to_db

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as db_f:
            db_path = db_f.name

        # First import
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as ndjson_f1:
            ndjson_f1.write(json.dumps({
                "ip": "192.168.1.1",
                "ports": [{"service": {"banner": json.dumps({
                    "description": "Original",
                    "players": {"online": 5, "max": 20},
                    "version": {"name": "1.20.4"}
                })}}]
            }) + '\n')
            ndjson_path1 = ndjson_f1.name

        # Second import with updated data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as ndjson_f2:
            ndjson_f2.write(json.dumps({
                "ip": "192.168.1.1",
                "ports": [{"service": {"banner": json.dumps({
                    "description": "Updated",
                    "players": {"online": 10, "max": 30},
                    "version": {"name": "1.20.5"}
                })}}]
            }) + '\n')
            ndjson_path2 = ndjson_f2.name

        config = {
            'db_path': db_path,
            'scan_output': ndjson_path1,
            'batch_size': 100,
        }

        try:
            import_to_db(config)

            config['scan_output'] = ndjson_path2
            import_to_db(config)

            # Verify update
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT motd, version, players_online FROM servers")
            row = cursor.fetchone()
            conn.close()

            self.assertEqual(row[0], 'Updated')
            self.assertEqual(row[1], '1.20.5')
            self.assertEqual(row[2], 10)
        finally:
            os.unlink(db_path)
            os.unlink(ndjson_path1)
            os.unlink(ndjson_path2)

    def test_import_to_db_batching(self):
        """Test batch importing."""
        from import_db import import_to_db

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as db_f:
            db_path = db_f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as ndjson_f:
            for i in range(150):
                ndjson_f.write(json.dumps({
                    "ip": f"192.168.1.{i}",
                    "ports": [{"service": {"banner": json.dumps({
                        "description": f"Server {i}",
                        "players": {"online": i, "max": 100},
                        "version": {"name": "1.20.4"}
                    })}}]
                }) + '\n')
            ndjson_path = ndjson_f.name

        config = {
            'db_path': db_path,
            'scan_output': ndjson_path,
            'batch_size': 50,  # Small batch size for testing
        }

        try:
            count = import_to_db(config)
            self.assertEqual(count, 150)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM servers")
            total = cursor.fetchone()[0]
            conn.close()

            self.assertEqual(total, 150)
        finally:
            os.unlink(db_path)
            os.unlink(ndjson_path)

    def test_import_to_db_missing_file(self):
        """Test import with missing NDJSON file."""
        from import_db import import_to_db

        config = {
            'db_path': ':memory:',
            'scan_output': '/nonexistent/file.ndjson',
            'batch_size': 100,
        }

        count = import_to_db(config)
        self.assertEqual(count, 0)

    def test_get_config_defaults(self):
        """Test configuration defaults."""
        from import_db import get_config

        config = get_config()

        self.assertEqual(config['db_path'], 'servers.db')
        self.assertEqual(config['scan_output'], 'scan_results.ndjson')
        self.assertEqual(config['batch_size'], 5000)

    def test_get_config_from_env(self):
        """Test configuration from environment variables."""
        from import_db import get_config

        os.environ['DB_PATH'] = '/custom/db.sqlite'
        os.environ['SCAN_OUTPUT'] = '/custom/scan.ndjson'
        os.environ['BATCH_SIZE'] = '500'

        config = get_config()

        self.assertEqual(config['db_path'], '/custom/db.sqlite')
        self.assertEqual(config['scan_output'], '/custom/scan.ndjson')
        self.assertEqual(config['batch_size'], 500)

        # Cleanup
        del os.environ['DB_PATH']
        del os.environ['SCAN_OUTPUT']
        del os.environ['BATCH_SIZE']


if __name__ == '__main__':
    unittest.main()
