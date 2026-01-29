#!/usr/bin/env python3
"""
Subprocess script to run scraper for a user.
Called from bot.py to run product checks.
API-only, no browser automation.
"""
import sys
import json
import scraper
import user_database


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No user_id provided"}))
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    urls = user_database.get_user_urls(user_id)
    pincodes = user_database.get_user_pincodes(user_id)
    
    if not urls:
        print(json.dumps({"status": "no_urls", "new_products": 0}))
        sys.exit(0)
    
    print(f"[SCRAPER] Starting check for user {user_id}", file=sys.stderr)
    print(f"[SCRAPER] URLs: {len(urls)} configured", file=sys.stderr)
    print(f"[SCRAPER] Pincodes: {', '.join(pincodes) if pincodes else 'None'}", file=sys.stderr)
    
    total_deliverable = 0
    new_products_found = []
    user_cookies = user_database.get_auth_cookies(user_id)
    
    if user_cookies:
        print(f"[SCRAPER] Using user's auth cookies for API calls", file=sys.stderr)
    
    try:
        scraper_instance = scraper.get_scraper()
    except Exception as e:
        print(f"[SCRAPER] Error getting scraper: {e}", file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    
    for url_index, filtered_url in enumerate(urls):
        print(f"[SCRAPER] Processing URL {url_index + 1}/{len(urls)}: {filtered_url[:60]}...", file=sys.stderr)
        
        try:
            # Use API with proxy to fetch products
            products_data = scraper_instance.fetch_products_api(filtered_url, user_cookies)
            
            if not products_data:
                print(f"[SCRAPER] No products found from this URL", file=sys.stderr)
                continue
            
            # Convert to URL format for compatibility
            product_urls = [p.get('url', f"https://www.sheinindia.in/p/{p.get('code', '')}") for p in products_data if p.get('code') or p.get('url')]
            
            new_products = []
            for product_url in product_urls:
                if not user_database.is_product_seen(user_id, product_url):
                    new_products.append(product_url)
            
            print(f"[SCRAPER] {len(new_products)} new products from this URL", file=sys.stderr)
            
            if not new_products:
                continue
            
            # Check if we can use cart-based availability check (Termux or Indian proxy)
            from scraper import IS_TERMUX, get_indian_proxy
            can_check_cart = IS_TERMUX or get_indian_proxy() is not None
            
            for product_url in new_products:
                new_products_found.append(product_url)
                print(f"[SCRAPER] New product: {product_url}", file=sys.stderr)
                
                product_id = scraper_instance.extract_product_id(product_url)
                if not product_id:
                    user_database.mark_product_seen(user_id, product_url)
                    continue
                
                # Check availability via cart if on Termux or have Indian proxy
                is_available = None
                if can_check_cart and user_cookies:
                    print(f"[SCRAPER] Checking cart availability for {product_id}...", file=sys.stderr)
                    is_available = scraper_instance.check_availability_via_cart(product_id, user_cookies)
                
                # Only notify if available (or if we can't check, notify all)
                if is_available is True or is_available is None:
                    if pincodes:
                        for pincode in pincodes:
                            # If we could check and it's available, or if we couldn't check
                            if is_available is True:
                                is_new = user_database.save_delivery_result(user_id, product_url, pincode)
                                if is_new:
                                    total_deliverable += 1
                                    print(f"[SCRAPER] AVAILABLE for {pincode}: {product_url}", file=sys.stderr)
                            elif is_available is None:
                                # Couldn't check, notify anyway
                                is_new = user_database.save_delivery_result(user_id, product_url, pincode)
                                if is_new:
                                    total_deliverable += 1
                                    print(f"[SCRAPER] NEW PRODUCT for {pincode}: {product_url}", file=sys.stderr)
                elif is_available is False:
                    print(f"[SCRAPER] Product {product_id} NOT available - skipping", file=sys.stderr)
                
                user_database.mark_product_seen(user_id, product_url)
        
        except Exception as e:
            print(f"[SCRAPER] Error processing URL: {e}", file=sys.stderr)
            continue
    
    result = {
        "status": "ok",
        "new_products": len(new_products_found),
        "deliverable": total_deliverable,
        "products": new_products_found[:10]
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
