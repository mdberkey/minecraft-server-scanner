"""Tests for scan.py script."""
import unittest
import os
import tempfile
import subprocess


class TestScanScript(unittest.TestCase):

    def test_get_config_defaults(self):
        """Test configuration defaults."""
        from scan import get_config
        config = get_config()

        self.assertEqual(config['masscan_path'], 'masscan/bin/masscan')
        self.assertEqual(config['exclude_file'], 'masscan/data/exclude.conf')
        self.assertEqual(config['scan_output'], 'scan_results.ndjson')
        self.assertEqual(config['scan_rate'], '20000')

    def test_get_config_from_env(self):
        """Test configuration from environment variables."""
        from scan import get_config

        os.environ['MASSCAN_PATH'] = '/custom/masscan'
        os.environ['SCAN_OUTPUT'] = '/custom/output.ndjson'
        os.environ['SCAN_RATE'] = '50000'

        config = get_config()

        self.assertEqual(config['masscan_path'], '/custom/masscan')
        self.assertEqual(config['scan_output'], '/custom/output.ndjson')
        self.assertEqual(config['scan_rate'], '50000')

        # Cleanup
        del os.environ['MASSCAN_PATH']
        del os.environ['SCAN_OUTPUT']
        del os.environ['SCAN_RATE']

    def test_run_scan_missing_masscan(self):
        """Test run_scan handles missing masscan binary gracefully."""
        from scan import run_scan
        import subprocess

        config = {
            'masscan_path': '/nonexistent/masscan',
            'exclude_file': '/nonexistent/exclude.conf',
            'scan_output': '/tmp/test_scan.ndjson',
            'scan_rate': '20000',
        }

        # Should raise FileNotFoundError or return False
        try:
            result = run_scan(config)
            self.assertFalse(result)
        except FileNotFoundError:
            pass  # Expected when masscan doesn't exist

    def test_run_scan_missing_exclude_file(self):
        """Test run_scan handles missing exclude file gracefully."""
        from scan import run_scan
        import subprocess

        with tempfile.NamedTemporaryFile(suffix='.ndjson', delete=False) as f:
            temp_output = f.name

        config = {
            'masscan_path': 'masscan',
            'exclude_file': '/nonexistent/exclude.conf',
            'scan_output': temp_output,
            'scan_rate': '20000',
        }

        try:
            result = run_scan(config)
            self.assertFalse(result)
        except FileNotFoundError:
            pass  # Expected when masscan or exclude file doesn't exist
        finally:
            if os.path.exists(temp_output):
                os.unlink(temp_output)


if __name__ == '__main__':
    unittest.main()
