import os
import sys
import time
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scanner.scanner_service import ScannerService


class ScanScheduler:
    def __init__(self, scan_interval_hours=24, **scanner_kwargs):
        self.scan_interval = scan_interval_hours * 3600
        self.scanner = ScannerService(**scanner_kwargs)
        self.running = False
        self._thread = None

    def _run_scan_loop(self):
        while self.running:
            try:
                print(f"[{datetime.now()}] Starting scheduled scan...")
                self.scanner.run_full_scan()
                next_run = datetime.now() + timedelta(seconds=self.scan_interval)
                print(f"[{datetime.now()}] Scan complete. Next scan at {next_run}")
            except Exception as e:
                print(f"[{datetime.now()}] Scan error: {e}")
            
            if self.running:
                time.sleep(self.scan_interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_scan_loop, daemon=True)
        self._thread.start()
        print(f"[{datetime.now()}] Scheduler started. Scanning every {self.scan_interval // 3600} hours")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"[{datetime.now()}] Scheduler stopped")

    def run_once(self):
        self.scanner.run_full_scan()
