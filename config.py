"""
Configuration settings for SHEIN Verse Product Monitor Bot.
Supports .env file for Termux compatibility.
"""

import os
from pathlib import Path

# --------------------------------------------------
# Load .env file
# --------------------------------------------------
try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("[CONFIG] Loaded .env file")
except ImportError:
    pass

# --------------------------------------------------
# TELEGRAM BOT CONFIGURATION
# --------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN or ":" not in TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Invalid or missing TELEGRAM_BOT_TOKEN")

# Multiple allowed users (admins)
TELEGRAM_CHAT_IDS = os.environ.get(
    "TELEGRAM_CHAT_IDS",
    "7194175926"
).split(",")

# Clean IDs
TELEGRAM_CHAT_IDS = [chat_id.strip() for chat_id in TELEGRAM_CHAT_IDS]

# --------------------------------------------------
# SCRAPING CONFIGURATION
# --------------------------------------------------

MAX_PRODUCTS = int(os.environ.get("MAX_PRODUCTS", "90"))
CACHE_EXPIRY_MINUTES = int(os.environ.get("CACHE_EXPIRY_MINUTES", "10"))
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "1"))

# --------------------------------------------------
# HUMAN-LIKE DELAYS
# --------------------------------------------------

DEFAULT_WAIT_MIN = 1.5
DEFAULT_WAIT_MAX = 3.0

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASE_PATH = "./shein_monitor.db"

# --------------------------------------------------
# DEBUG INFO
# --------------------------------------------------

print("[CONFIG] Bot token loaded")
print("[CONFIG] Allowed users:", TELEGRAM_CHAT_IDS)
print("[CONFIG] Max products:", MAX_PRODUCTS)
print("[CONFIG] Check interval (min):", CHECK_INTERVAL_MINUTES)