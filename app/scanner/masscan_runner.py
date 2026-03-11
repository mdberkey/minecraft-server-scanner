import subprocess
import os
import json
import time
from datetime import datetime

class MasscanRunner:
    def __init__(self, masscan_path, exclude_file, output_file, rate=20000):
        self.masscan_path = masscan_path
        self.exclude_file = exclude_file
        self.output_file = output_file
        self.rate = rate

    def run_scan(self):
        cmd = [
            self.masscan_path,
            '--excludefile', self.exclude_file,
            '-p25565',
            '0.0.0.0/0',
            '--source-port', '61000',
            '--banners',
            '--rate', str(self.rate),
            '-oJ', self.output_file
        ]
        
        print(f"[{datetime.now()}] Starting masscan scan...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Masscan error: {result.stderr}")
            return False
        
        print(f"[{datetime.now()}] Scan completed.")
        return True

    def parse_results(self):
        results = []
        if not os.path.exists(self.output_file):
            return results
        
        with open(self.output_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    obj = json.loads(line.rstrip(','))
                    if obj.get('ip') and obj.get('ports'):
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
        
        return results
