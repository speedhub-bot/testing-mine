"""
subscriptions.py — Microsoft active subscriptions check.
Extracted from meow.py MicrosoftChecker.check_subscriptions().
"""

_SUBS_URL = 'https://account.microsoft.com/services/api/subscriptions'


def check_subscriptions(
    session,
    email: str,
    password: str,
    fname: str,
    write_dedupe,
    config: dict,
) -> list:
    """
    Fetch active Microsoft subscriptions for the authenticated session.
    Returns list of subscription strings. Writes to Subscriptions.txt if any found.
    """
    if not config.get('cap_subscriptions', False):
        return []

    try:
        timeout = int(config.get('timeout', 15))
        r = session.get(_SUBS_URL, timeout=timeout)
        subs = []

        if r.status_code == 200:
            try:
                data = r.json()
                items = data if isinstance(data, list) else data.get('subscriptions', [])
                for item in items:
                    if item.get('status', '').lower() == 'active':
                        name = item.get('productName', item.get('name', 'Unknown Subscription'))
                        recurrence = item.get('recurrenceState', item.get('billingCycle', ''))
                        sub_str = f'{name} ({recurrence})' if recurrence else name
                        subs.append(sub_str)
            except Exception:
                pass

        if subs:
            content = f"{email}:{password} | Subs: {', '.join(subs)}\n"
            write_dedupe(fname, 'Subscriptions.txt', content)

        return subs

    except Exception:
        return []
