import sqlite3
import logging
from config import DB_NAME

class Database:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # تحسينات أداء فائقة لخدمة أكثر من 10,000 مستخدم
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. جدول العملاء
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance REAL DEFAULT 0.0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # 2. جدول الطلبات (سجل الشراء)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_type TEXT,
                    item_details TEXT,
                    price REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # 3. جدول السيرفرات المخصصة للتحكم بهامش الربح من الأدمن
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_name TEXT,
                    margin_type TEXT DEFAULT 'fixed',
                    margin_value REAL DEFAULT 0.15,
                    is_active INTEGER DEFAULT 1
                )
            ''')

            # إضافة سيرفرين افتراضيين للعميل عند إنشاء قاعدة البيانات لأول مرة
            cursor.execute("SELECT COUNT(*) FROM custom_servers")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO custom_servers (server_name, margin_type, margin_value) VALUES ('سيرفر 1', 'fixed', 0.15)")
                cursor.execute("INSERT INTO custom_servers (server_name, margin_type, margin_value) VALUES ('سيرفر 2', 'fixed', 0.20)")

            # الفهارس لسرعة البحث في قاعدة البيانات
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_id ON users(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
            conn.commit()

    def add_user(self, user_id: int, username: str, full_name: str):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            conn.commit()

    def get_user(self, user_id: int):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def update_balance(self, user_id: int, amount: float):
        """ إضافة أو خصم رصيد """
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()

    def get_all_users_count(self) -> int:
        with self.get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_all_users(self):
        with self.get_connection() as conn:
            return conn.execute("SELECT user_id FROM users").fetchall()

    def get_custom_servers(self):
        """ جلب السيرفرات المخصصة المفعّلة """
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM custom_servers WHERE is_active = 1").fetchall()

    def update_server_margin(self, server_id: int, margin_value: float):
        """ تعديل هامش الربح للسيرفر """
        with self.get_connection() as conn:
            conn.execute("UPDATE custom_servers SET margin_value = ? WHERE id = ?", (margin_value, server_id))
            conn.commit()

    def add_order(self, user_id: int, service_type: str, item_details: str, price: float, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (user_id, service_type, item_details, price, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, service_type, item_details, price, status)
            )
            conn.commit()
            return cursor.lastrowid

db = Database()
