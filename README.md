# SHEIN Verse Product Monitor Bot

A Telegram bot that automatically monitors SHEIN Verse products for availability and sends notifications when products are deliverable to your specified pincodes.

## Features

- Automatic Monitoring: Runs on a configurable schedule (default: every 5 minutes)
- New Product Detection: Only checks new/unseen products to avoid duplicate work
- Multi-Pincode Support: Check delivery for multiple pincodes simultaneously
- Telegram Notifications: Instant alerts when products are available
- Persistent Configuration: Settings stored in SQLite database
- Interactive Commands: Configure everything through Telegram
- Silent When No Results: Only sends messages when products are found

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and instructions |
| `/status` | View current configuration and stats |
| `/seturl <url>` | Set SHEIN filtered URL |
| `/setpin <codes>` | Add pincodes (space-separated) |
| `/rmpin <codes>` | Remove pincodes |
| `/listpin` | List all configured pincodes |
| `/check` | Run a manual check now |
| `/help` | Show help message |

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Open Telegram and search for **@userinfobot**
2. Start the bot with `/start`
3. Copy the **Id** number shown (this is your Chat ID)

### Step 3: Configure Environment Variables

Set the following in Replit:

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather | Yes |
| `TELEGRAM_CHAT_ID` | Your chat ID from userinfobot | Yes |

### Step 4: Configure via Telegram

1. Start your bot on Telegram with `/start`
2. Set your SHEIN URL: `/seturl https://www.sheinindia.in/c/sverse-5939-37961?query=...`
3. Add your pincodes: `/setpin 335704 110001`
4. The bot will automatically check every 5 minutes

### How to Get Your SHEIN Filtered URL

1. Go to [SHEIN India](https://www.sheinindia.in/)
2. Navigate to SHEIN Verse collection
3. Apply your filters (size, gender, category, etc.)
4. Copy the full URL from your browser's address bar

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PRODUCTS` | 30 | Maximum products to check per run |
| `CACHE_EXPIRY_MINUTES` | 10 | How long to cache delivery results |
| `CHECK_INTERVAL_MINUTES` | 5 | How often to run checks |

## How It Works

1. **Scheduled Checks**: The bot runs automatically every `CHECK_INTERVAL_MINUTES`
2. **Product Discovery**: Opens your filtered URL and collects product links
3. **New Product Filter**: Skips products already checked before
4. **Size Selection**: Selects the first available size for each product
5. **Delivery Check**: Checks delivery for each configured pincode
6. **Notifications**: Sends Telegram alert for each deliverable product

## Notification Format

When a product is available, you'll receive:

```
NEW SHEIN VERSE PRODUCT AVAILABLE

PINCODE: 335704
LINK: https://www.sheinindia.in/p/product-id
```

## Important Notes

### Security
- Only the authorized `TELEGRAM_CHAT_ID` can use bot commands
- Other users are silently ignored

### Rate Limiting & Safety
- The bot uses human-like delays between actions
- Products are processed one at a time (no parallel requests)
- Session cookies are persisted to avoid repeated logins
- Default check interval is 5 minutes

### Database
- Uses SQLite database (`shein_monitor.db`)
- Stores pincodes, URL, and seen products
- Automatically cleans up entries older than 7 days

## Troubleshooting

### Bot not sending messages?
- Verify your `TELEGRAM_BOT_TOKEN` is correct
- Make sure you've started a chat with your bot
- Check that `TELEGRAM_CHAT_ID` is your personal ID

### Commands not working?
- Make sure you're using the correct Chat ID
- Only the authorized user can use commands

### Products not found?
- Check if the SHEIN URL is valid with `/status`
- Verify pincodes are configured with `/listpin`

## Files

- `bot.py` - Main Telegram bot with scheduler and commands
- `scraper.py` - Playwright automation for SHEIN
- `database.py` - SQLite database operations
- `config.py` - Configuration settings
- `README.md` - This documentation

## License

This project is for personal use only. Use responsibly and respect SHEIN's terms of service.
