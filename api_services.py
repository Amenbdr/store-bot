import aiohttp
import logging
import sqlite3

def init_api_config_db():
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_providers (
            provider_key TEXT PRIMARY KEY,
            provider_name TEXT,
            api_key TEXT,
            base_url TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pinned_products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            price REAL DEFAULT 0.0,
            description TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO api_providers (provider_key, provider_name, api_key, base_url)
        VALUES ('foxreload', 'FoxReload API', 'dmk_SLDMDj7c85zyzMGiCN56JGFYsu0Dyc_cuFL9DWxcpEA', 'https://public-api.foxreload.com')
    """)
    conn.commit()
    conn.close()

def get_provider_config(provider_key: str = "foxreload"):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, base_url, provider_name FROM api_providers WHERE provider_key = ?", (provider_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"api_key": row[0], "base_url": row[1], "name": row[2]}
    return None

def update_provider_api_key(provider_key: str, new_api_key: str):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE api_providers SET api_key = ? WHERE provider_key = ?", (new_api_key, provider_key))
    conn.commit()
    conn.close()

def get_all_providers():
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT provider_key, provider_name FROM api_providers")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pinned_products():
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, product_name, price, description FROM pinned_products")
    rows = cursor.fetchall()
    conn.close()
    return rows

def pin_product(product_id: str, product_name: str, price: float, description: str):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO pinned_products (product_id, product_name, price, description) 
        VALUES (?, ?, ?, ?)
    """, (product_id, product_name, price, description))
    conn.commit()
    conn.close()

def unpin_product(product_id: str):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pinned_products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

async def search_products_from_provider(query: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return []
    
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            search_url = f"{config['base_url']}/api/products/search?query={query}&limit=50"
            async with session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, list):
                        results = data
                    elif isinstance(data, dict):
                        results = data.get("items", []) or data.get("data", [])
                    else:
                        results = []
                    
                    if not results:
                        logging.info("API search returned empty. Using smart local search fall-back...")
                        all_url = f"{config['base_url']}/api/products/"
                        async with session.get(all_url, headers=headers) as all_res:
                            if all_res.status == 200:
                                all_data = await all_res.json()
                                
                                if isinstance(all_data, list):
                                    all_items = all_data
                                elif isinstance(all_data, dict):
                                    all_items = all_data.get("items", []) or all_data.get("data", [])
                                else:
                                    all_items = []
                                    
                                results = [
                                    item for item in all_items 
                                    if query.lower() in str(item.get("name", "")).lower()
                                ]
                    return results
                else:
                    return []
        except Exception as e:
            logging.error(f"Search exception: {str(e)}")
            return []

async def get_product_details_from_provider(product_id_or_slug: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return None
    
    url = f"{config['base_url']}/api/products/{product_id_or_slug}"
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return None
        except Exception as e:
            return None

async def check_provider_balance(provider_key: str):
    config = get_provider_config(provider_key)
    if not config:
        return "الموقع غير موجود"
    
    balance_url = f"{config['base_url']}/api/access/me/balances/"
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(balance_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return f"خطأ في المصادقة (كود: {response.status})"
        except Exception as e:
            return f"تعذر الاتصال: {str(e)}"

async def send_order_to_provider(product_id: str, target_info: str, quantity: int = 1, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return False, "Provider config not found."
        
    url = f"{config['base_url']}/api/orders/"
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # الهيكل الصحيح حسب توثيق الفوكس ريلود (itemId, quantity, note.username)
    payload = {
        "items": [
            {
                "itemId": product_id,
                "quantity": quantity,
                "note": {
                    "username": target_info
                }
            }
        ]
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                try:
                    res_data = await response.json()
                except Exception:
                    res_data = await response.text()
                
                if response.status in [200, 201]:
                    return True, res_data
                else:
                    return False, res_data
        except Exception as e:
            return False, str(e)

async def pay_order_in_provider(order_id: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return False, "Provider config not found."
        
    url = f"{config['base_url']}/api/orders/{order_id}/pay"
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "paymentProvider": None
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                try:
                    res_data = await response.json()
                except Exception:
                    res_data = await response.text()
                
                if response.status in [200, 201]:
                    return True, res_data
                else:
                    return False, res_data
        except Exception as e:
            return False, str(e)

async def get_order_status_from_provider(order_id: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return None
    
    url = f"{config['base_url']}/api/orders/{order_id}"
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return None
        except Exception as e:
            return None
