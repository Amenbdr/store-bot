import sqlite3

def init_db():
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    # جدول المستخدمين والحسابات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            password TEXT,
            language TEXT DEFAULT 'ar',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, language, is_admin FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_language(user_id: int, lang: str):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def save_user_if_not_exists(user_id: int, username: str, email: str, password: str, is_admin: int = 0):
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username, email, password, is_admin) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, email, password, is_admin)
        )
        conn.commit()
    conn.close()

def get_total_users_count():
    conn = sqlite3.connect("secure_bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count
