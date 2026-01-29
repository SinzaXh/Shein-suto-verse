"""
API-based Scraper for SHEIN Verse Product Availability.

This module uses SHEIN India APIs directly to check product availability
and delivery options for specified pincodes.
No browser automation - pure API requests only.
"""
import os
import re
import random
import urllib.parse
import requests
from typing import List, Optional, Dict, Any
import config

# Proxy configuration - 50 proxies for rotation
PROXY_LIST = [
    "196.51.218.250:8800", "196.51.85.213:8800", "170.130.62.221:8800",
    "170.130.62.251:8800", "196.51.85.127:8800", "196.51.109.6:8800",
    "170.130.62.223:8800", "77.83.170.168:8800", "196.51.82.112:8800",
    "196.51.221.158:8800", "196.51.82.238:8800", "196.51.109.52:8800",
    "77.83.170.30:8800", "196.51.221.46:8800", "196.51.109.31:8800",
    "196.51.221.125:8800", "196.51.82.106:8800", "170.130.62.211:8800",
    "196.51.106.100:8800", "196.51.106.117:8800", "196.51.106.149:8800",
    "196.51.221.174:8800", "196.51.221.102:8800", "77.83.170.124:8800",
    "196.51.85.7:8800", "196.51.218.236:8800", "196.51.218.169:8800",
    "196.51.106.30:8800", "196.51.106.69:8800", "196.51.85.59:8800",
    "196.51.109.138:8800", "77.83.170.222:8800", "196.51.85.156:8800",
    "170.130.62.24:8800", "196.51.218.179:8800", "77.83.170.79:8800",
    "196.51.82.198:8800", "196.51.218.227:8800", "196.51.218.60:8800",
    "196.51.82.59:8800", "196.51.82.120:8800", "196.51.109.8:8800",
    "196.51.109.151:8800", "196.51.106.16:8800", "77.83.170.91:8800",
    "170.130.62.27:8800", "196.51.221.38:8800", "196.51.85.207:8800",
    "170.130.62.42:8800", "170.130.62.151:8800"
]

# Check if running on Termux (no proxy needed - Indian IP)
IS_TERMUX = os.environ.get('TERMUX_VERSION') is not None or os.environ.get('NO_PROXY', '').lower() == 'true'


def get_proxy():
    """Get a random proxy with authentication. Returns None if on Termux or NO_PROXY=true."""
    if IS_TERMUX:
        return None
    
    # Check for Indian proxy first (for delivery checks)
    indian_proxy = os.environ.get('INDIAN_PROXY', '')
    if indian_proxy:
        username = os.environ.get('PROXY_USERNAME', '')
        password = os.environ.get('PROXY_PASSWORD', '')
        if username and password:
            return {
                'http': f'http://{username}:{password}@{indian_proxy}',
                'https': f'http://{username}:{password}@{indian_proxy}'
            }
        return {
            'http': f'http://{indian_proxy}',
            'https': f'http://{indian_proxy}'
        }
    
    # Fallback to regular proxy list
    proxy_ip = random.choice(PROXY_LIST)
    username = os.environ.get('PROXY_USERNAME', '')
    password = os.environ.get('PROXY_PASSWORD', '')
    if username and password:
        return {
            'http': f'http://{username}:{password}@{proxy_ip}',
            'https': f'http://{username}:{password}@{proxy_ip}'
        }
    return None


def get_indian_proxy():
    """Get Indian proxy for delivery checks (cart API). Returns None if not available."""
    if IS_TERMUX:
        return None  # No proxy needed on Termux
    
    indian_proxy = os.environ.get('INDIAN_PROXY', '')
    if indian_proxy:
        username = os.environ.get('PROXY_USERNAME', '')
        password = os.environ.get('PROXY_PASSWORD', '')
        if username and password:
            return {
                'http': f'http://{username}:{password}@{indian_proxy}',
                'https': f'http://{username}:{password}@{indian_proxy}'
            }
        return {
            'http': f'http://{indian_proxy}',
            'https': f'http://{indian_proxy}'
        }
    return None


def extract_product_id(product_url: str) -> Optional[str]:
    """Extract base product ID from URL like /p/443336453_pink"""
    match = re.search(r'/p/(\d+)', product_url)
    if match:
        return match.group(1)
    return None


