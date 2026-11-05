import sqlite3

def init_db():
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            password TEXT,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'ar',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_name TEXT,
            target_info TEXT,
            cost REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('profit_margin', '10')")
    conn.commit()
    conn.close()

def get_profit_margin() -> float:
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'profit_margin'")
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 10.0

def set_profit_margin(margin: float):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('profit_margin', ?)", (str(margin),))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, language, is_admin, balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def find_user_by_identifier(identifier: str):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    if identifier.isdigit():
        cursor.execute("SELECT user_id, email, balance FROM users WHERE user_id = ?", (int(identifier),))
    else:
        cursor.execute("SELECT user_id, email, balance FROM users WHERE email = ?", (identifier,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_balance(user_id: int, amount: float, operation: str):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    if operation == "add":
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    elif operation == "sub":
        cursor.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_user_language(user_id: int, lang: str):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def save_user_credentials(user_id: int, username: str, email: str, password: str):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET email = ?, password = ? WHERE user_id = ?", (email, password, user_id))
    else:
        is_admin = 1 if user_id == 5396793642 else 0
        cursor.execute(
            "INSERT INTO users (user_id, username, email, password, is_admin) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, email, password, is_admin)
        )
    conn.commit()
    conn.close()

def log_user_activity(user_id: int, service_name: str, target_info: str, cost: float):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_activity_log (user_id, service_name, target_info, cost) VALUES (?, ?, ?, ?)",
        (user_id, service_name, target_info, cost)
    )
    conn.commit()
    conn.close()

def get_user_logs(user_id: int):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT service_name, target_info, cost, created_at FROM user_activity_log WHERE user_id = ? ORDER BY log_id DESC LIMIT 10",
        (user_id,)
    )
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_total_users_count() -> int:
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_users_balances() -> float:
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(balance) FROM users")
    total = cursor.fetchone()[0]
    conn.close()
    return float(total) if total else 0.0

def get_total_consumption() -> float:
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cost) FROM user_activity_log")
    total = cursor.fetchone()[0]
    conn.close()
    return float(total) if total else 0.0
