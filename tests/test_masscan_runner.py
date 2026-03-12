"""Unit tests for MasscanRunner banner parsing."""
import unittest
import os
import json
import tempfile

from app.scanner.masscan_runner import MasscanRunner


class TestMasscanRunner(unittest.TestCase):
    
    def setUp(self):
        self.runner = MasscanRunner(
            masscan_path='masscan',
            exclude_file='exclude.conf',
            output_file='test.json',
            rate=20000
        )
    
    def test_parse_minecraft_banner_basic(self):
        """Test parsing a basic Minecraft status JSON from banner."""
        banner = '{"description":"A Minecraft Server","players":{"online":5,"max":20},"version":{"name":"1.20.4","protocol":765}}'
        
        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['ip'], '192.168.1.1')
        self.assertEqual(result['port'], 25565)
        self.assertEqual(result['motd'], 'A Minecraft Server')
        self.assertEqual(result['players_online'], 5)
        self.assertEqual(result['players_max'], 20)
        self.assertEqual(result['version'], '1.20.4')
        self.assertEqual(result['whitelist'], 'Unknown')
        self.assertFalse(result['is_modded'])
    
    def test_parse_minecraft_banner_with_chat_json(self):
        """Test parsing MOTD with JSON chat formatting."""
        banner = '{"description":{"text":"Hypixel Network","extra":[{"text":" [1.8-1.20]","color":"gray"}]},"players":{"online":50000,"max":100000},"version":{"name":"Requires MC 1.8 / 1.20"}}'
        
        result = self.runner._parse_minecraft_banner(banner, '1.2.3.4', 25565)
        
        self.assertEqual(result['motd'], 'Hypixel Network [1.8-1.20]')
        self.assertEqual(result['players_online'], 50000)
    
    def test_parse_minecraft_banner_with_favicon(self):
        """Test parsing banner with favicon."""
        banner = '{"description":"Test","players":{"online":0,"max":20},"version":{"name":"1.20.4"},"favicon":"data:image/png;base64,iVBORw0KGgoAAAANS"}'
        
        result = self.runner._parse_minecraft_banner(banner, '10.0.0.1', 25565)
        
        self.assertEqual(result['favicon'], 'data:image/png;base64,iVBORw0KGgoAAAANS')
    
    def test_parse_minecraft_banner_forge_modded(self):
        """Test detecting Forge modded servers."""
        banner = '{"description":"Modded Server","players":{"online":10,"max":50},"version":{"name":"1.20.1 Forge","protocol":763}}'
        
        result = self.runner._parse_minecraft_banner(banner, '5.6.7.8', 25565)
        
        self.assertTrue(result['is_modded'])
    
    def test_parse_minecraft_banner_fabric_modded(self):
        """Test detecting Fabric modded servers."""
        banner = '{"description":"Fabric Server","players":{"online":5,"max":20},"version":{"name":"1.19.2 Fabric","protocol":760}}'
        
        result = self.runner._parse_minecraft_banner(banner, '9.10.11.12', 25565)
        
        self.assertTrue(result['is_modded'])
    
    def test_parse_minecraft_banner_fml_modinfo(self):
        """Test detecting modded servers via FML modinfo."""
        banner = '{"description":"FML Server","players":{"online":3,"max":10},"version":{"name":"1.12.2"},"modinfo":{"type":"FML","modList":[]}}'
        
        result = self.runner._parse_minecraft_banner(banner, '13.14.15.16', 25565)
        
        self.assertTrue(result['is_modded'])
    
    def test_parse_minecraft_banner_invalid_json(self):
        """Test handling of invalid JSON."""
        banner = 'not valid json'
        
        result = self.runner._parse_minecraft_banner(banner, '1.1.1.1', 25565)
        
        self.assertIsNone(result)
    
    def test_parse_minecraft_banner_empty_banner(self):
        """Test handling of empty banner."""
        result = self.runner._parse_minecraft_banner('', '1.1.1.1', 25565)
        self.assertIsNone(result)
        
        result = self.runner._parse_minecraft_banner(None, '1.1.1.1', 25565)
        self.assertIsNone(result)
    
    def test_parse_minecraft_banner_missing_description(self):
        """Test handling of banner without description field."""
        banner = '{"players":{"online":0,"max":20},"version":{"name":"1.20.4"}}'
        
        result = self.runner._parse_minecraft_banner(banner, '1.1.1.1', 25565)
        
        self.assertIsNone(result)
    
    def test_parse_chat_nested(self):
        """Test parsing deeply nested chat JSON."""
        banner = '{"description":{"text":"Server","extra":[{"text":" - ","color":"dark_gray"},{"text":"Survival","color":"green","extra":[{"text":" [VIP]","color":"gold"}]}]},"players":{"online":0,"max":20},"version":{"name":"1.20.4"}}'
        
        result = self.runner._parse_minecraft_banner(banner, '1.2.3.4', 25565)
        
        self.assertEqual(result['motd'], 'Server - Survival [VIP]')
    
    def test_parse_results_from_file(self):
        """Test parsing masscan JSON output file with embedded Minecraft banners."""
        # Create test data that mimics masscan output
        test_data = [
            {
                "ip": "192.168.1.100",
                "timestamp": "1234567890",
                "ports": [{
                    "port": 25565,
                    "proto": "tcp",
                    "service": {
                        "name": "minecraft",
                        "banner": json.dumps({
                            "description": "Hypixel Network",
                            "players": {"online": 50000, "max": 100000},
                            "version": {"name": "Requires MC 1.8 / 1.20"},
                            "favicon": "data:image/png;base64,test123"
                        })
                    }
                }]
            },
            {
                "ip": "10.0.0.50",
                "timestamp": "1234567891",
                "ports": [{
                    "port": 25565,
                    "proto": "tcp",
                    "service": {
                        "name": "minecraft",
                        "banner": json.dumps({
                            "description": {"text": "Survival Server", "extra": [{"text": " [1.20]", "color": "gray"}]},
                            "players": {"online": 25, "max": 100},
                            "version": {"name": "Paper 1.20.4"}
                        })
                    }
                }]
            },
            {
                "ip": "172.16.0.1",
                "timestamp": "1234567892",
                "ports": [{
                    "port": 25565,
                    "proto": "tcp",
                    "service": {
                        "name": "minecraft",
                        "banner": json.dumps({
                            "description": "Modded",
                            "players": {"online": 10, "max": 50},
                            "version": {"name": "1.19.2 Forge"},
                            "modinfo": {"type": "FML"}
                        })
                    }
                }]
            }
        ]

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('[\n')
            for i, entry in enumerate(test_data):
                line = json.dumps(entry)
                if i < len(test_data) - 1:
                    line += ','
                f.write(line + '\n')
            f.write(']\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()

            self.assertEqual(len(results), 3)

            # Check first server (basic with favicon)
            self.assertEqual(results[0]['ip'], '192.168.1.100')
            self.assertEqual(results[0]['motd'], 'Hypixel Network')
            self.assertEqual(results[0]['players_online'], 50000)
            self.assertEqual(results[0]['favicon'], 'data:image/png;base64,test123')

            # Check second server (chat JSON MOTD)
            self.assertEqual(results[1]['ip'], '10.0.0.50')
            self.assertEqual(results[1]['motd'], 'Survival Server [1.20]')
            self.assertEqual(results[1]['players_online'], 25)

            # Check third server (modded)
            self.assertEqual(results[2]['ip'], '172.16.0.1')
            self.assertTrue(results[2]['is_modded'])
            self.assertEqual(results[2]['version'], '1.19.2 Forge')
        finally:
            os.unlink(temp_file)

    # ==================== EDGE CASES ====================

    def test_parse_minecraft_banner_unicode_motd(self):
        """Test parsing MOTD with unicode characters."""
        banner = '{"description":"服务器测试 - テスト - 🎮","players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], '服务器测试 - テスト - 🎮')

    def test_parse_minecraft_banner_html_entities(self):
        """Test parsing MOTD with HTML entities."""
        banner = '{"description":"Server &amp; Test","players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], 'Server &amp; Test')

    def test_parse_minecraft_banner_color_codes(self):
        """Test parsing MOTD with Minecraft color codes."""
        banner = '{"description":"§6Gold Server §cRed Text","players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], '§6Gold Server §cRed Text')

    def test_parse_minecraft_banner_whitespace_only(self):
        """Test parsing banner with whitespace-only description."""
        banner = '{"description":"   ","players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], '   ')

    def test_parse_minecraft_banner_null_description(self):
        """Test parsing banner with null description."""
        banner = '{"description":null,"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        # Should return None since description is required
        self.assertIsNone(result)

    def test_parse_minecraft_banner_missing_players(self):
        """Test parsing banner without players field."""
        banner = '{"description":"Test Server","version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['players_online'], 0)
        self.assertEqual(result['players_max'], 0)

    def test_parse_minecraft_banner_missing_version(self):
        """Test parsing banner without version field."""
        banner = '{"description":"Test Server","players":{"online":5,"max":20}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertIsNone(result['version'])

    def test_parse_minecraft_banner_null_players(self):
        """Test parsing banner with null players values."""
        banner = '{"description":"Test Server","players":{"online":null,"max":null},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        # .get() returns None for null values
        self.assertIsNone(result['players_online'])
        self.assertIsNone(result['players_max'])

    def test_parse_minecraft_banner_string_players(self):
        """Test parsing banner with string player counts."""
        banner = '{"description":"Test Server","players":{"online":"5","max":"20"},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        # String values won't match int comparison but should be stored
        self.assertEqual(result['players_online'], "5")

    def test_parse_minecraft_banner_negative_players(self):
        """Test parsing banner with negative player count."""
        banner = '{"description":"Test Server","players":{"online":-5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['players_online'], -5)

    def test_parse_minecraft_banner_very_large_players(self):
        """Test parsing banner with extremely large player count."""
        banner = '{"description":"Test Server","players":{"online":999999999999,"max":999999999999},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['players_online'], 999999999999)

    def test_parse_minecraft_banner_empty_version_name(self):
        """Test parsing banner with empty version name."""
        banner = '{"description":"Test Server","players":{"online":5,"max":20},"version":{"name":""}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '')

    def test_parse_minecraft_banner_null_version_name(self):
        """Test parsing banner with null version name."""
        banner = '{"description":"Test Server","players":{"online":5,"max":20},"version":{"name":null}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertIsNone(result['version'])

    def test_parse_minecraft_banner_truncated_json(self):
        """Test parsing truncated/incomplete JSON banner."""
        banner = '{"description":"Test Server","players":{"online":5'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNone(result)

    def test_parse_minecraft_banner_double_encoded_json(self):
        """Test parsing double-encoded JSON banner."""
        # Banner that's JSON-encoded twice
        inner = json.dumps({"description":"Test","players":{"online":5,"max":20},"version":{"name":"1.20.4"}})
        banner = json.dumps(inner)  # Double encoded

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        # First decode gives a string, not a dict - should fail
        self.assertIsNone(result)

    def test_parse_minecraft_banner_array_description(self):
        """Test parsing banner with array as description (unexpected type)."""
        banner = '{"description":["Test","Server"],"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        # Should handle gracefully - _parse_chat expects dict or string
        self.assertIsNotNone(result)

    def test_parse_chat_empty_extra_array(self):
        """Test parsing chat with empty extra array."""
        banner = '{"description":{"text":"Server","extra":[]},"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertEqual(result['motd'], 'Server')

    def test_parse_chat_extra_with_null_text(self):
        """Test parsing chat with null text in extra."""
        banner = '{"description":{"text":"Server","extra":[{"text":null,"color":"red"}]},"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        # Null text should be treated as empty string
        self.assertEqual(result['motd'], 'Server')

    def test_parse_chat_extra_missing_text_field(self):
        """Test parsing chat with missing text field in extra."""
        banner = '{"description":{"text":"Server","extra":[{"color":"red"}]},"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertEqual(result['motd'], 'Server')

    def test_parse_results_empty_file(self):
        """Test parsing empty masscan output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_nonexistent_file(self):
        """Test parsing non-existent masscan output file."""
        self.runner.output_file = '/nonexistent/path/file.json'
        results = self.runner.parse_results()
        self.assertEqual(results, [])

    def test_parse_results_malformed_json_lines(self):
        """Test parsing file with malformed JSON lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json\n')
            f.write('{"ip": "1.2.3.4", "ports": []}\n')  # Valid but no ports
            f.write('{broken json\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            # Should skip malformed lines and return empty (no valid banners)
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_missing_ip_field(self):
        """Test parsing entry without IP field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"timestamp": "123", "ports": []}\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_empty_ports_array(self):
        """Test parsing entry with empty ports array."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"ip": "1.2.3.4", "ports": []}\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_missing_service_field(self):
        """Test parsing entry without service field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"ip": "1.2.3.4", "ports": [{"port": 25565}]}\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            # Should return empty result (no banner)
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_empty_banner(self):
        """Test parsing entry with empty banner."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"ip": "1.2.3.4", "ports": [{"port": 25565, "service": {"banner": ""}}]}\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            self.assertEqual(results, [])
        finally:
            os.unlink(temp_file)

    def test_parse_results_non_minecraft_port(self):
        """Test parsing entry with non-standard port."""
        test_data = {
            "ip": "192.168.1.1",
            "timestamp": "1234567890",
            "ports": [{
                "port": 25566,  # Non-standard port
                "proto": "tcp",
                "service": {
                    "name": "minecraft",
                    "banner": json.dumps({
                        "description": "Test",
                        "players": {"online": 5, "max": 20},
                        "version": {"name": "1.20.4"}
                    })
                }
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json.dumps(test_data) + '\n')
            temp_file = f.name

        try:
            self.runner.output_file = temp_file
            results = self.runner.parse_results()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['port'], 25566)
        finally:
            os.unlink(temp_file)

    def test_parse_chat_with_integer_text(self):
        """Test parsing chat where text is an integer (unexpected type)."""
        banner = '{"description":{"text":123,"extra":[]},"players":{"online":5,"max":20},"version":{"name":"1.20.4"}}'

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertIsNotNone(result)
        self.assertEqual(result['motd'], '123')

    def test_parse_chat_with_nested_deeply_nested_extra(self):
        """Test parsing deeply nested extra arrays."""
        banner = '''{
            "description": {
                "text": "Level1",
                "extra": [{
                    "text": "Level2",
                    "extra": [{
                        "text": "Level3",
                        "extra": [{
                            "text": "Level4"
                        }]
                    }]
                }]
            },
            "players": {"online": 5, "max": 20},
            "version": {"name": "1.20.4"}
        }'''

        result = self.runner._parse_minecraft_banner(banner, '192.168.1.1', 25565)

        self.assertEqual(result['motd'], 'Level1Level2Level3Level4')

    def test_parse_minecraft_banner_fabric_in_description(self):
        """Test detecting modded when Fabric mentioned in description."""
        banner = '{"description":"Fabric Server Test","players":{"online":5,"max":20},"version":{"name":"1.19.2"}}'

        result = self.runner._parse_minecraft_banner(banner, '1.2.3.4', 25565)

        # Currently only checks version field for modded detection
        self.assertFalse(result['is_modded'])


if __name__ == '__main__':
    unittest.main()
