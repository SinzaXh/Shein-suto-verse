# SHEIN Verse Product Monitor Bot

## Overview
A multi-user Telegram bot that automatically monitors SHEIN Verse products for delivery availability. Uses pure API calls (no browser automation) with proxy rotation. Fully Termux-compatible with .env file support. Each user has fully isolated data storage including separate authentication.

## Project Structure
- `bot.py` - Main entry point with Telegram bot, commands, and multi-user support
- `run_scraper.py` - Subprocess script for running checks
- `user_database.py` - Per-user JSON storage for isolated data management
- `scraper.py` - API-only product fetching and login (no browser)
- `database.py` - Legacy SQLite database module (kept for compatibility)
- `config.py` - Environment configuration with .env file support
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment file for Termux
- `data/` - Per-user JSON files (user_7194175926.json, user_1950577113.json)

## Authorized Users
- 7194175926
- 1950577113

Both users can independently configure their URLs, pincodes, and authentication. Data is fully isolated per user.

## How to Run (Replit)
1. Set environment variable: `TELEGRAM_BOT_TOKEN`
2. Run `python bot.py`
3. Login via `/login <phone>` and `/otp <code>`
4. Configure URLs and pincodes
5. Bot runs auto-checks every 2 minutes

## How to Run (Termux)
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your values
3. Set `NO_PROXY=true` in `.env` (uses phone's Indian IP)
4. Run: `python bot.py`

## Telegram Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/login <phone>` | Start SHEIN OTP login via API |
| `/otp <code>` | Complete login with OTP code |
| `/mystatus` | View your personal configuration |
| `/seturl <url>` | Add a SHEIN filtered URL (supports multiple URLs) |
| `/seturl` | View all your configured URLs |
| `/rmurl` | Remove URLs with inline buttons |
| `/setpin <codes>` | Add pincodes |
| `/rmpin <codes>` | Remove pincodes |
| `/listpin` | List all pincodes |
| `/settoken <cookies>` | Set SHEIN auth cookies manually |
| `/check` | Manual check now |
| `/resend` | Resend all pending notifications |
| `/clearseen` | Clear seen products (re-check all) |
| `/help` | Show help |

## Key Features
- **Pure API-only** - No browser automation, works on Termux
- **Proxy-Based API Access** - Uses rotating proxies (50 proxies)
- **API-based OTP Login** - Login to SHEIN via API calls
- **Multi-user support** with fully isolated data per user
- **Multiple URLs per user** - monitor several filtered pages at once
- **Cart-based availability check** - Verifies product availability via cart API
- `/rmurl` with inline buttons for easy URL removal
- Automatic scheduled checks every 2 minutes
- Only processes new/unseen products
- Silent when no matches (no spam)
- Per-user JSON database files in `data/` directory
- `.env` file support for Termux

## API Login Flow (Per-User)
1. Send `/login <phone_number>` (e.g., `/login 9876543210`)
2. Bot calls SHEIN API to request OTP
3. Receive OTP on your phone
4. Send `/otp <code>` (e.g., `/otp 123456`)
5. Bot verifies OTP via API and saves your cookies

Each user has separate authentication stored in their JSON file.

## Per-User Data Storage
Each user gets their own JSON file:
- `data/user_7194175926.json`
- `data/user_1950577113.json`

Each file stores:
- userId
- monitorUrls (list of URLs)
- pincodes
- authCookies (per-user authentication)
- lastKnownStock
- lastCheckedTimestamp
- seenProducts
- deliveries

## Environment Variables
| Variable | Description |
|----------|-------------|
| TELEGRAM_BOT_TOKEN | Bot token from @BotFather (required) |
| AUTHORIZED_USERS | Comma-separated Telegram user IDs (e.g., `123456,789012`) |
| CHECK_INTERVAL_MINUTES | Check frequency (default: 2) |
| MAX_PRODUCTS | Max products per check (default: 30) |
| PROXY_USERNAME | Proxy authentication username |
| PROXY_PASSWORD | Proxy authentication password |
| INDIAN_PROXY | Indian proxy IP:PORT for cart/delivery APIs (optional) |
| NO_PROXY | Set to "true" when running on Termux (uses direct connection) |

## Running on Termux (Recommended)
When running on Termux (your phone), set `NO_PROXY=true` in your `.env` file.
This disables proxy and uses your phone's Indian IP directly, allowing:
- Product fetching via API
- Cart-based availability checking
- Full delivery checks

### Termux Setup
```bash
pkg install python
pip install -r requirements.txt
cp .env.example .env
nano .env  # Add your TELEGRAM_BOT_TOKEN and set NO_PROXY=true
python bot.py
```

## Running with Indian Proxies
If you have Indian residential proxies, set in `.env`:
```
INDIAN_PROXY=103.x.x.x:8080
PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password
```

## Technical Notes
- Pure API-based, no browser automation
- Uses requests library only
- Global lock ensures only one check runs at a time
- Per-user callbacks route notifications to correct user
- Auto-check processes all users sequentially
- All URLs for a user are processed in sequence during each check
- Concurrent updates enabled for responsive bot during checks

## Recent Changes
- 2026-01-29: Removed Playwright/Selenium - now fully API-based
- 2026-01-29: Added .env file support with python-dotenv
- 2026-01-29: Added requirements.txt for Termux compatibility
- 2026-01-29: Implemented API-based OTP login (no browser)
- 2026-01-29: Added cart-based availability check
- 2026-01-29: Added NO_PROXY and INDIAN_PROXY environment variables
- 2026-01-29: Added proxy rotation support (50 proxies with authentication)
- 2026-01-28: Reduced auto-check interval to 2 minutes
- 2026-01-28: Added OTP login with /login and /otp commands
- 2026-01-28: Added multiple URL support per user
- 2026-01-28: Implemented multi-user support with isolated JSON storage
