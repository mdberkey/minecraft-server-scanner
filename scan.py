#!/usr/bin/env python3
"""
Run masscan fork and append results to NDJSON file.
"""
import os
import subprocess
from datetime import datetime


def get_config():
    return {
        'masscan_path': os.environ.get('MASSCAN_PATH', 'masscan/bin/masscan'),
        'exclude_file': os.environ.get('EXCLUDE_FILE', 'masscan/data/exclude.conf'),
        'scan_output': os.environ.get('SCAN_OUTPUT', 'scan_results.ndjson'),
        'scan_rate': os.environ.get('SCAN_RATE', '20000'),
    }


def run_scan(config):
    """Run masscan and append results to NDJSON file."""
    cmd = [
        config['masscan_path'],
        '--excludefile', config['exclude_file'],
        '-p25565',
        '0.0.0.0/0',
        '--source-port', '61000',
        '--banners',
        '--rate', config['scan_rate'],
        '-oD', config['scan_output'],
    ]

    print(f"[{datetime.now()}] Starting masscan scan...")
    print(f"[{datetime.now()}] Rate: {config['scan_rate']} pps, Output: {config['scan_output']}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[{datetime.now()}] Masscan error: {result.stderr}")
        return False

    print(f"[{datetime.now()}] Scan completed.")
    return True


def main():
    config = get_config()
    success = run_scan(config)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
