import socket
import json
import struct
import select

class MinecraftQuery:
    @staticmethod
    def ping_server(ip, port=25565, timeout=5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            
            server_addr = ip.encode('utf-8')
            handshake = b'\x00' + b'\x2f' + struct.pack('B', len(server_addr)) + server_addr
            handshake += struct.pack('>H', port) + b'\x01'
            
            sock.sendall(struct.pack('B', len(handshake)) + handshake)
            sock.sendall(b'\x01\x00')
            
            import time
            time.sleep(0.3)
            
            sock.setblocking(False)
            ready = select.select([sock], [], [], timeout)
            if not ready[0]:
                return None
            
            data = sock.recv(65535)
            if not data:
                return None
            
            json_start = data.find(b'{')
            json_end = data.rfind(b'}') + 1
            if json_start < 0 or json_end <= json_start:
                return None
            
            json_bytes = data[json_start:json_end]
            json_str = json_bytes.decode('utf-8', errors='replace')
            response = json.loads(json_str)
            
            sock.close()
            return MinecraftQuery._parse_response(response, ip, port)
            
        except Exception:
            return None

    @staticmethod
    def _parse_response(response, ip, port):
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
        
        if 'description' in response:
            desc = response['description']
            if isinstance(desc, dict):
                result['motd'] = MinecraftQuery._parse_chat(desc)
            else:
                result['motd'] = str(desc)
        
        if 'version' in response:
            version = response['version']
            result['version'] = version.get('name', 'Unknown')
            if 'forge' in version.get('name', '').lower() or 'mod' in version.get('name', '').lower():
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

    @staticmethod
    def _parse_chat(chat_obj):
        text = chat_obj.get('text', '')
        extra = chat_obj.get('extra', [])
        for item in extra:
            if isinstance(item, dict):
                text += item.get('text', '')
            else:
                text += str(item)
        return text
