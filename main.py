import asyncio

from aiogram import F, types

from bot_interface import bot, dp
from checker_engine import CheckerEngine
from database import Database

db = Database()


@dp.message(F.text)
async def handle_single_account(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or user[3] not in ('authorized', 'admin'):
        await message.reply('🚫 You are not authorized to use this bot.')
        return

    text = (message.text or '').strip()
    if text.startswith('/'):
        return
    if ':' not in text or '\n' in text:
        await message.reply(
            'Send exactly one authorized account as <code>email:password</code>.\n'
            'Bulk combo files and proxy checking are disabled.',
            parse_mode='HTML'
        )
        return

    email, password = text.split(':', 1)
    if not email.strip() or not password.strip():
        await message.reply('⚠️ Use <code>email:password</code>.', parse_mode='HTML')
        return

    status_msg = await message.reply('⌛ Checking this authorized account...')
    settings = db.get_settings(user_id)
    loop = asyncio.get_event_loop()
    engine = CheckerEngine(user_id, [text], settings, db, bot, loop)

    await loop.run_in_executor(None, engine.start)

    if engine.hits:
        await status_msg.edit_text(
            '✅ Minecraft entitlement found. Check result files were sent privately.',
            parse_mode='HTML'
        )
    elif engine.valid_mail:
        await status_msg.edit_text(
            '📧 Microsoft login worked, but no Minecraft entitlement was found.',
            parse_mode='HTML'
        )
    elif engine.twofa:
        await status_msg.edit_text(
            '🔐 This account requires 2FA or extra verification. Check it manually.',
            parse_mode='HTML'
        )
    elif engine.bad:
        await status_msg.edit_text('❌ Login failed for this account.')
    else:
        await status_msg.edit_text('⚠️ Check could not complete. Try again later.')

    for filename, caption in (
        ('hits.txt', '✅ Result'),
        ('Capture.txt', '📄 Account diagnostics'),
        ('Valid_Mail.txt', '📧 Valid Microsoft account'),
        ('2fa.txt', '🔐 2FA required'),
        ('bad.txt', '❌ Login failed'),
        ('errors.txt', '⚠️ Errors'),
    ):
        path = f'{engine.results_dir}/{filename}'
        try:
            await bot.send_document(user_id, types.FSInputFile(path), caption=caption)
        except Exception:
            pass


async def main():
    print('[Bot] Starting safe single-account checker...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
