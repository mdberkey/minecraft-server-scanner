import os
import time
from datetime import datetime, timedelta
from app.scanner.scanner_service import ScannerService

def main():
    scan_interval = int(os.environ.get('SCAN_INTERVAL_HOURS', '24'))
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
    
    print(f"[{datetime.now()}] Scanner service initialized")
    print(f"[{datetime.now()}] Scan interval: {scan_interval} hours")
    
    while True:
        try:
            print(f"[{datetime.now()}] Starting scheduled scan...")
            scanner.run_full_scan()
            next_run = datetime.now() + timedelta(hours=scan_interval)
            print(f"[{datetime.now()}] Scan complete. Next scan at {next_run}")
        except Exception as e:
            print(f"[{datetime.now()}] Scan error: {e}")
        
        time.sleep(scan_interval * 3600)

if __name__ == '__main__':
    main()
