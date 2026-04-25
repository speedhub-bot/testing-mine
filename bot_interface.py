import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database

TOKEN = os.getenv("BOT_TOKEN", "8459126546:AAHN9oT3OzcM74yHPINr7mjJWHTyYbvkn_g")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5944410248"))

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

_waiting_state = {}
VERSION = '2.1-safe'


def get_main_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎯 How to Check", callback_data="how_to_check"),
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


def _home_text(first_name, total, hits, role):
    role_badge = '👑' if role == 'admin' else '⭐'
    return (
        f"╔══════════════════════════╗\n"
        f"  ⚡ <b>Safe MC Account Checker v{VERSION}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"Welcome back, <b>{first_name}</b>! {role_badge}\n\n"
        f"📊 <b>Quick Stats:</b>\n"
        f"  ├ 🔄 Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Minecraft: <code>{hits:,}</code>\n"
        f"  └ 📈 Success Rate: <code>{(hits/total*100) if total > 0 else 0:.1f}%</code>\n\n"
        f"Send exactly one authorized account as <code>email:password</code>.\n"
        f"Bulk files, proxies, Discord webhooks, inbox/payment capture, cookies, and auto account changes are disabled."
    )


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
                "👋 <b>Welcome to Safe MC Account Checker!</b>\n\n"
                "Your access request has been sent to the admin.",
                parse_mode="HTML"
            )
            return
        db.update_user_role(user_id, 'admin')
    user = db.get_user(user_id)
    if user[3] == 'pending' and user_id != ADMIN_ID:
        await message.reply("⏳ Your access is still pending admin review.")
        return
    if user[3] == 'banned':
        await message.reply("🚫 You are banned from using this bot.")
        return
    stats = db.get_user_stats(user_id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    await message.reply(
        _home_text(message.from_user.first_name, total, hits, user[3]),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(user_id)
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(
        f"❓ <b>Help — Safe MC Account Checker v{VERSION}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>How to use:</b>\n"
        f"1️⃣ Send one account you are authorized to check as <code>email:password</code>\n"
        f"2️⃣ The bot checks Microsoft login and Minecraft entitlements\n"
        f"3️⃣ Results are sent privately as simple diagnostic files\n\n"
        f"<b>Disabled for safety:</b>\n"
        f"  • Bulk combo files and proxy checking\n"
        f"  • Discord webhooks / hit reporting\n"
        f"  • Inbox, payment, billing, cookies, buddy-pass claiming\n"
        f"  • Auto name/skin changes",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id)
    )


@dp.message(F.document)
async def handle_document(message: types.Message):
    await message.reply(
        "Bulk file checking is disabled. Send exactly one authorized account as "
        "<code>email:password</code> instead.",
        parse_mode="HTML"
    )


@dp.message(Command("noproxy"))
async def no_proxy(message: types.Message):
    await message.reply("Proxy checking is disabled. Single-account checks run directly.")


@dp.callback_query(F.data == "how_to_check")
async def how_to_check(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎯 <b>How to Check One Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Step 1:</b> Make sure you have permission to check the account.\n"
        "<b>Step 2:</b> Send one line: <code>email:password</code>\n"
        "<b>Step 3:</b> The bot checks login and Minecraft entitlements only.\n\n"
        "Bulk combo files, proxy lists, Discord hit reporting, cookies, inbox scans, "
        "payment capture, and auto account changes are disabled.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")
        ).as_markup()
    )


@dp.callback_query(F.data == "help_menu")
async def help_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        f"❓ <b>Help — Safe MC Account Checker v{VERSION}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Supported diagnostics:</b>\n"
        f"  🎮 Minecraft entitlement type\n"
        f"  👤 Minecraft profile name / UUID / capes\n"
        f"  📊 Hypixel public stats\n"
        f"  🚫 Hypixel ban check\n"
        f"  🧢 Optifine cape detection\n"
        f"  ⭐ Microsoft Rewards points\n"
        f"  🍩 DonutSMP public stats\n\n"
        f"<b>Disabled:</b> bulk/proxy/webhook/payment/inbox/cookie/auto-change modules.",
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
    rate = (hits / total * 100) if total > 0 else 0
    role_icons = {'admin': '👑', 'authorized': '⭐', 'pending': '⏳', 'banned': '🚫'}
    role_icon = role_icons.get(user[3], '👤')
    await callback.message.edit_text(
        f"{role_icon} <b>Profile — {user[2]}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  🆔 ID: <code>{user[0]}</code>\n"
        f"  📛 Name: {user[2]}\n"
        f"  👤 Username: @{user[1] or 'N/A'}\n"
        f"  🎖 Role: <b>{user[3].upper()}</b>\n\n"
        f"📊 <b>Lifetime Diagnostics:</b>\n"
        f"  ┌ 🔄 Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Minecraft: <code>{hits:,}</code>\n"
        f"  ├ ❌ Failed Login: <code>{bad:,}</code>\n"
        f"  ├ ⚠️ Errors/2FA: <code>{errors:,}</code>\n"
        f"  └ 📈 Success Rate: <code>{rate:.1f}%</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder()
        .row(types.InlineKeyboardButton(text="📊 Detailed Stats", callback_data="my_stats"))
        .row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        .as_markup()
    )