def api_login_request_otp(phone_number: str) -> Dict[str, Any]:
    """
    Request OTP via SHEIN API using cURL - sends OTP to phone.
    Returns dict with 'success', 'error' keys.
    """
    import subprocess
    import json as json_module
    
    try:
        print(f"[LOGIN] Requesting OTP for phone: {phone_number}")
        
        curl_cmd = [
            'curl', '-s', '-L', '--compressed',
            '-X', 'POST',
            '-H', 'accept: application/json',
            '-H', 'content-type: application/json',
            '-H', 'origin: https://www.sheinindia.in',
            '-H', 'referer: https://www.sheinindia.in/login?referrer=/my-account/',
            '-H', 'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            '-H', 'x-tenant-id: SHEIN',
            '-d', json_module.dumps({"mobileNumber": phone_number}),
            '--max-time', '20'
        ]
        
        proxy = get_proxy()
        if proxy:
            proxy_url = proxy.get('http', '') or proxy.get('https', '')
            if proxy_url:
                curl_cmd.extend(['--proxy', proxy_url])
        
        curl_cmd.append('https://www.sheinindia.in/api/auth/generateLoginOTP')
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=25)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if 'Access Denied' in output:
                return {"success": False, "error": "Access denied - try again"}
            print(f"[LOGIN] OTP sent to {phone_number}")
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": "Failed to send OTP request"}
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        print(f"[LOGIN] Error requesting OTP: {e}")
        return {"success": False, "error": str(e)}


def api_login_verify_otp(phone_number: str, otp: str) -> Dict[str, Any]:
    """
    Verify OTP via SHEIN API using cURL and return cookies on success.
    Returns dict with 'success', 'cookies' (string), 'error' keys.
    """
    import subprocess
    import json as json_module
    
    try:
        print(f"[LOGIN] Verifying OTP for {phone_number}")
        
        curl_cmd = [
            'curl', '-s', '-L', '--compressed',
            '-X', 'POST',
            '-H', 'accept: application/json',
            '-H', 'content-type: application/json',
            '-H', 'origin: https://www.sheinindia.in',
            '-H', 'referer: https://www.sheinindia.in/login/otp?referrer=/my-account/',
            '-H', 'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            '-H', 'x-tenant-id: SHEIN',
            '-d', json_module.dumps({"username": phone_number, "otp": otp}),
            '-c', '-',  # Output cookies to stdout
            '-D', '-',  # Output headers to stdout
            '--max-time', '20'
        ]
        
        proxy = get_proxy()
        if proxy:
            proxy_url = proxy.get('http', '') or proxy.get('https', '')
            if proxy_url:
                curl_cmd.extend(['--proxy', proxy_url])
        
        curl_cmd.append('https://www.sheinindia.in/api/auth/login')
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=25)
        
        if result.returncode != 0:
            return {"success": False, "cookies": None, "error": "Login request failed"}
        
        output = result.stdout
        
        if 'Access Denied' in output:
            return {"success": False, "cookies": None, "error": "Access denied - try again"}
        
        # Extract JSON from response (after headers)
        json_start = output.rfind('{')
        if json_start == -1:
            return {"success": False, "cookies": None, "error": "Invalid response"}
        
        try:
            resp_data = json_module.loads(output[json_start:])
        except:
            return {"success": False, "cookies": None, "error": "Could not parse response"}
        
        # Check for error in response
        if 'error' in resp_data or resp_data.get('statusCode', 0) >= 400:
            error_msg = resp_data.get('message', resp_data.get('error', 'Login failed'))
            return {"success": False, "cookies": None, "error": error_msg}
        
        # Build cookies from response
        cookies_dict = {}
        if 'accessToken' in resp_data:
            cookies_dict['A'] = resp_data['accessToken']
        if 'refreshToken' in resp_data:
            cookies_dict['R'] = resp_data['refreshToken']
        
        # Extract cookies from headers
        for line in output.split('\n'):
            if line.lower().startswith('set-cookie:'):
                cookie_part = line.split(':', 1)[1].strip()
                if '=' in cookie_part:
                    name_val = cookie_part.split(';')[0]
                    if '=' in name_val:
                        name, val = name_val.split('=', 1)
                        cookies_dict[name.strip()] = val.strip()
        
        # Add default cookies
        cookies_dict['LS'] = 'LOGGED_IN'
        cookies_dict['customerType'] = 'Existing'
        
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
        
        print(f"[LOGIN] Login successful! Got {len(cookies_dict)} cookies")
        
        return {
            "success": True,
            "cookies": cookie_string,
            "error": None
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "cookies": None, "error": "Request timed out"}
    except Exception as e:
        print(f"[LOGIN] Error verifying OTP: {e}")
        return {"success": False, "cookies": None, "error": str(e)}


