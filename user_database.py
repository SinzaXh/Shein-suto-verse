"""
Per-User JSON Database Module for SHEIN Verse Product Monitor.

Handles separate storage per user with full isolation.
Each user gets their own JSON file: data/user_{userId}.json
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DATA_DIR = "./data"

def _load_authorized_users() -> List[str]:
    """Load authorized users from environment variable or use defaults."""
    env_users = os.environ.get('AUTHORIZED_USERS', '')
    if env_users:
        return [u.strip() for u in env_users.split(',') if u.strip()]
    return ["7194175926", "1950577113"]

AUTHORIZED_USERS = _load_authorized_users()

def get_default_user_data(user_id: str) -> Dict[str, Any]:
    """Return default structure for a new user."""
    return {
        "userId": user_id,
        "monitorUrls": [],
        "pincodes": [],
        "authCookies": None,
        "lastKnownStock": 0,
        "lastCheckedTimestamp": None,
        "seenProducts": [],
        "deliveries": [],
        "settings": {}
    }


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def get_user_file_path(user_id: str) -> str:
    """Get the file path for a user's database."""
    return os.path.join(DATA_DIR, f"user_{user_id}.json")


def load_user_data(user_id: str) -> Dict[str, Any]:
    """Load user data from their JSON file. Creates default if not exists."""
    ensure_data_dir()
    file_path = get_user_file_path(user_id)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if "pincodes" not in data:
                    data["pincodes"] = []
                if "seenProducts" not in data:
                    data["seenProducts"] = []
                if "deliveries" not in data:
                    data["deliveries"] = []
                if "settings" not in data:
                    data["settings"] = {}
                if "monitorUrls" not in data:
                    old_url = data.get("monitorUrl")
                    data["monitorUrls"] = [old_url] if old_url else []
                    if "monitorUrl" in data:
                        del data["monitorUrl"]
                return data
        except json.JSONDecodeError:
            print(f"[USER_DB] Error reading {file_path}, creating new")
    
    default_data = get_default_user_data(user_id)
    save_user_data(user_id, default_data)
    return default_data


def save_user_data(user_id: str, data: Dict[str, Any]) -> bool:
    """Save user data to their JSON file."""
    ensure_data_dir()
    file_path = get_user_file_path(user_id)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"[USER_DB] Error saving {file_path}: {e}")
        return False


def is_authorized_user(user_id: str) -> bool:
    """Check if a user is in the authorized list."""
    return str(user_id) in AUTHORIZED_USERS


def get_all_authorized_users() -> List[str]:
    """Get list of all authorized user IDs."""
    return AUTHORIZED_USERS.copy()


def get_user_urls(user_id: str) -> List[str]:
    """Get all monitor URLs for a user."""
    data = load_user_data(user_id)
    return data.get("monitorUrls", [])


def add_user_url(user_id: str, url: str) -> bool:
    """Add a monitor URL for a user. Returns True if added, False if already exists."""
    data = load_user_data(user_id)
    urls = data.get("monitorUrls", [])
    if url not in urls:
        urls.append(url)
        data["monitorUrls"] = urls
        save_user_data(user_id, data)
        return True
    return False


def remove_user_url(user_id: str, url_index: int) -> Optional[str]:
    """Remove a monitor URL by index. Returns the removed URL or None."""
    data = load_user_data(user_id)
    urls = data.get("monitorUrls", [])
    if 0 <= url_index < len(urls):
        removed = urls.pop(url_index)
        data["monitorUrls"] = urls
        save_user_data(user_id, data)
        return removed
    return None


def get_auth_cookies(user_id: str) -> Optional[str]:
    """Get auth cookies for a user."""
    data = load_user_data(user_id)
    return data.get("authCookies")


def set_auth_cookies(user_id: str, cookies: str) -> bool:
    """Set auth cookies for a user."""
    data = load_user_data(user_id)
    data["authCookies"] = cookies
    return save_user_data(user_id, data)


def get_user_pincodes(user_id: str) -> List[str]:
    """Get all pincodes for a user."""
    data = load_user_data(user_id)
    return data.get("pincodes", [])


