import socket
import json
import struct

class MinecraftQuery:
    @staticmethod
    def ping_server(ip, port=25565, timeout=5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            
            server_addr = ip.encode('utf-8')
            packed_addr = struct.pack('B', len(server_addr)) + server_addr
            packed_port = struct.pack('>H', port)
            packet = b'\x00' + packed_addr + packed_port + b'\x01'
            
            packet_len = struct.pack('B', len(packet))
            sock.sendall(packet_len + packet)
            
            sock.sendall(b'\x01\x00')
            
            length = MinecraftQuery._read_varint(sock)
            if length < 1:
                return None
            
            packet_id = MinecraftQuery._read_varint(sock)
            if packet_id < 0:
                return None
            
            json_length = MinecraftQuery._read_varint(sock)
            json_data = sock.recv(json_length).decode('utf-8')
            
            sock.close()
            
            response = json.loads(json_data)
            return MinecraftQuery._parse_response(response, ip, port)
            
        except (socket.timeout, socket.error, json.JSONDecodeError, Exception):
            return None

    @staticmethod
    def _read_varint(sock):
        result = 0
        for i in range(5):
            byte = sock.recv(1)
            if len(byte) == 0:
                return -1
            byte = byte[0]
            result |= (byte & 0x7F) << (7 * i)
            if not byte & 0x80:
                return result
        return -1

    @staticmethod
    def _parse_response(response, ip, port):
        result = {
            'ip': ip,
            'port': port,
            'favicon': None,
            'whitelist': False,
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
                result['motd'] = desc
        
        if 'version' in response:
            version = response['version']
            result['version'] = version.get('name', 'Unknown')
            if 'forge' in version.get('name', '').lower() or 'mod' in version.get('name', '').lower():
                result['is_modded'] = True
        
        if 'players' in response:
            players = response['players']
            result['players_online'] = players.get('online', 0)
            result['players_max'] = players.get('max', 0)
            if players.get('enforced', False):
                result['whitelist'] = True
        
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