def fetch_products_api(filtered_url: str, user_cookies: str = None) -> List[Dict[str, Any]]:
    """
    Fetch products via SHEIN API using cURL subprocess.
    Uses cURL to bypass blocking that Python requests might trigger.
    Returns list of product dicts with code, name, price, image, url.
    """
    import subprocess
    import json as json_module
    
    try:
        parsed = urllib.parse.urlparse(filtered_url)
        path_parts = parsed.path.strip('/').split('/')
        
        category_code = None
        for part in path_parts:
            if 'sverse' in part.lower() or part.startswith('c/'):
                category_code = part.replace('c/', '')
                break
        
        if not category_code:
            if len(path_parts) >= 2 and path_parts[0] == 'c':
                category_code = path_parts[1]
            elif len(path_parts) >= 1:
                category_code = path_parts[-1]
        
        if not category_code:
            print(f"[API] Could not extract category from URL: {filtered_url}")
            return []
        
        query_params = urllib.parse.parse_qs(parsed.query)
        facets = query_params.get('facets', [''])[0]
        
        default_facets = 'genderfilter:Men:verticalsizegroupformat:S:verticalsizegroupformat:M:verticalsizegroupformat:L:verticalsizegroupformat:28:verticalsizegroupformat:30'
        
        if not facets:
            facets = default_facets
        
        params = {
            'fields': 'SITE',
            'currentPage': '0',
            'pageSize': '60',
            'format': 'json',
            'gridColumns': '2',
            'segmentIds': '15,8,19',
            'customerType': 'Existing',
            'includeUnratedProducts': 'false',
            'advfilter': 'true',
            'platform': 'Desktop',
            'showAdsOnNextPage': 'false',
            'is_ads_enable_plp': 'true',
            'displayRatings': 'true',
            'customertype': 'Existing',
            'store': 'shein',
            'facets': facets,
            'query': f':relevance:{facets}'
        }
        
        query_string = urllib.parse.urlencode(params)
        api_url = f"https://www.sheinindia.in/api/category/{category_code}?{query_string}"
        
        base_cookies = 'V=1; deviceId=R8RkVsXwi4j0zW82Wu8iK; LS=LOGGED_IN; customerType=Existing; bookingType=SHEIN; storeTypes=shein;'
        cookies = user_cookies if user_cookies else base_cookies
        
        curl_cmd = [
            'curl', '-s', '-L', '--compressed',
            '-H', 'accept: application/json',
            '-H', 'accept-language: en-GB,en-US;q=0.9,en;q=0.8',
            '-H', f'referer: {filtered_url}',
            '-H', 'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            '-H', 'x-tenant-id: SHEIN',
            '-H', 'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
            '-H', 'sec-ch-ua-mobile: ?1',
            '-H', 'sec-ch-ua-platform: "Android"',
            '-H', 'sec-fetch-dest: empty',
            '-H', 'sec-fetch-mode: cors',
            '-H', 'sec-fetch-site: same-origin',
            '-H', f'cookie: {cookies}',
            '--max-time', '30'
        ]
        
        proxy = get_proxy()
        if proxy:
            proxy_url = proxy.get('http', '') or proxy.get('https', '')
            if proxy_url:
                curl_cmd.extend(['--proxy', proxy_url])
        
        curl_cmd.append(api_url)
        
        print(f"[API] Fetching products from: https://www.sheinindia.in/api/category/{category_code}")
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
        
        if result.returncode != 0:
            print(f"[API] cURL failed: {result.stderr[:100] if result.stderr else 'Unknown error'}")
            return []
        
        output = result.stdout.strip()
        if not output:
            print(f"[API] Empty response from cURL")
            return []
        
        try:
            data = json_module.loads(output)
        except json_module.JSONDecodeError:
            if 'Access Denied' in output or '403' in output:
                print(f"[API] Access denied (403)")
            else:
                print(f"[API] Invalid JSON response: {output[:100]}")
            return []
        
        products = data.get('products', [])
        
        pagination = data.get('pagination', {})
        total_results = pagination.get('totalNumberOfResults', 0)
        total_pages = pagination.get('numberOfPages', 0)
        current_page = pagination.get('currentPage', 0)
        
        if total_results > 0:
            print(f"[API] Total products available: {total_results} (page {current_page + 1}/{total_pages})")
        
        result_list = []
        for p in products:
            code = p.get('code', '')
            if not code:
                continue
            
            color_data = p.get('fnlColorVariantData', {})
            product_info = {
                'code': code,
                'name': color_data.get('brandName', '') + ' ' + p.get('name', ''),
                'price': p.get('price', {}).get('value', 0),
                'image': color_data.get('outfitPictureURL', ''),
                'url': f"https://www.sheinindia.in/p/{code}"
            }
            result_list.append(product_info)
        
        print(f"[API] Found {len(result_list)} products via cURL")
        return result_list
            
    except subprocess.TimeoutExpired:
        print(f"[API] cURL timeout")
        return []
    except Exception as e:
        print(f"[API] Error fetching products: {e}")
        return []


