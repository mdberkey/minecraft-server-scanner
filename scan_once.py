#!/usr/bin/env python3
"""Run a single scan - designed for cron jobs."""
import os
from datetime import datetime

from app.scanner.scanner_service import ScannerService


def main():
    db_path = os.environ.get('DB_PATH', 'servers.db')
    masscan_path = os.environ.get('MASSCAN_PATH', 'masscan/bin/masscan')
    exclude_file = os.environ.get('EXCLUDE_FILE', 'masscan/data/exclude.conf')
    scan_output = os.environ.get('SCAN_OUTPUT', 'scan_results.json')
    scan_rate = int(os.environ.get('SCAN_RATE', '20000'))

    scanner = ScannerService(
        db_path=db_path,
        masscan_path=masscan_path,
        exclude_file=exclude_file,
        scan_output=scan_output,
        scan_rate=scan_rate
    )

    print(f"[{datetime.now()}] Starting scan...")
    scanner.run_full_scan()
    print(f"[{datetime.now()}] Scan complete.")


if __name__ == '__main__':
    main()
