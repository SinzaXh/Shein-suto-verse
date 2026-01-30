"""
Configuration settings for SHEIN Verse Product Monitor Bot.

Fully defined configuration.
Supports .env file for Termux compatibility.
No empty or undefined values.
"""

import os
from pathlib import Path

# --------------------------------------------------
# Load .env file
# --------------------------------------------------
try:
    from dotenv import load_dotenv
    env_path = Path(".") / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("[CONFIG] Loaded .env file")
except ImportError:
    print("[CONFIG] python-dotenv not installed")

# --------------------------------------------------
# TELEGRAM CONFIGURATION
# --------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "7201368733:AAG3Yp-E5g-DExLHEN-ETrv74zeqwuTIhNM"
)

if ":" not in TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Invalid TELEGRAM_BOT_TOKEN")

# Allowed users (comma separated)
TELEGRAM_CHAT_IDS = os.environ.get(
    "TELEGRAM_CHAT_IDS",
    "7194175926,1950577113"
).split(",")

TELEGRAM_CHAT_IDS = [cid.strip() for cid in TELEGRAM_CHAT_IDS]

# --------------------------------------------------
# SCRAPER CONFIGURATION
# --------------------------------------------------

MAX_PRODUCTS = int(os.environ.get("MAX_PRODUCTS", "90"))
CACHE_EXPIRY_MINUTES = int(os.environ.get("CACHE_EXPIRY_MINUTES", "10"))
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "1"))

# --------------------------------------------------
# HUMAN-LIKE DELAYS
# --------------------------------------------------

DEFAULT_WAIT_MIN = float(os.environ.get("DEFAULT_WAIT_MIN", "1.5"))
DEFAULT_WAIT_MAX = float(os.environ.get("DEFAULT_WAIT_MAX", "3.0"))

# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    "./shein_monitor.db"
)

# --------------------------------------------------
# LOGGING
# --------------------------------------------------

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# --------------------------------------------------
# FINAL SAFETY LOG
# --------------------------------------------------

print("[CONFIG] Token loaded ✔")
print("[CONFIG] Allowed users:", TELEGRAM_CHAT_IDS)
print("[CONFIG] Max products:", MAX_PRODUCTS)
print("[CONFIG] Check interval:", CHECK_INTERVAL_MINUTES, "minute(s)")
print("[CONFIG] Cache expiry:", CACHE_EXPIRY_MINUTES, "minutes")
print("[CONFIG] Database:", DATABASE_PATH)
print("[CONFIG] Log level:", LOG_LEVEL)