def check_delivery_via_api(product_id: str, pincode: str, user_cookies: str = None) -> Optional[bool]:
    """
    Check delivery via SHEIN India API using cURL subprocess.
    Returns True if deliverable, False if not, None if unable to determine.
    """
    import subprocess
    import json as json_module
    
    base_cookies = 'V=1; deviceId=R8RkVsXwi4j0zW82Wu8iK; LS=LOGGED_IN; customerType=Existing;'
    cookies = user_cookies if user_cookies else base_cookies
    
    url = f"https://www.sheinindia.in/api/edd/checkDeliveryDetails?productCode={product_id}&postalCode={pincode}&quantity=1&IsExchange=false"
    
    curl_cmd = [
        'curl', '-s', '-L', '--compressed',
        '-H', 'accept: application/json',
        '-H', f'referer: https://www.sheinindia.in/p/{product_id}',
        '-H', 'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        '-H', 'x-tenant-id: SHEIN',
        '-H', 'sec-ch-ua: "Chromium";v="137", "Not/A)Brand";v="24"',
        '-H', 'sec-ch-ua-mobile: ?1',
        '-H', 'sec-ch-ua-platform: "Android"',
        '-H', f'cookie: {cookies}',
        '--max-time', '15'
    ]
    
    proxy = get_proxy()
    if proxy:
        proxy_url = proxy.get('http', '') or proxy.get('https', '')
        if proxy_url:
            curl_cmd.extend(['--proxy', proxy_url])
    
    curl_cmd.append(url)
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=20)
        
        if result.returncode != 0:
            return None
        
        output = result.stdout.strip()
        if not output:
            return None
        
        try:
            data = json_module.loads(output)
        except json_module.JSONDecodeError:
            if 'Access Denied' in output:
                return None
            return None
        
        if 'servicability' in data:
            if data['servicability']:
                edd = ''
                if 'productDetails' in data and data['productDetails']:
                    edd = data['productDetails'][0].get('eddUpper', '')
                print(f"[DELIVERY] {product_id} -> {pincode}: YES (EDD: {edd})")
                return True
            else:
                print(f"[DELIVERY] {product_id} -> {pincode}: NO")
                return False
        
        if 'serviceable' in data:
            if data['serviceable']:
                print(f"[DELIVERY] {product_id} -> {pincode}: YES")
                return True
            else:
                print(f"[DELIVERY] {product_id} -> {pincode}: NO")
                return False
        
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"[DELIVERY] Error: {e}")
        return None


