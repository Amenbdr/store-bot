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
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            email TEXT,
            username TEXT,
            is_admin INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'ar'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT,
            target TEXT,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO api_providers (provider_key, provider_name, api_key, base_url)
        VALUES ('foxreload', 'FoxReload API', 'dmk_SLDMDj7c85zyzMGiCN56JGFYsu0Dyc_cuFL9DWxcpEA', 'https://public-api.foxreload.com')
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email, username, language, is_admin, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def save_user_credentials(user_id: int, username: str, email: str, password: str):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, email, username, balance) 
        VALUES (?, ?, ?, 0.0)
        ON CONFLICT(user_id) DO UPDATE SET email = ?, username = ?
    """, (user_id, email, username, email, username))
    conn.commit()
    conn.close()

def get_total_users_count():
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def find_user_by_identifier(identifier: str):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    if identifier.isdigit():
        cursor.execute("SELECT user_id, username, balance FROM users WHERE user_id = ?", (int(identifier),))
    else:
        cursor.execute("SELECT user_id, username, balance FROM users WHERE username = ?", (identifier.lstrip('@'),))
    row = cursor.fetchone()
    conn.close()
    return row

def update_user_balance(user_id: int, amount: float, operation: str = "add"):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    if operation == "add":
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    else:
        cursor.execute("UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def log_user_activity(user_id: int, service: str, target: str, cost: float):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_logs (user_id, service, target, cost) VALUES (?, ?, ?, ?)", (user_id, service, target, cost))
    conn.commit()
    conn.close()

def get_user_logs(user_id: int):
    init_api_config_db()
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT service, target, cost, created_at FROM user_logs WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

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
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            search_url = f"{config['base_url']}/api/products/search?query={query}&limit=50"
            async with session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data if isinstance(data, list) else (data.get("items", []) or data.get("data", []))
                    if not results:
                        all_url = f"{config['base_url']}/api/products/"
                        async with session.get(all_url, headers=headers) as all_res:
                            if all_res.status == 200:
                                all_data = await all_res.json()
                                all_items = all_data if isinstance(all_data, list) else (all_data.get("items", []) or all_data.get("data", []))
                                results = [item for item in all_items if query.lower() in str(item.get("name", "")).lower()]
                    return results
                return []
        except Exception as e:
            logging.error(f"Search exception: {str(e)}")
            return []

async def get_product_details_from_provider(product_id_or_slug: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return None
    url = f"{config['base_url']}/api/products/{product_id_or_slug}"
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                return await response.json() if response.status == 200 else None
        except Exception:
            return None

async def check_provider_balance(provider_key: str):
    config = get_provider_config(provider_key)
    if not config:
        return "الموقع غير موجود"
    balance_url = f"{config['base_url']}/api/access/me/balances/"
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(balance_url, headers=headers) as response:
                return await response.json() if response.status == 200 else f"خطأ في المصادقة (كود: {response.status})"
        except Exception as e:
            return f"تعذر الاتصال: {str(e)}"

async def send_order_to_provider(product_id: str, target_info: str, quantity: int = 1, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return False, "Provider config not found."
    url = f"{config['base_url']}/api/orders/"
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json", "Content-Type": "application/json"}
    payload = {"items": [{"itemId": product_id, "quantity": quantity, "note": {"username": target_info}}]}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                res_data = await response.json() if response.content_type == 'application/json' else await response.text()
                return (True, res_data) if response.status in [200, 201] else (False, res_data)
        except Exception as e:
            return False, str(e)

async def pay_order_in_provider(order_id: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return False, "Provider config not found."
    url = f"{config['base_url']}/api/orders/{order_id}/pay"
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json", "Content-Type": "application/json"}
    payload = {"paymentProvider": None}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                res_data = await response.json() if response.content_type == 'application/json' else await response.text()
                return (True, res_data) if response.status in [200, 201] else (False, res_data)
        except Exception as e:
            return False, str(e)

async def get_order_status_from_provider(order_id: str, provider_key: str = "foxreload"):
    config = get_provider_config(provider_key)
    if not config:
        return None
    url = f"{config['base_url']}/api/orders/{order_id}"
    headers = {"X-API-Key": config["api_key"], "X-Language": "en", "X-Currency": "usd", "Accept": "application/json"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                return await response.json() if response.status == 200 else None
        except Exception:
            return None
