"""
SHEIN Verse Product Monitor - Telegram Bot

Interactive bot with commands to configure and control monitoring.
Auto-check runs on a schedule without requiring commands.
Supports MULTIPLE USERS with isolated JSON storage per user.
"""
import asyncio
import concurrent.futures
import requests
import re
import json
from datetime import datetime, timedelta
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from typing import Dict
import config
import user_database

user_check_in_progress = {}
user_notification_queues: Dict[str, asyncio.Queue] = {}
user_login_state = {}
next_check_time = None
thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

def get_user_queue(user_id: str) -> asyncio.Queue:
    """Get or create an async notification queue for a user."""
    if user_id not in user_notification_queues:
        user_notification_queues[user_id] = asyncio.Queue()
    return user_notification_queues[user_id]

def is_user_check_in_progress(user_id: str) -> bool:
    """Check if a check is in progress for a specific user."""
    return user_check_in_progress.get(user_id, False)

def set_user_check_in_progress(user_id: str, in_progress: bool):
    """Set the check in progress status for a specific user."""
    user_check_in_progress[user_id] = in_progress



def is_authorized(update: Update) -> bool:
    """Check if the user is authorized to use this bot."""
    chat_id = str(update.effective_chat.id)
    return user_database.is_authorized_user(chat_id)