def check_availability_via_cart(product_id: str, user_cookies: str = None) -> Optional[bool]:
    """
    Check product availability using cart API via cURL.
    Works on Termux (no proxy) or with Indian proxies.
    Returns True if product can be added to cart, False if not, None if unable to determine.
    """
    import subprocess
    import json as json_module
    
    base_cookies = 'V=1; deviceId=R8RkVsXwi4j0zW82Wu8iK; LS=LOGGED_IN; customerType=Existing;'
    cookies = user_cookies if user_cookies else base_cookies
    
    proxy = get_indian_proxy()
    
    try:
        # Try to add product to cart directly
        add_url = f'https://www.sheinindia.in/api/cart/add'
        add_data = {"productCode": product_id, "quantity": 1}
        
        curl_cmd = [
            'curl', '-s', '-L', '--compressed',
            '-X', 'POST',
            '-H', 'accept: application/json',
            '-H', 'content-type: application/json',
            '-H', f'cookie: {cookies}',
            '-H', 'origin: https://www.sheinindia.in',
            '-H', f'referer: https://www.sheinindia.in/p/{product_id}',
            '-H', 'user-agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
            '-H', 'x-tenant-id: SHEIN',
            '-d', json_module.dumps(add_data),
            '--max-time', '15'
        ]
        
        if proxy:
            proxy_url = proxy.get('http', '') or proxy.get('https', '')
            if proxy_url:
                curl_cmd.extend(['--proxy', proxy_url])
        
        curl_cmd.append(add_url)
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=20)
        
        if result.returncode != 0:
            return None
        
        output = result.stdout.strip()
        
        if 'Access Denied' in output:
            print(f"[CART] Blocked - need Indian IP or Termux")
            return None
        
        try:
            resp_data = json_module.loads(output)
            if resp_data.get('success') or 'cartId' in resp_data:
                print(f"[CART] Product {product_id} CAN be added")
                return True
            if 'outOfStock' in str(resp_data) or 'sold out' in str(resp_data).lower():
                print(f"[CART] Product {product_id} OUT OF STOCK")
                return False
        except:
            pass
        
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"[CART] Error: {e}")
        return None


class SheinScraper:
    """SHEIN product availability scraper using API-only methods."""
    
    def __init__(self):
        self.new_product_callback = None
    
    def set_new_product_callback(self, callback):
        """Set callback function to be called when new product is found."""
        self.new_product_callback = callback
    
    def fetch_products_api(self, filtered_url: str, user_cookies: str = None) -> List[Dict[str, Any]]:
        """Fetch products via SHEIN API."""
        return fetch_products_api(filtered_url, user_cookies)
    
    def check_delivery_via_api(self, product_id: str, pincode: str, user_cookies: str = None) -> Optional[bool]:
        """Check delivery via SHEIN India API."""
        return check_delivery_via_api(product_id, pincode, user_cookies)
    
    def check_availability_via_cart(self, product_id: str, user_cookies: str = None) -> Optional[bool]:
        """Check product availability using cart API."""
        return check_availability_via_cart(product_id, user_cookies)
    
    def api_login_request_otp(self, phone_number: str) -> Dict[str, Any]:
        """Request OTP via SHEIN API."""
        return api_login_request_otp(phone_number)
    
    def api_login_verify_otp(self, phone_number: str, otp: str) -> Dict[str, Any]:
        """Verify OTP via SHEIN API."""
        return api_login_verify_otp(phone_number, otp)
    
    def extract_product_id(self, product_url: str) -> Optional[str]:
        """Extract base product ID from URL."""
        return extract_product_id(product_url)


# Global scraper instance
_scraper_instance: Optional[SheinScraper] = None
_new_product_callback = None


def get_scraper() -> SheinScraper:
    """Get or create the global scraper instance."""
    global _scraper_instance
    
    if _scraper_instance is None:
        _scraper_instance = SheinScraper()
    
    return _scraper_instance


def set_new_product_callback(callback):
    """Set the global callback for new products."""
    global _new_product_callback
    _new_product_callback = callback
    scraper = get_scraper()
    scraper.new_product_callback = callback


def cleanup_scraper() -> None:
    """Clean up the global scraper instance."""
    global _scraper_instance, _new_product_callback
    _scraper_instance = None
    _new_product_callback = None
