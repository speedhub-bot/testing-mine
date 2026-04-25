"""
cookie_saver.py — Save authenticated session cookies in MozillaCookieJar format.
Extracted from DonutSMP Checker.py Capture.save_cookies().
"""
import os
from http.cookiejar import MozillaCookieJar


def save_cookies(
    session,
    name: str,
    account_type: str,
    fname: str,
) -> None:
    """
    Save session cookies to results/{fname}/Cookies/{account_type}/{name}.txt
    in MozillaCookieJar format, stripping the standard header comment lines.
    """
    try:
        # Sanitise account_type for use as a directory name
        safe_type = account_type.replace(' ', '_').replace('/', '_').replace('\\', '_')
        cookie_dir = os.path.join(fname, 'Cookies', safe_type)
        os.makedirs(cookie_dir, exist_ok=True)

        cookie_path = os.path.join(cookie_dir, f'{name}.txt')
        jar = MozillaCookieJar(cookie_path)

        for cookie in session.cookies:
            jar.set_cookie(cookie)

        jar.save(ignore_discard=True, ignore_expires=True)

        # Strip the MozillaCookieJar header lines (lines starting with '#')
        with open(cookie_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.startswith('#')]
        # Remove leading blank lines
        while data_lines and not data_lines[0].strip():
            data_lines.pop(0)

        with open(cookie_path, 'w', encoding='utf-8') as f:
            f.writelines(data_lines)

    except Exception:
        pass