def get_user_id(update: Update) -> str:
    """Get the user ID from the update."""
    return str(update.effective_chat.id)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Welcome message and setup instructions."""
    if not is_authorized(update):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return
    
    user_id = get_user_id(update)
    
    welcome_message = (
        "SHEIN Verse Product Monitor\n\n"
        f"Welcome User: {user_id}\n\n"
        "I automatically check SHEIN Verse products and notify you when they're available for delivery to your pincode.\n\n"
        "COMMANDS:\n"
        "/mystatus - View your personal configuration\n"
        "/seturl <url> - Set your SHEIN filtered URL\n"
        "/setpin <codes> - Add pincodes\n"
        "/rmpin <codes> - Remove pincodes\n"
        "/listpin - List all pincodes\n"
        "/settoken - Set SHEIN auth token (for API access)\n"
        "/check - Run a check now\n"
        "/help - Show help\n\n"
        f"Auto-check runs every {config.CHECK_INTERVAL_MINUTES} minutes."
    )
    
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    if not is_authorized(update):
        return
    
    help_text = (
        "SHEIN Monitor Bot Help\n\n"
        "LOGIN (OTP):\n"
        "/login <phone> - Start OTP login\n"
        "/otp <code> - Complete login with OTP\n\n"
        "URL MANAGEMENT:\n"
        "/seturl <url> - Add a SHEIN filtered URL\n"
        "/seturl - View your current URLs\n"
        "/rmurl - Remove URLs (with buttons)\n\n"
        "PINCODE MANAGEMENT:\n"
        "/setpin <codes> - Add pincodes\n"
        "/rmpin <codes> - Remove pincodes\n"
        "/listpin - List all pincodes\n\n"
        "MONITORING:\n"
        "/mystatus - View your configuration\n"
        "/check - Run manual check now\n"
        "/resend - Resend pending notifications\n"
        "/clearseen - Clear seen products (re-check all)\n\n"
        "TIPS:\n"
        "- Use /login for OTP-based login\n"
        "- You can add multiple URLs to monitor\n"
        "- Use /resend if notifications were missed"
    )
    await update.message.reply_text(help_text)




async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mystatus command - Show user's personal configuration."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    urls = user_database.get_user_urls(user_id)
    pincodes = user_database.get_user_pincodes(user_id)
    stats = user_database.get_user_stats(user_id)
    data = user_database.load_user_data(user_id)
    last_check = data.get("lastCheckedTimestamp")
    
    if urls:
        url_list = "\n".join([f"  {i+1}. {u[:50]}..." for i, u in enumerate(urls)])
    else:
        url_list = "  Not configured"
    
    pincodes_str = ', '.join(pincodes) if pincodes else "None configured"
    last_check_str = last_check if last_check else "Never"
    
    global next_check_time
    if next_check_time:
        next_check_str = next_check_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        next_check_str = f"Every {config.CHECK_INTERVAL_MINUTES} minutes"
    
    status_text = (
        f"Your Configuration (User: {user_id})\n\n"
        f"Check Interval: {config.CHECK_INTERVAL_MINUTES} minutes\n"
        f"Pincodes ({len(pincodes)}): {pincodes_str}\n\n"
        f"URLs ({len(urls)}):\n{url_list}\n\n"
        "Statistics:\n"
        f"  Products seen: {stats['seen_products']}\n"
        f"  Deliveries found: {stats['total_deliveries']}\n"
        f"  Pending notifications: {stats['pending_notifications']}\n\n"
        f"Last check: {last_check_str}\n"
        f"Next check: {next_check_str}"
    )
    
    await update.message.reply_text(status_text)


async def seturl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /seturl command - Add a SHEIN filtered URL for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    if not context.args:
        urls = user_database.get_user_urls(user_id)
        if urls:
            url_list = "\n".join([f"{i+1}. {u[:60]}..." for i, u in enumerate(urls)])
            await update.message.reply_text(
                f"Your current URLs:\n{url_list}\n\n"
                "Usage: /seturl <url> to add a new URL\n"
                "Use /rmurl to remove URLs"
            )
        else:
            await update.message.reply_text(
                "No URLs configured.\n\n"
                "Usage: /seturl <your-shein-url>\n\n"
                "Example:\n"
                "/seturl https://www.sheinindia.in/c/sverse-5939-37961?query=..."
            )
        return
    
    url = ' '.join(context.args)
    
    if not url.startswith('https://'):
        await update.message.reply_text("URL must start with https://")
        return
    
    if 'shein' not in url.lower():
        await update.message.reply_text("This doesn't look like a SHEIN URL.")
        return
    
    if user_database.add_user_url(user_id, url):
        urls = user_database.get_user_urls(user_id)
        url_display = url[:60] + "..." if len(url) > 60 else url
        await update.message.reply_text(
            f"URL Added!\n\n"
            f"Added: {url_display}\n"
            f"Total URLs: {len(urls)}\n\n"
            "Use /rmurl to manage URLs\n"
            "Use /check to test monitoring"
        )
    else:
        await update.message.reply_text("URL already exists in your list.")


async def rmurl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rmurl command - Show inline buttons to remove URLs."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    urls = user_database.get_user_urls(user_id)
    
    if not urls:
        await update.message.reply_text("No URLs to remove. Add URLs with /seturl")
        return
    
    keyboard = []
    for i, url in enumerate(urls):
        url_short = url.split('?')[0][-40:] if '?' in url else url[-40:]
        keyboard.append([InlineKeyboardButton(f"Remove: ...{url_short}", callback_data=f"rmurl_{i}")])
    
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="rmurl_cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a URL to remove:", reply_markup=reply_markup)


async def rmurl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callback for removing URLs."""
    query = update.callback_query
    
    try:
        await query.answer()
        print(f"[BOT] rmurl_callback triggered: {query.data}")
        
        user_id = str(query.from_user.id)
        
        if not user_database.is_authorized_user(user_id):
            await query.edit_message_text("Not authorized.")
            return
        
        data = query.data
        
        if data == "rmurl_cancel":
            await query.edit_message_text("Cancelled.")
            return
        
        if data.startswith("rmurl_"):
            try:
                index = int(data.split("_")[1])
                removed = user_database.remove_user_url(user_id, index)
                if removed:
                    removed_short = removed[:60] + "..." if len(removed) > 60 else removed
                    await query.edit_message_text(f"Removed URL:\n{removed_short}")
                    print(f"[BOT] Removed URL for user {user_id}: {removed_short}")
                else:
                    await query.edit_message_text("URL not found or already removed.")
            except (ValueError, IndexError) as e:
                print(f"[BOT] Error in rmurl_callback: {e}")
                await query.edit_message_text("Error removing URL.")
    except Exception as e:
        print(f"[BOT] rmurl_callback exception: {e}")
        try:
            await query.edit_message_text(f"Error: {str(e)[:50]}")
        except:
            pass


