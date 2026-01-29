"""
SQLite Database Module for SHEIN Verse Product Monitor.

Handles storage of delivery results, seen products tracking,
pincodes management, and settings persistence.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import config


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table to track deliverable products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_url TEXT NOT NULL,
            pincode TEXT NOT NULL,
            source_url TEXT NOT NULL,
            last_checked TIMESTAMP NOT NULL,
            notified INTEGER DEFAULT 0,
            UNIQUE(product_url, pincode, source_url)
        )
    """)
    
    # Table to track seen products (to avoid reprocessing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_products (
            product_url TEXT PRIMARY KEY,
            source_url TEXT NOT NULL,
            first_seen TIMESTAMP NOT NULL
        )
    """)
    
    # Table for pincodes (user-configurable)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pincodes (
            pincode TEXT PRIMARY KEY,
            added_at TIMESTAMP NOT NULL
        )
    """)
    
    # Table for settings (key-value storage)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    
    # Index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_deliveries_notified 
        ON deliveries(notified)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_deliveries_last_checked 
        ON deliveries(last_checked)
    """)
    
    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully")


# ============================================================
# PINCODE MANAGEMENT FUNCTIONS
# ============================================================

def add_pincodes(pincodes: List[str]) -> List[str]:
    """
    Add one or more pincodes to the database.
    Returns list of successfully added pincodes (ignores duplicates).
    """
    conn = get_connection()
    cursor = conn.cursor()
    added = []
    
    for pincode in pincodes:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO pincodes (pincode, added_at)
                VALUES (?, ?)
            """, (pincode, datetime.now()))
            if cursor.rowcount > 0:
                added.append(pincode)
        except Exception as e:
            print(f"[DB] Error adding pincode {pincode}: {e}")
    
    conn.commit()
    conn.close()
    return added


def remove_pincodes(pincodes: List[str]) -> List[str]:
    """
    Remove one or more pincodes from the database.
    Returns list of removed pincodes (ignores non-existing).
    """
    conn = get_connection()
    cursor = conn.cursor()
    removed = []
    
    for pincode in pincodes:
        try:
            cursor.execute("""
                DELETE FROM pincodes WHERE pincode = ?
            """, (pincode,))
            if cursor.rowcount > 0:
                removed.append(pincode)
        except Exception as e:
            print(f"[DB] Error removing pincode {pincode}: {e}")
    
    conn.commit()
    conn.close()
    return removed


def get_pincodes() -> List[str]:
    """
    Get all configured pincodes from the database.
    Returns sorted list of pincodes.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT pincode FROM pincodes ORDER BY pincode ASC
    """)
    
    pincodes = [row['pincode'] for row in cursor.fetchall()]
    conn.close()
    return pincodes


def get_pincode_count() -> int:
    """Get the total number of configured pincodes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM pincodes")
    count = cursor.fetchone()['count']
    conn.close()
    return count


# ============================================================
# SETTINGS MANAGEMENT FUNCTIONS
# ============================================================

def set_setting(key: str, value: str) -> bool:
    """
    Set a setting value in the database.
    Creates or updates the setting.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error setting {key}: {e}")
        return False
    finally:
        conn.close()


