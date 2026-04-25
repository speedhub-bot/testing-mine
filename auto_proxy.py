"""
auto_proxy.py — Automatic proxy scraping from public APIs.
Extracted from meow.py / MSMC.py get_proxies() logic.
"""
import threading
import time
import requests

HTTP_APIS = [
    'https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=http&timeout=15000&proxy_format=ipport&format=text',
    'https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt',
    'https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt',
]

SOCKS4_APIS = [
    'https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks4&timeout=15000&proxy_format=ipport&format=text',
    'https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt',
    'https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks4/data.txt',
]

SOCKS5_APIS = [
    'https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks5&timeout=15000&proxy_format=ipport&format=text',
    'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
    'https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt',
    'https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt',
]

GEONODE_SOCKS4 = 'https://proxylist.geonode.com/api/proxy-list?protocols=socks4&limit=500'
GEONODE_SOCKS5 = 'https://proxylist.geonode.com/api/proxy-list?protocols=socks5&limit=500'


def _fetch_text_list(url: str, timeout: int = 10) -> list:
    """Fetch a plain-text proxy list (one ip:port per line)."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return [line.strip() for line in r.text.splitlines() if line.strip() and ':' in line]
    except Exception:
        pass
    return []


def _fetch_geonode(url: str, timeout: int = 10) -> list:
    """Fetch proxies from GeoNode JSON API."""
    proxies = []
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            for item in r.json().get('data', []):
                ip = item.get('ip', '')
                port = item.get('port', '')
                if ip and port:
                    proxies.append(f'{ip}:{port}')
    except Exception:
        pass
    return proxies


def get_proxies(config: dict) -> list:
    """
    Scrape HTTP, SOCKS4, and SOCKS5 proxies from all configured public APIs.
    Returns a deduplicated list of requests-compatible proxy dicts.
    """
    if not config.get('auto_proxy', False):
        return []

    http_raw = []
    socks4_raw = []
    socks5_raw = []

    for url in HTTP_APIS:
        http_raw.extend(_fetch_text_list(url))

    for url in SOCKS4_APIS:
        socks4_raw.extend(_fetch_text_list(url))
    socks4_raw.extend(_fetch_geonode(GEONODE_SOCKS4))

    for url in SOCKS5_APIS:
        socks5_raw.extend(_fetch_text_list(url))
    socks5_raw.extend(_fetch_geonode(GEONODE_SOCKS5))

    # Deduplicate within each type
    http_raw = list(dict.fromkeys(http_raw))
    socks4_raw = list(dict.fromkeys(socks4_raw))
    socks5_raw = list(dict.fromkeys(socks5_raw))

    result = []
    for proxy in http_raw:
        result.append({'http': f'http://{proxy}', 'https': f'http://{proxy}'})
    for proxy in socks4_raw:
        result.append({'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'})
    for proxy in socks5_raw:
        result.append({'http': f'socks5://{proxy}', 'https': f'socks5://{proxy}'})

    return result


def start_auto_proxy_thread(
    proxy_pool: list,
    config: dict,
    stop_event: threading.Event,
) -> threading.Thread:
    """
    Start a daemon thread that refreshes proxy_pool at the configured interval.
    The thread replaces proxy_pool[:] in-place so all references stay valid.
    """
    refresh_minutes = int(config.get('proxy_refresh_minutes', 5))

    def _worker():
        while not stop_event.is_set():
            try:
                new_proxies = get_proxies(config)
                if new_proxies:
                    proxy_pool[:] = new_proxies
            except Exception:
                pass
            # Sleep in small increments so stop_event is checked frequently
            for _ in range(refresh_minutes * 60):
                if stop_event.is_set():
                    return
                time.sleep(1)

    t = threading.Thread(target=_worker, daemon=True, name='auto-proxy-scraper')
    t.start()
    return t
