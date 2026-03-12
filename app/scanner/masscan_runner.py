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
                    if not obj.get('ip') or not obj.get('ports'):
                        continue

                    ip = obj['ip']
                    port_obj = obj['ports'][0] if obj['ports'] else None
                    if not port_obj:
                        continue

                    port = port_obj.get('port', 25565)
                    service = port_obj.get('service', {})
                    banner_str = service.get('banner', '')

                    server_data = self._parse_minecraft_banner(banner_str, ip, port)
                    if server_data:
                        results.append(server_data)

                except json.JSONDecodeError:
                    continue

        return results

    def _parse_minecraft_banner(self, banner_str, ip, port):
        if not banner_str:
            return None

        try:
            response = json.loads(banner_str)
        except json.JSONDecodeError:
            return None

        if not isinstance(response, dict) or 'description' not in response:
            return None

        if response.get('description') is None:
            return None

        result = {
            'ip': ip,
            'port': port,
            'favicon': None,
            'whitelist': 'Unknown',
            'motd': None,
            'version': None,
            'is_modded': False,
            'players_online': 0,
            'players_max': 0,
        }

        desc = response['description']
        if isinstance(desc, dict):
            result['motd'] = self._parse_chat(desc)
        else:
            result['motd'] = str(desc)

        if 'version' in response:
            version = response['version']
            version_name = version.get('name')
            if version_name is None:
                result['version'] = None
            else:
                result['version'] = str(version_name)
                version_name_lower = version_name.lower()
                if 'forge' in version_name_lower or 'mod' in version_name_lower or 'fabric' in version_name_lower:
                    result['is_modded'] = True

        if 'players' in response:
            players = response['players']
            result['players_online'] = players.get('online', 0)
            result['players_max'] = players.get('max', 0)

        if 'favicon' in response:
            result['favicon'] = response['favicon']

        mods = response.get('modinfo', {})
        if mods.get('type') == 'FML':
            result['is_modded'] = True

        return result

    def _parse_chat(self, chat_obj):
        if isinstance(chat_obj, str):
            return chat_obj
        if not isinstance(chat_obj, dict):
            return str(chat_obj) if chat_obj is not None else ''

        text = chat_obj.get('text', '')
        if text is None:
            text = ''
        else:
            text = str(text)
        extra = chat_obj.get('extra', [])
        for item in extra:
            text += self._parse_chat(item)
        return text
