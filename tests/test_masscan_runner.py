"""Unit tests for MasscanRunner banner parsing."""
import unittest
import os
import sys
import json
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


if __name__ == '__main__':
    unittest.main()
