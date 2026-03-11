import os
import threading
from app.main import create_app
from app.scanner.scheduler import ScanScheduler

app = create_app()

def run_scheduler():
    scan_interval = int(os.environ.get('SCAN_INTERVAL_HOURS', '24'))
    db_path = os.environ.get('DB_PATH', 'servers.db')
    masscan_path = os.environ.get('MASSCAN_PATH', 'masscan/bin/masscan')
    exclude_file = os.environ.get('EXCLUDE_FILE', 'masscan/data/exclude.conf')
    scan_output = os.environ.get('SCAN_OUTPUT', 'scan_results.json')
    scan_rate = int(os.environ.get('SCAN_RATE', '20000'))

    scheduler = ScanScheduler(
        scan_interval_hours=scan_interval,
        db_path=db_path,
        masscan_path=masscan_path,
        exclude_file=exclude_file,
        scan_output=scan_output,
        scan_rate=scan_rate
    )
    scheduler.start()

if __name__ == '__main__':
    enable_scheduler = os.environ.get('ENABLE_SCHEDULER', 'true').lower() == 'true'
    run_scan_on_start = os.environ.get('RUN_SCAN_ON_START', 'false').lower() == 'true'

    if enable_scheduler:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    if run_scan_on_start:
        print(f"[{__import__('datetime').datetime.now()}] Running initial masscan...")
        scan_interval = int(os.environ.get('SCAN_INTERVAL_HOURS', '24'))
        db_path = os.environ.get('DB_PATH', 'servers.db')
        masscan_path = os.environ.get('MASSCAN_PATH', 'masscan/bin/masscan')
        exclude_file = os.environ.get('EXCLUDE_FILE', 'masscan/data/exclude.conf')
        scan_output = os.environ.get('SCAN_OUTPUT', 'scan_results.json')
        scan_rate = int(os.environ.get('SCAN_RATE', '20000'))

        scanner = ScanScheduler(
            scan_interval_hours=scan_interval,
            db_path=db_path,
            masscan_path=masscan_path,
            exclude_file=exclude_file,
            scan_output=scan_output,
            scan_rate=scan_rate
        )
        scanner.run_once()
        print(f"[{__import__('datetime').datetime.now()}] Initial scan complete.")

    app.run(host='0.0.0.0', port=5000, debug=False)
