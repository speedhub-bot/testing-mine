"""
ban_checker.py — Hypixel ban check via pyCraft connection to alpha.hypixel.net
"""
import json
import threading
import time
import uuid as uuid_mod
from io import StringIO
import sys

try:
    from minecraft.networking.connection import Connection
    from minecraft.authentication import AuthenticationToken, Profile
    from minecraft.networking.packets import clientbound
    from minecraft.exceptions import LoginDisconnect
    PYCRAFT_AVAILABLE = True
except ImportError:
    PYCRAFT_AVAILABLE = False


def _account_label(email: str) -> str:
    return email

def check_hypixel_ban(
    capture_obj,
    token: str,
    name: str,
    uuid_val: str,
    session,
    fname: str,
    write_dedupe,
    file_lock: threading.Lock,
    maxretries: int,
    config: dict,
) -> None:
    """
    Attempt a pyCraft connection to alpha.hypixel.net:25565 to determine ban status.
    Sets capture_obj.banned:
      - 'False'        → unbanned
      - ban string     → banned (includes ban type and ID)
      - '[Error] ...'  → could not determine
    Writes to Banned.txt or Unbanned.txt via write_dedupe.
    """
    if not config.get('cap_ban_check', True):
        return

    if not PYCRAFT_AVAILABLE:
        capture_obj.banned = '[Error] pyCraft not installed'
        return

    if not name or name == 'N/A' or not token or not uuid_val:
        capture_obj.banned = '[Error] Missing account data'
        return

    clean_uuid = uuid_val.replace('-', '')

    auth_token = AuthenticationToken(
        username=name,
        access_token=token,
        client_token=uuid_mod.uuid4().hex
    )
    auth_token.profile = Profile(id_=clean_uuid, name=name)

    tries = 0
    while tries < maxretries:
        connection = Connection(
            'alpha.hypixel.net', 25565,
            auth_token=auth_token,
            initial_version=47,
            allowed_versions={'1.8', 47}
        )

        @connection.listener(clientbound.login.DisconnectPacket, early=True)
        def login_disconnect(packet):
            try:
                data = json.loads(str(packet.json_data))
                data_str = str(data)
                if 'Suspicious activity' in data_str:
                    ban_id = ''
                    try:
                        ban_id = data['extra'][6]['text'].strip()
                    except Exception:
                        pass
                    capture_obj.banned = f'[Permanently] Suspicious activity detected. Ban ID: {ban_id}'
                    write_dedupe(fname, 'Banned.txt', f'{_account_label(capture_obj.email)}\n')
                elif 'temporarily banned' in data_str:
                    duration = ''
                    reason = ''
                    ban_id = ''
                    try:
                        duration = data['extra'][1]['text']
                        reason = data['extra'][4]['text'].strip()
                        ban_id = data['extra'][8]['text'].strip()
                    except Exception:
                        pass
                    capture_obj.banned = f'[{duration}] {reason} Ban ID: {ban_id}'
                    write_dedupe(fname, 'Banned.txt', f'{_account_label(capture_obj.email)}\n')
                elif 'You are permanently banned from this server!' in data_str:
                    reason = ''
                    ban_id = ''
                    try:
                        reason = data['extra'][2]['text'].strip()
                        ban_id = data['extra'][6]['text'].strip()
                    except Exception:
                        pass
                    capture_obj.banned = f'[Permanently] {reason} Ban ID: {ban_id}'
                    write_dedupe(fname, 'Banned.txt', f'{_account_label(capture_obj.email)}\n')
                elif 'The Hypixel Alpha server is currently closed!' in data_str:
                    capture_obj.banned = 'False'
                    write_dedupe(fname, 'Unbanned.txt', f'{_account_label(capture_obj.email)}\n')
                elif 'Failed cloning your SkyBlock data' in data_str:
                    capture_obj.banned = 'False'
                    write_dedupe(fname, 'Unbanned.txt', f'{_account_label(capture_obj.email)}\n')
                else:
                    try:
                        msg = ''.join(item.get('text', '') for item in data.get('extra', []))
                    except Exception:
                        msg = data_str[:200]
                    capture_obj.banned = msg or '[Unknown disconnect]'
                    write_dedupe(fname, 'Banned.txt', f'{_account_label(capture_obj.email)}\n')
            except Exception as e:
                capture_obj.banned = f'[Error] Packet parse: {e}'

        @connection.listener(clientbound.play.JoinGamePacket, early=True)
        def joined_server(packet):
            if capture_obj.banned is None:
                capture_obj.banned = 'False'
                write_dedupe(fname, 'Unbanned.txt', f'{_account_label(capture_obj.email)}\n')

        try:
            original_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                connection.connect()
                counter = 0
                while capture_obj.banned is None and counter < 1000:
                    time.sleep(0.01)
                    counter += 1
                try:
                    connection.disconnect()
                except Exception:
                    pass
            except Exception:
                pass
            finally:
                sys.stderr = original_stderr

        except Exception:
            pass

        if capture_obj.banned is not None:
            break
        tries += 1

    if capture_obj.banned is None:
        capture_obj.banned = '[Error] Could not determine ban status'

    capture_obj.ban_checked = True
