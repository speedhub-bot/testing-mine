"""
auto_ops.py — Auto name and skin setting for Minecraft accounts.
Extracted from meow.py / DonutSMP Checker.py setname/setskin logic.
"""
import random
import string
import time

_NAME_URL = 'https://api.minecraftservices.com/minecraft/profile/name/{name}'
_SKIN_URL = 'https://api.minecraftservices.com/minecraft/profile/skins'


def _resolve_name_format(name_format: str) -> str:
    """Replace {random_letter} and {random_number} placeholders."""
    result = name_format
    # Replace all {random_letter} occurrences
    while '{random_letter}' in result:
        result = result.replace('{random_letter}', random.choice(string.ascii_lowercase), 1)
    # Replace all {random_number} occurrences
    while '{random_number}' in result:
        result = result.replace('{random_number}', str(random.randint(0, 9)), 1)
    # Legacy: replace {random} with 3 random alphanumeric chars
    while '{random}' in result:
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
        result = result.replace('{random}', rand_str, 1)
    return result


def setname(
    session,
    token: str,
    name_format: str,
    maxretries: int,
    original_name: str = 'N/A',
) -> str:
    """
    Attempt to rename the Minecraft account using name_format.
    Returns the new name on success, original_name on failure.
    """
    new_name = _resolve_name_format(name_format)
    headers = {'Authorization': f'Bearer {token}'}

    for _ in range(maxretries):
        try:
            resp = session.put(
                _NAME_URL.format(name=new_name),
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                return new_name
            if resp.status_code == 429:
                time.sleep(3)
                continue
            # 400 = name taken / invalid; try a new random name
            new_name = _resolve_name_format(name_format)
        except Exception:
            pass

    return original_name


def setskin(
    session,
    token: str,
    skin_url: str,
    variant: str,
    maxretries: int,
) -> bool:
    """
    Set the Minecraft account skin.
    Returns True on success, False on failure.
    """
    if not skin_url:
        return False

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    payload = {'url': skin_url, 'variant': variant or 'classic'}

    for _ in range(maxretries):
        try:
            resp = session.post(_SKIN_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return True
            if resp.status_code == 429:
                time.sleep(3)
                continue
        except Exception:
            pass

    return False
