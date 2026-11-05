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
        INSERT OR IGNORE INTO api_providers (provider_key, provider_name, api_key, base_url)
        VALUES ('foxreload', 'FoxReload API', 'dmk_SLDMDj7c85zyzMGiCN56JGFYsu0Dyc_cuFL9DWxcpEA', 'https://public-api.foxreload.com/api/orders/')
    """)
    conn.commit()
    conn.close()

def get_provider_config(provider_key: str):
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

# قائمة الخدمات والاشتراكات كاملة
SERVICES_CATALOG = {
    "stars": {
        "name": "⭐ شحن نجوم تليجرام (Stars)",
        "product_id": "YOUR_STARS_PRODUCT_ID",
        "provider": "foxreload"
    },
    "premium_1m": {
        "name": "💎 اشتراك بريميوم (شهر)",
        "product_id": "YOUR_PREMIUM_1M_ID",
        "provider": "foxreload"
    },
    "premium_3m": {
        "name": "📅 اشتراك بريميوم (3 أشهر)",
        "product_id": "YOUR_PREMIUM_3M_ID",
        "provider": "foxreload"
    },
    "premium_6m": {
        "name": "📅 اشتراك بريميوم (6 أشهر)",
        "product_id": "YOUR_PREMIUM_6M_ID",
        "provider": "foxreload"
    },
    "premium_1y": {
        "name": "📅 اشتراك بريميوم (سنة)",
        "product_id": "YOUR_PREMIUM_1Y_ID",
        "provider": "foxreload"
    }
}

async def check_provider_balance(provider_key: str):
    config = get_provider_config(provider_key)
    if not config:
        return "الموقع غير موجود"
    
    balance_url = "https://public-api.foxreload.com/api/access/me/balances/"
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

async def send_order_to_provider(service_code: str, target_info: str):
    service_info = SERVICES_CATALOG.get(service_code)
    if not service_info:
        return False, "Service not found."
    
    provider_key = service_info["provider"]
    config = get_provider_config(provider_key)
    if not config:
        return False, "Provider config not found."
        
    product_id = service_info["product_id"]
    url = config["base_url"]
    
    headers = {
        "X-API-Key": config["api_key"],
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "items": [
            {
                "itemId": product_id,
                "quantity": 1,
                "link": target_info
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
                    logging.error(f"API Error Status {response.status}: {res_data}")
                    return False, res_data
        except Exception as e:
            logging.error(f"API Connection Exception: {str(e)}")
            return False, str(e)
