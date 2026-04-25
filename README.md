# Safe Minecraft Account Checker Bot v2.1

A Telegram bot for checking Minecraft account entitlements on accounts you are authorized to check.

This fork removes bulk combo checking, proxy rotation, Discord hit reporting, inbox/payment/cookie capture, buddy-pass claiming, and automatic account changes.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Override the built-in defaults via environment variables:
   ```bash
   export BOT_TOKEN="your-telegram-bot-token"
   export ADMIN_ID="your-telegram-user-id"
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## What's New in v2.1-safe

- **Single-account checks only** — send one authorized `email:password` line at a time
- **No bulk combo files** — uploaded text files are rejected
- **No proxy support** — checks run directly
- **No Discord webhooks** — hit reporting integrations were removed
- **No harvesting modules** — inbox, payment, billing, cookies, buddy-pass claiming, and auto name/skin changes are disabled/removed
- **Safer diagnostics** — entitlement type, Minecraft profile, public game stats, rewards points, and optional ban/cape/name-change checks

## Features

- Microsoft account authentication and Minecraft entitlement checking for authorized accounts
- Hypixel stats lookup (via soopy.dev API)
- DonutSMP stats (money, kills, deaths, playtime, shards, blocks)
- Hypixel ban detection via pyCraft
- Microsoft Rewards Points
- Optifine cape detection
- Name change status
- Multi-user support with admin panel, user authorization, and broadcasting
- Configurable safe diagnostic modules per user

## Credits

@akaza_isnt