async def setpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setpin command - Add pincodes for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    if not context.args:
        await update.message.reply_text(
            "Please provide pincodes.\n\n"
            "Usage: /setpin <pincode1> <pincode2> ...\n\n"
            "Examples:\n"
            "/setpin 335704\n"
            "/setpin 335704 110001 400001"
        )
        return
    
    valid_pincodes = []
    invalid_pincodes = []
    
    for arg in context.args:
        for p in arg.replace(',', ' ').split():
            p = p.strip()
            if p.isdigit() and 5 <= len(p) <= 6:
                valid_pincodes.append(p)
            elif p:
                invalid_pincodes.append(p)
    
    if invalid_pincodes:
        await update.message.reply_text(
            f"Invalid pincodes (must be 5-6 digits): {', '.join(invalid_pincodes)}"
        )
        if not valid_pincodes:
            return
    
    added = user_database.add_user_pincodes(user_id, valid_pincodes)
    
    if added:
        current_pincodes = user_database.get_user_pincodes(user_id)
        await update.message.reply_text(
            f"Added: {', '.join(added)}\n\n"
            f"Current pincodes ({len(current_pincodes)}): {', '.join(current_pincodes)}"
        )
    else:
        await update.message.reply_text(
            "Pincodes already exist or nothing to add."
        )


async def rmpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rmpin command - Remove pincodes for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    if not context.args:
        await update.message.reply_text(
            "Please provide pincodes to remove.\n\n"
            "Usage: /rmpin <pincode1> <pincode2> ...\n\n"
            "Example: /rmpin 110001 400001"
        )
        return
    
    pincodes_to_remove = []
    for arg in context.args:
        for p in arg.replace(',', ' ').split():
            p = p.strip()
            if p:
                pincodes_to_remove.append(p)
    
    removed = user_database.remove_user_pincodes(user_id, pincodes_to_remove)
    
    if removed:
        current_pincodes = user_database.get_user_pincodes(user_id)
        if current_pincodes:
            await update.message.reply_text(
                f"Removed: {', '.join(removed)}\n\n"
                f"Remaining pincodes ({len(current_pincodes)}): {', '.join(current_pincodes)}"
            )
        else:
            await update.message.reply_text(
                f"Removed: {', '.join(removed)}\n\n"
                "No pincodes configured."
            )
    else:
        await update.message.reply_text("No matching pincodes found to remove.")


async def listpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listpin command - List all pincodes for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    pincodes = user_database.get_user_pincodes(user_id)
    
    if pincodes:
        await update.message.reply_text(
            f"Configured Pincodes ({len(pincodes)}):\n\n"
            + '\n'.join(pincodes)
        )
    else:
        await update.message.reply_text("No pincodes configured.")


async def settoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settoken command - Set SHEIN auth cookies for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    if not context.args:
        current_token = user_database.get_user_auth_cookies(user_id)
        status = "Set" if current_token else "Not set"
        
        await update.message.reply_text(
            f"SHEIN Auth Cookies: {status}\n\n"
            "To set your auth cookies:\n\n"
            "1. Open SHEIN India in your browser (logged in)\n"
            "2. Open Developer Tools (F12)\n"
            "3. Go to Network tab\n"
            "4. Click on any request to sheinindia.in\n"
            "5. Find 'Cookie' in Request Headers\n"
            "6. Copy the ENTIRE cookie value\n"
            "7. Send: /settoken <cookie_value>\n\n"
            "This enables API-based delivery checking."
        )
        return
    
    cookies = ' '.join(context.args)
    
    if 'deviceId' not in cookies and 'V=' not in cookies:
        await update.message.reply_text(
            "This doesn't look like valid SHEIN cookies.\n"
            "Please copy the entire Cookie header value from your browser."
        )
        return
    
    if user_database.set_user_auth_cookies(user_id, cookies):
        await update.message.reply_text(
            "Auth cookies saved!\n\n"
            "API-based delivery checking is now enabled.\n"
            "Use /check to test it."
        )
    else:
        await update.message.reply_text("Failed to save cookies. Please try again.")