@dp.callback_query(F.data == "my_stats")
async def process_my_stats(callback: types.CallbackQuery):
    stats = db.get_user_stats(callback.from_user.id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    bad = stats[3] if stats else 0
    errors = stats[4] if stats else 0
    hit_rate = (hits / total * 100) if total > 0 else 0
    await callback.message.edit_text(
        f"📊 <b>Detailed Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  ┌ 🔄 Checked: <code>{total:,}</code>\n"
        f"  ├ 🎯 Minecraft entitlements: <code>{hits:,}</code>\n"
        f"  ├ ❌ Failed logins: <code>{bad:,}</code>\n"
        f"  ├ ⚠️ Errors/2FA: <code>{errors:,}</code>\n"
        f"  └ 📈 Success Rate: <code>{hit_rate:.2f}%</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder()
        .row(types.InlineKeyboardButton(text="👤 Profile", callback_data="profile"))
        .row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
        .as_markup()
    )


@dp.callback_query(F.data == "configure")
async def process_configure(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    enabled = sum(
        1 for c in (
            s.cap_hypixel_stats, s.cap_hypixel_plancke, s.cap_ban_check,
            s.cap_optifine_cape, s.cap_name_change, s.cap_rewards_points,
            s.cap_donut_stats,
        ) if c
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"🎯 Safe Diagnostics ({enabled}/7)", callback_data="cfg_captures"))
    builder.row(types.InlineKeyboardButton(text=f"📦 Format: {s.file_format.upper()}", callback_data="toggle_format"))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main"))
    await callback.message.edit_text(
        "⚙️ <b>Configuration Center</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Safe diagnostics active: <b>{enabled}</b>/7\n"
        f"Output format: <b>{s.file_format.upper()}</b>\n\n"
        "Bulk/proxy/webhook/payment/inbox/cookie/auto-change settings are removed.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


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
                _btn("Rewards", "cap_rewards_points", s.cap_rewards_points))
    builder.row(_btn("DonutSMP", "cap_donut_stats", s.cap_donut_stats))
    builder.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="configure"))
    await callback.message.edit_text(
        "🎯 <b>Safe Diagnostics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "These modules use account entitlement/profile data or public game stats only.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("toggle_cap_"))
async def toggle_capture_module(callback: types.CallbackQuery):
    col = callback.data.replace("toggle_cap_", "")
    safe_cols = {
        'cap_hypixel_stats', 'cap_hypixel_plancke', 'cap_ban_check',
        'cap_optifine_cape', 'cap_name_change', 'cap_rewards_points',
        'cap_donut_stats',
    }
    if col not in safe_cols:
        await callback.answer("That module is disabled for safety.", show_alert=True)
        return
    s = db.get_settings(callback.from_user.id)
    current = getattr(s, col, 0)
    db.update_settings(callback.from_user.id, **{col: 0 if current else 1})
    await cfg_captures(callback)


@dp.callback_query(F.data == "toggle_format")
async def toggle_format(callback: types.CallbackQuery):
    s = db.get_settings(callback.from_user.id)
    db.update_settings(callback.from_user.id, file_format="zip" if s.file_format == "txt" else "txt")
    await process_configure(callback)


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
    text = (
        f"👑 <b>Admin Control Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌍 <b>Global Statistics:</b>\n"
        f"  ┌ 🔄 Checked: <code>{g_total:,}</code>\n"
        f"  ├ 🎯 Minecraft: <code>{g_hits:,}</code>\n"
        f"  ├ ❌ Failed Login: <code>{g_bad:,}</code>\n"
        f"  └ ⚠️ Errors/2FA: <code>{g_errors:,}</code>\n\n"
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
    pending = [u for u in db.get_all_users() if u[2] == 'pending']
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
        lines.append(f"{icon} @{u[1] or 'N/A'} — <code>{hits:,}</code> Minecraft / <code>{total:,}</code> checked")
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


@dp.message(lambda m: m.from_user.id in _waiting_state)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    state = _waiting_state.pop(user_id, None)
    text = (message.text or '').strip()
    if state == 'broadcast':
        if user_id != ADMIN_ID:
            return
        sent = 0
        for uid in db.get_all_authorized_users():
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
        except ValueError:
            await message.reply("⚠️ Invalid user ID.")
            return
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


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stats = db.get_user_stats(user_id)
    total = stats[1] if stats else 0
    hits = stats[2] if stats else 0
    user = db.get_user(user_id)
    await callback.message.edit_text(
        _home_text(callback.from_user.first_name, total, hits, user[3] if user else 'authorized'),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(user_id)
    )
