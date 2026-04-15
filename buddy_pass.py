"""
buddy_pass.py — Xbox Game Pass Ultimate buddy-pass code generation.
Extracted from MSMC.py / DonutSMP Checker.py buddy pass logic.
"""
import time
from datetime import datetime, timezone


_BUDDYPASS_OFFERS_URL = 'https://emerald.xboxservices.com/xboxcomfd/buddypass/Offers'
_BUDDYPASS_GENERATE_URL = 'https://emerald.xboxservices.com/xboxcomfd/buddypass/GenerateOffer?market=GB'
_XSTS_URL = 'https://xsts.auth.xboxlive.com/xsts/authorize'

_XBOX_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Ms-Cv': 'OgMi8P4bcc7vra2wAjJZ/O.19',
    'Origin': 'https://www.xbox.com',
    'Priority': 'u=1, i',
    'Referer': 'https://www.xbox.com/',
    'Sec-Ch-Ua': '"Opera GX";v="111", "Chromium";v="125", "Not.A/Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0',
    'X-Ms-Api-Version': '1.0',
}


def _get_mp_xsts_token(session, xbox_token: str, proxylist: list, getproxy, maxretries: int):
    """Obtain XSTS token with relying party http://mp.microsoft.com/ for buddy-pass API."""
    tries = 0
    while tries < maxretries:
        try:
            proxy = getproxy() if proxylist else None
            resp = session.post(
                _XSTS_URL,
                json={
                    'Properties': {'SandboxId': 'RETAIL', 'UserTokens': [xbox_token]},
                    'RelyingParty': 'http://mp.microsoft.com/',
                    'TokenType': 'JWT',
                },
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                proxies=proxy,
                timeout=15,
            )
            if resp.status_code == 200:
                js = resp.json()
                uhs = js['DisplayClaims']['xui'][0]['uhs']
                xsts_token = js.get('Token')
                return uhs, xsts_token
        except Exception:
            pass
        tries += 1
        if proxylist:
            try:
                session.proxies = getproxy()
            except Exception:
                pass
    return None, None


def _get_valid_offers(session, auth_header: str, proxylist: list, getproxy, maxretries: int):
    """Fetch current buddy-pass offers."""
    tries = 0
    while tries < maxretries:
        try:
            headers = dict(_XBOX_HEADERS)
            headers['Authorization'] = auth_header
            proxy = getproxy() if proxylist else None
            resp = session.get(_BUDDYPASS_OFFERS_URL, headers=headers, proxies=proxy, timeout=15)
            if resp.status_code == 200:
                return resp.json().get('offers', [])
        except Exception:
            pass
        tries += 1
    return []


def _generate_offer(session, auth_header: str, proxylist: list, getproxy, maxretries: int):
    """Generate a new buddy-pass offer."""
    tries = 0
    while tries < maxretries:
        try:
            headers = dict(_XBOX_HEADERS)
            headers['Authorization'] = auth_header
            proxy = getproxy() if proxylist else None
            resp = session.post(_BUDDYPASS_GENERATE_URL, headers=headers, proxies=proxy, timeout=15)
            if resp.status_code == 200 and 'offerId' in resp.text:
                return resp.json().get('offers', [])
        except Exception:
            pass
        tries += 1
    return []


def claim_buddypass_offers(
    session,
    xbox_token: str,
    fname: str,
    write_dedupe,
    config: dict,
    proxylist: list,
    getproxy,
    maxretries: int,
) -> list:
    """
    Generate and collect Xbox Game Pass Ultimate buddy-pass codes.
    Returns list of valid unclaimed offer IDs. Writes each to Codes.txt.
    """
    if not config.get('cap_buddy_pass', True):
        return []

    try:
        uhs, xsts_token = _get_mp_xsts_token(session, xbox_token, proxylist, getproxy, maxretries)
        if not uhs or not xsts_token:
            return []

        auth_header = f'XBL3.0 x={uhs};{xsts_token}'
        now = datetime.now(timezone.utc)
        seen_ids = set()
        collected = []

        def _process_offers(offers):
            for offer in offers:
                offer_id = offer.get('offerId', '')
                if not offer_id or offer_id in seen_ids:
                    continue
                seen_ids.add(offer_id)
                if not offer.get('claimed', True):
                    try:
                        exp = offer.get('expiration', '')
                        exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                        if exp_dt > now:
                            collected.append(offer_id)
                            write_dedupe(fname, 'Codes.txt', f'{offer_id}\n')
                    except Exception:
                        collected.append(offer_id)
                        write_dedupe(fname, 'Codes.txt', f'{offer_id}\n')

        # Check existing offers
        existing = _get_valid_offers(session, auth_header, proxylist, getproxy, maxretries)
        _process_offers(existing)

        # Generate new offers until no new unclaimed codes remain
        max_generate_attempts = 10
        attempt = 0
        while attempt < max_generate_attempts:
            new_offers = _generate_offer(session, auth_header, proxylist, getproxy, maxretries)
            if not new_offers:
                break
            before = len(collected)
            _process_offers(new_offers)
            if len(collected) == before:
                break  # No new codes generated
            attempt += 1

        return collected

    except Exception:
        return []