def add_user_pincodes(user_id: str, pincodes: List[str]) -> List[str]:
    """Add pincodes for a user. Returns list of newly added pincodes."""
    data = load_user_data(user_id)
    existing = set(data.get("pincodes", []))
    added = []
    
    for p in pincodes:
        if p not in existing:
            existing.add(p)
            added.append(p)
    
    data["pincodes"] = sorted(list(existing))
    save_user_data(user_id, data)
    return added


def remove_user_pincodes(user_id: str, pincodes: List[str]) -> List[str]:
    """Remove pincodes for a user. Returns list of removed pincodes."""
    data = load_user_data(user_id)
    existing = set(data.get("pincodes", []))
    removed = []
    
    for p in pincodes:
        if p in existing:
            existing.remove(p)
            removed.append(p)
    
    data["pincodes"] = sorted(list(existing))
    save_user_data(user_id, data)
    return removed


def get_user_auth_cookies(user_id: str) -> Optional[str]:
    """Get auth cookies for a user."""
    data = load_user_data(user_id)
    return data.get("authCookies")


def set_user_auth_cookies(user_id: str, cookies: str) -> bool:
    """Set auth cookies for a user."""
    data = load_user_data(user_id)
    data["authCookies"] = cookies
    return save_user_data(user_id, data)


def mark_product_seen(user_id: str, product_url: str) -> None:
    """Mark a product as seen for a user."""
    data = load_user_data(user_id)
    seen = data.get("seenProducts", [])
    if product_url not in seen:
        seen.append(product_url)
        data["seenProducts"] = seen
        save_user_data(user_id, data)


def is_product_seen(user_id: str, product_url: str) -> bool:
    """Check if a product has been seen by a user."""
    data = load_user_data(user_id)
    return product_url in data.get("seenProducts", [])


def save_delivery_result(user_id: str, product_url: str, pincode: str) -> bool:
    """Save a deliverable result for a user. Returns True if new."""
    data = load_user_data(user_id)
    deliveries = data.get("deliveries", [])
    
    for d in deliveries:
        if d["product_url"] == product_url and d["pincode"] == pincode:
            d["last_checked"] = datetime.now().isoformat()
            save_user_data(user_id, data)
            return False
    
    deliveries.append({
        "product_url": product_url,
        "pincode": pincode,
        "first_found": datetime.now().isoformat(),
        "last_checked": datetime.now().isoformat(),
        "notified": False
    })
    data["deliveries"] = deliveries
    save_user_data(user_id, data)
    return True


def get_user_new_deliverables(user_id: str) -> List[tuple]:
    """Get unnotified deliverables for a user. Returns list of (product_url, pincode)."""
    data = load_user_data(user_id)
    deliveries = data.get("deliveries", [])
    result = []
    
    for d in deliveries:
        if not d.get("notified", False):
            result.append((d["product_url"], d["pincode"]))
            d["notified"] = True
    
    if result:
        save_user_data(user_id, data)
    
    return result


def update_user_last_check(user_id: str) -> None:
    """Update the last check timestamp for a user."""
    data = load_user_data(user_id)
    data["lastCheckedTimestamp"] = datetime.now().isoformat()
    save_user_data(user_id, data)


def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get statistics for a user."""
    data = load_user_data(user_id)
    deliveries = data.get("deliveries", [])
    seen = data.get("seenProducts", [])
    pincodes = data.get("pincodes", [])
    
    pending = sum(1 for d in deliveries if not d.get("notified", False))
    
    return {
        "seen_products": len(seen),
        "total_deliveries": len(deliveries),
        "pending_notifications": pending,
        "pincode_count": len(pincodes)
    }


def cleanup_user_old_entries(user_id: str, max_seen: int = 500) -> int:
    """Cleanup old entries to prevent file bloat."""
    data = load_user_data(user_id)
    seen = data.get("seenProducts", [])
    
    if len(seen) > max_seen:
        data["seenProducts"] = seen[-max_seen:]
        save_user_data(user_id, data)
        return len(seen) - max_seen
    
    return 0