def get_setting(key: str, default: str = None) -> Optional[str]:
    """
    Get a setting value from the database.
    Returns default if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT value FROM settings WHERE key = ?
    """, (key,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row['value']
    return default


def get_filtered_url() -> Optional[str]:
    """Get the configured SHEIN filtered URL from database."""
    return get_setting('FILTERED_URL')


def set_filtered_url(url: str) -> bool:
    """Set the SHEIN filtered URL in database."""
    return set_setting('FILTERED_URL', url)


def get_auth_token() -> Optional[str]:
    """Get the SHEIN auth token (A cookie value) from database."""
    return get_setting('AUTH_TOKEN')


def set_auth_token(token: str) -> bool:
    """Set the SHEIN auth token in database."""
    return set_setting('AUTH_TOKEN', token)


def get_auth_cookies() -> Optional[str]:
    """Get the full SHEIN auth cookies string from database."""
    return get_setting('AUTH_COOKIES')


def set_auth_cookies(cookies: str) -> bool:
    """Set the full SHEIN auth cookies in database."""
    return set_setting('AUTH_COOKIES', cookies)


def get_last_check_time() -> Optional[str]:
    """Get the last successful scrape time."""
    return get_setting('LAST_CHECK_TIME')


def set_last_check_time() -> bool:
    """Update the last check time to now."""
    return set_setting('LAST_CHECK_TIME', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# ============================================================
# DELIVERY TRACKING FUNCTIONS
# ============================================================

def save_result(product_url: str, pincode: str, source_url: str) -> bool:
    """
    Save a deliverable result to the database.
    Returns True if this is a NEW entry (should notify), False if it already exists.
    Uses explicit check to avoid SQLite UPSERT ambiguity.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First check if this combination already exists
        cursor.execute("""
            SELECT id, notified FROM deliveries 
            WHERE product_url = ? AND pincode = ? AND source_url = ?
        """, (product_url, pincode, source_url))
        
        existing = cursor.fetchone()
        
        if existing is None:
            # New entry - insert with notified=0
            cursor.execute("""
                INSERT INTO deliveries (product_url, pincode, source_url, last_checked, notified)
                VALUES (?, ?, ?, ?, 0)
            """, (product_url, pincode, source_url, datetime.now()))
            conn.commit()
            print(f"[DB] New deliverable saved: {pincode}")
            return True  # This is new, should notify
        else:
            # Already exists - just update timestamp, don't change notified flag
            cursor.execute("""
                UPDATE deliveries SET last_checked = ?
                WHERE product_url = ? AND pincode = ? AND source_url = ?
            """, (datetime.now(), product_url, pincode, source_url))
            conn.commit()
            return False  # Already notified before
            
    except Exception as e:
        print(f"[DB] Error saving result: {e}")
        return False
    finally:
        conn.close()


def is_recent(product_url: str, pincode: str, source_url: str) -> bool:
    """
    Check if this product/pincode combination was recently checked.
    Returns True if checked within CACHE_EXPIRY_MINUTES.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    expiry_time = datetime.now() - timedelta(minutes=config.CACHE_EXPIRY_MINUTES)
    
    cursor.execute("""
        SELECT 1 FROM deliveries 
        WHERE product_url = ? AND pincode = ? AND source_url = ? 
        AND last_checked > ?
    """, (product_url, pincode, source_url, expiry_time))
    
    result = cursor.fetchone() is not None
    conn.close()
    return result


def mark_seen(product_url: str, source_url: str) -> None:
    """Mark a product as seen (processed)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO seen_products (product_url, source_url, first_seen)
            VALUES (?, ?, ?)
        """, (product_url, source_url, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"[DB] Error marking seen: {e}")
    finally:
        conn.close()


def is_seen(product_url: str, source_url: str) -> bool:
    """Check if a product has already been seen/processed."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 1 FROM seen_products 
        WHERE product_url = ? AND source_url = ?
    """, (product_url, source_url))
    
    result = cursor.fetchone() is not None
    conn.close()
    return result


def get_new_deliverables() -> List[Tuple[str, str]]:
    """
    Get all deliverable products that haven't been notified yet.
    Returns list of (product_url, pincode) tuples.
    Marks them as notified after retrieval.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, product_url, pincode FROM deliveries 
        WHERE notified = 0
        ORDER BY last_checked DESC
    """)
    
    results = cursor.fetchall()
    deliverables = [(row['product_url'], row['pincode']) for row in results]
    
    # Mark all as notified
    if results:
        ids = [row['id'] for row in results]
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f"""
            UPDATE deliveries SET notified = 1 
            WHERE id IN ({placeholders})
        """, ids)
        conn.commit()
    
    conn.close()
    return deliverables


def cleanup_old_entries(days: int = 7) -> int:
    """
    Remove entries older than specified days.
    Returns the number of entries removed.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(days=days)
    
    # Clean up old deliveries
    cursor.execute("""
        DELETE FROM deliveries WHERE last_checked < ?
    """, (cutoff_time,))
    deliveries_deleted = cursor.rowcount
    
    # Clean up old seen products
    cursor.execute("""
        DELETE FROM seen_products WHERE first_seen < ?
    """, (cutoff_time,))
    seen_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    total_deleted = deliveries_deleted + seen_deleted
    if total_deleted > 0:
        print(f"[DB] Cleaned up {total_deleted} old entries")
    
    return total_deleted


def get_stats() -> dict:
    """Get database statistics for debugging."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM seen_products")
    seen_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM deliveries")
    delivery_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM deliveries WHERE notified = 0")
    pending_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM pincodes")
    pincode_count = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'seen_products': seen_count,
        'total_deliveries': delivery_count,
        'pending_notifications': pending_count,
        'pincode_count': pincode_count
    }
