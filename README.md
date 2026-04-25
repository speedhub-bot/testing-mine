# Minecraft Checker Telegram Bot

A Telegram bot for checking Minecraft account entitlements via Microsoft authentication.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export BOT_TOKEN="your-telegram-bot-token"
   export ADMIN_ID="your-telegram-user-id"
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Features

- Microsoft account authentication and Minecraft entitlement checking
- Hypixel stats lookup (via soopy.dev API)
- DonutSMP stats
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
- Configurable capture modules per user
- Queue system with concurrent worker support
