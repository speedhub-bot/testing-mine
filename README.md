# Ultimate Minecraft Checker Bot v2.0

A powerful Telegram bot for checking Minecraft account entitlements via Microsoft authentication with advanced capture, Discord webhooks, and a polished UI.

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

## What's New in v2.0

- **Redesigned UI** — Rich formatted messages with tree-view layouts, progress bars, and 2-column keyboards
- **Enhanced Progress** — Live progress bar with ETA, CPM, hit rate, and elapsed time
- **Richer Captures** — Sectioned Capture.txt output (`[HYPIXEL]`, `[MICROSOFT]`, `[DONUTSMP]`, etc.)
- **Better Hits** — hits.txt now includes capes, Skywars stars, SB level, email access, payments, donut stats, and inbox matches
- **Upgraded Discord Embeds** — Timestamps, color-coded by account type (Hypixel/GamePass/Normal), player body render via Crafatar, spoiler-tagged credentials
- **/help command** — In-bot help with full feature list and usage guide
- **Quick Check button** — Step-by-step guide accessible from main menu
- **No Proxy button** — One-tap "check without proxies" after uploading combos
- **Detailed completion summary** — Hit rate, average CPM, and total duration
- **Better Admin Panel** — User breakdown by role, hit rate stats, 2-column action buttons

## Features

- Microsoft account authentication and Minecraft entitlement checking
- Hypixel stats lookup (via soopy.dev API)
- DonutSMP stats (money, kills, deaths, playtime, shards, blocks)
- Hypixel ban detection via pyCraft
- Email access (IMAP) checking
- Microsoft Balance, Rewards Points, Payment Methods, and Subscriptions
- Xbox Game Pass buddy-pass code generation
- Optifine cape detection
- Name change status
- Inbox keyword scanning (Outlook Substrate API)
- Auto name/skin setting
- Cookie saving
- Discord webhook notifications (embed and plain-text modes)
- Auto proxy scraping from public APIs
- Multi-user support with admin panel, user authorization, and broadcasting
- Configurable capture modules per user (17 toggleable modules)
- Queue system with concurrent worker support

## Credits

@akaza_isnt