async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command - Start SHEIN OTP login via API."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    global user_login_state
    
    if not context.args:
        await update.message.reply_text(
            "SHEIN OTP Login\n\n"
            "Usage: /login <phone_number>\n"
            "Example: /login 9876543210\n\n"
            "This will send an OTP to your phone. Then use /otp <code> to complete login."
        )
        return
    
    phone_number = context.args[0].strip()
    
    if not phone_number.isdigit() or len(phone_number) < 10:
        await update.message.reply_text("Please enter a valid 10-digit phone number.")
        return
    
    await update.message.reply_text(f"Requesting OTP for {phone_number}...")
    
    try:
        from scraper import api_login_request_otp
        result = api_login_request_otp(phone_number)
        
        if result.get("success"):
            user_login_state[user_id] = {"phone": phone_number, "waiting_otp": True}
            await update.message.reply_text(
                f"OTP sent to {phone_number}!\n\n"
                "Enter the OTP code using:\n"
                "/otp <code>\n\n"
                "Example: /otp 123456"
            )
        else:
            error = result.get("error", "Unknown error")
            await update.message.reply_text(f"Failed to request OTP: {error}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def otp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /otp command - Complete SHEIN OTP login via API."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    global user_login_state
    
    if not context.args:
        await update.message.reply_text(
            "OTP Verification\n\n"
            "Usage: /otp <code>\n"
            "Example: /otp 123456\n\n"
            "First start login with /login <phone_number>"
        )
        return
    
    if user_id not in user_login_state or not user_login_state[user_id].get("waiting_otp"):
        await update.message.reply_text(
            "No pending login. Please start with /login <phone_number> first."
        )
        return
    
    otp_code = context.args[0].strip()
    phone_number = user_login_state[user_id].get("phone")
    
    if not otp_code.isdigit() or len(otp_code) < 4:
        await update.message.reply_text("Please enter a valid OTP code (4-6 digits).")
        return
    
    if not phone_number:
        await update.message.reply_text("Phone number not found. Please start again with /login <phone>")
        return
    
    await update.message.reply_text("Verifying OTP...")
    
    try:
        from scraper import api_login_verify_otp
        result = api_login_verify_otp(phone_number, otp_code)
        
        if result.get("success"):
            user_login_state[user_id] = {"phone": phone_number, "waiting_otp": False, "logged_in": True}
            
            cookies = result.get("cookies", "")
            if cookies:
                user_database.set_auth_cookies(user_id, cookies)
                print(f"[LOGIN] Saved auth cookies for user {user_id}")
            
            await update.message.reply_text(
                "Login successful!\n\n"
                "Your SHEIN session is saved."
            )
        else:
            error = result.get("error", "Unknown error")
            await update.message.reply_text(f"OTP verification failed: {error}\n\nTry again with /login <phone>")
            user_login_state[user_id] = {}
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - Run a manual check for this user."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    if is_user_check_in_progress(user_id):
        await update.message.reply_text("A check is already in progress for you. Please wait...")
        return
    
    urls = user_database.get_user_urls(user_id)
    pincodes = user_database.get_user_pincodes(user_id)
    
    if not urls:
        await update.message.reply_text(
            "No URL configured!\n\n"
            "Use /seturl to set your SHEIN filtered URL first."
        )
        return
    
    url_display = f"{len(urls)} URL(s) configured"
    pincodes_str = ', '.join(pincodes) if pincodes else "None"
    
    await update.message.reply_text(
        "Starting check...\n\n"
        f"URL: {url_display}\n"
        f"Pincodes: {pincodes_str}\n\n"
        "This may take a few minutes..."
    )
    
    await run_check_for_user(user_id, update.effective_chat.id, context)


async def resend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resend command - Resend all unnotified deliveries."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    chat_id = update.effective_chat.id
    
    deliverables = user_database.get_user_new_deliverables(user_id)
    
    if not deliverables:
        await update.message.reply_text("No pending notifications to send.")
        return
    
    await update.message.reply_text(f"Sending {len(deliverables)} pending notifications...")
    
    sent = 0
    for product_url, pincode in deliverables:
        try:
            message = (
                "DELIVERY AVAILABLE!\n\n"
                f"PINCODE: {pincode}\n"
                f"LINK: {product_url}"
            )
            await context.bot.send_message(chat_id=chat_id, text=message)
            sent += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[BOT] Error sending notification: {e}")
    
    await update.message.reply_text(f"Sent {sent} notifications!")


async def clearseen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearseen command - Clear all seen products to re-check."""
    if not is_authorized(update):
        return
    
    user_id = get_user_id(update)
    
    data = user_database.load_user_data(user_id)
    old_count = len(data.get("seenProducts", []))
    data["seenProducts"] = []
    user_database.save_user_data(user_id, data)
    
    await update.message.reply_text(
        f"Cleared {old_count} seen products.\n\n"
        "Next check will treat all products as new!"
    )


async def auto_check_job(context: ContextTypes.DEFAULT_TYPE):
    """Job callback for automatic scheduled checks - processes ALL users."""
    global next_check_time
    
    next_check_time = datetime.now() + timedelta(minutes=config.CHECK_INTERVAL_MINUTES)
    
    # Run checks as background task to avoid blocking message handlers
    asyncio.create_task(run_all_user_checks(context))


async def run_all_user_checks(context: ContextTypes.DEFAULT_TYPE):
    """Run checks for all users sequentially in background."""
    for user_id in user_database.get_all_authorized_users():
        try:
            await run_check_for_user(user_id, int(user_id), context, silent_if_empty=True)
            # Yield control to allow message handlers to run
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[BOT] Error checking user {user_id}: {e}")


def create_user_callback(user_id: str, loop: asyncio.AbstractEventLoop):
    """Create a user-specific callback for new product notifications."""
    def callback(product_url: str):
        user_queue = get_user_queue(user_id)
        loop.call_soon_threadsafe(user_queue.put_nowait, product_url)
    return callback


async def process_notification_queue(bot, chat_id: int, user_id: str, stop_event: asyncio.Event):
    """Process the notification queue and send instant messages for a specific user."""
    user_queue = get_user_queue(user_id)
    
    while not stop_event.is_set():
        try:
            product_url = await asyncio.wait_for(user_queue.get(), timeout=0.3)
            
            message = (
                "NEW PRODUCT FOUND!\n\n"
                f"LINK: {product_url}\n\n"
                "Checking delivery availability..."
            )
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"[BOT] Sent instant notification for new product")
            
        except asyncio.TimeoutError:
            await asyncio.sleep(0.1)
            continue
        except Exception as e:
            print(f"[BOT] Error sending instant notification: {e}")


def run_scraper_inline(user_id: str, notification_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Run scraper inline with real-time notifications.
    Called from thread pool - sends notifications immediately as products are found.
    """
    import scraper
    
    urls = user_database.get_user_urls(user_id)
    pincodes = user_database.get_user_pincodes(user_id)
    user_cookies = user_database.get_auth_cookies(user_id)
    
    if not urls:
        return {"status": "no_urls", "new_products": 0, "deliverable": 0}
    
    print(f"[SCRAPER] Starting check for user {user_id}")
    print(f"[SCRAPER] URLs: {len(urls)} configured")
    print(f"[SCRAPER] Pincodes: {', '.join(pincodes) if pincodes else 'None'}")
    
    if user_cookies:
        print(f"[SCRAPER] Using user's auth cookies")
    
    scraper_instance = scraper.get_scraper()
    total_new = 0
    total_deliverable = 0
    
    from scraper import IS_TERMUX, get_indian_proxy
    can_check_availability = IS_TERMUX or get_indian_proxy() is not None
    
    for url_index, filtered_url in enumerate(urls):
        print(f"[SCRAPER] Processing URL {url_index + 1}/{len(urls)}")
        
        try:
            products_data = scraper_instance.fetch_products_api(filtered_url, user_cookies)
            
            if not products_data:
                print(f"[SCRAPER] No products found from this URL")
                continue
            
            print(f"[SCRAPER] API returned {len(products_data)} products")
            
            for product in products_data:
                product_url = product.get('url', f"https://www.sheinindia.in/p/{product.get('code', '')}")
                product_code = product.get('code', '')
                
                if not product_code:
                    continue
                
                if user_database.is_product_seen(user_id, product_url):
                    continue
                
                total_new += 1
                print(f"[SCRAPER] NEW: {product_url}")
                
                is_available = None
                if can_check_availability and user_cookies:
                    is_available = scraper_instance.check_availability_via_cart(product_code, user_cookies)
                
                if is_available is False:
                    print(f"[SCRAPER] Product {product_code} NOT available - skipping")
                    user_database.mark_product_seen(user_id, product_url)
                    continue
                
                for pincode in pincodes:
                    is_deliverable = scraper_instance.check_delivery_via_api(product_code, pincode, user_cookies)
                    
                    if is_deliverable:
                        is_new = user_database.save_delivery_result(user_id, product_url, pincode)
                        if is_new:
                            total_deliverable += 1
                            print(f"[SCRAPER] DELIVERABLE: {product_url} -> {pincode}")
                            
                            notification = {
                                "type": "delivery",
                                "product_url": product_url,
                                "pincode": pincode
                            }
                            loop.call_soon_threadsafe(notification_queue.put_nowait, notification)
                    else:
                        print(f"[SCRAPER] NOT deliverable: {product_url} -> {pincode}")
                
                user_database.mark_product_seen(user_id, product_url)
                
        except Exception as e:
            print(f"[SCRAPER] Error processing URL: {e}")
            continue
    
    return {"status": "ok", "new_products": total_new, "deliverable": total_deliverable}


async def send_notifications_realtime(bot, chat_id: int, notification_queue: asyncio.Queue, stop_event: asyncio.Event):
    """Send notifications in real-time as they arrive in the queue."""
    while not stop_event.is_set():
        try:
            notification = await asyncio.wait_for(notification_queue.get(), timeout=0.3)
            
            if notification.get("type") == "delivery":
                message = (
                    "DELIVERY AVAILABLE!\n\n"
                    f"PINCODE: {notification['pincode']}\n"
                    f"LINK: {notification['product_url']}"
                )
                await bot.send_message(chat_id=chat_id, text=message)
                print(f"[BOT] Sent instant notification for {notification['product_url']}")
                
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[BOT] Error sending notification: {e}")


async def run_check_for_user(user_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, silent_if_empty: bool = False):
    """
    Run a product check for a specific user with their isolated data.
    Sends notifications INSTANTLY as products are found.
    """
    if is_user_check_in_progress(user_id):
        return
    
    set_user_check_in_progress(user_id, True)
    bot = context.bot if context else Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    notification_queue = asyncio.Queue()
    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    
    notification_task = asyncio.create_task(
        send_notifications_realtime(bot, chat_id, notification_queue, stop_event)
    )
    
    try:
        print(f"\n{'='*50}")
        print(f"[BOT] Check started for user {user_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        result = await loop.run_in_executor(
            thread_executor,
            run_scraper_inline,
            user_id,
            notification_queue,
            loop
        )
        
        await asyncio.sleep(0.5)
        stop_event.set()
        
        try:
            await asyncio.wait_for(notification_task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            notification_task.cancel()
        
        new_count = result.get('new_products', 0)
        deliverable_count = result.get('deliverable', 0)
        
        print(f"[BOT] Check complete: {new_count} new, {deliverable_count} deliverable")
        
        if deliverable_count == 0 and not silent_if_empty:
            stats = user_database.get_user_stats(user_id)
            await bot.send_message(
                chat_id=chat_id, 
                text=(
                    "Check Complete\n\n"
                    f"Products seen: {stats['seen_products']}\n"
                    f"Deliveries found: {stats['total_deliveries']}\n"
                    "No new matches this time."
                )
            )
        
        user_database.cleanup_user_old_entries(user_id)
        user_database.update_user_last_check(user_id)
        
        stats = user_database.get_user_stats(user_id)
        print(f"[BOT] User {user_id} Stats: {stats}")
        
    except Exception as e:
        print(f"[BOT] Error during check for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        if not silent_if_empty:
            try:
                await bot.send_message(chat_id=chat_id, text=f"Error during check: {str(e)[:100]}")
            except Exception:
                pass
    finally:
        stop_event.set()
        try:
            notification_task.cancel()
        except Exception:
            pass
        set_user_check_in_progress(user_id, False)


async def post_init(application: Application):
    """Called after the application is initialized."""
    global next_check_time
    
    job_queue = application.job_queue
    
    next_check_time = datetime.now() + timedelta(seconds=30)
    
    job_queue.run_repeating(
        auto_check_job,
        interval=config.CHECK_INTERVAL_MINUTES * 60,
        first=30,
        name='auto_check'
    )
    
    print(f"[BOT] Auto-check scheduled every {config.CHECK_INTERVAL_MINUTES} minutes")
    print(f"[BOT] First check in 30 seconds")
    print(f"[BOT] Authorized users: {', '.join(user_database.get_all_authorized_users())}")


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("   SHEIN VERSE PRODUCT MONITOR (MULTI-USER)")
    print("="*60)
    print(f"  Check Interval: {config.CHECK_INTERVAL_MINUTES} minutes")
    print(f"  Authorized Users: {', '.join(user_database.get_all_authorized_users())}")
    print("="*60 + "\n")
    
    for user_id in user_database.get_all_authorized_users():
        data = user_database.load_user_data(user_id)
        urls = data.get("monitorUrls", [])
        pincodes_count = len(data.get("pincodes", []))
        print(f"[DB] User {user_id}: URLs={len(urls)}, Pincodes={pincodes_count}")
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).concurrent_updates(True).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mystatus", mystatus_command))
    app.add_handler(CommandHandler("seturl", seturl_command))
    app.add_handler(CommandHandler("Seturl", seturl_command))
    app.add_handler(CommandHandler("rmurl", rmurl_command))
    app.add_handler(CommandHandler("Rmurl", rmurl_command))
    app.add_handler(CallbackQueryHandler(rmurl_callback, pattern="^rmurl_"))
    
    async def debug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        print(f"[BOT] Unknown callback received: {query.data}")
        await query.answer("Unknown action")
    app.add_handler(CallbackQueryHandler(debug_callback))
    app.add_handler(CommandHandler("setpin", setpin_command))
    app.add_handler(CommandHandler("rmpin", rmpin_command))
    app.add_handler(CommandHandler("listpin", listpin_command))
    app.add_handler(CommandHandler("settoken", settoken_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("otp", otp_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("resend", resend_command))
    app.add_handler(CommandHandler("clearseen", clearseen_command))
    
    print("[BOT] Bot started! Waiting for commands...")
    print("[BOT] Auto-check will run automatically on schedule")
    
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
