import sqlite3

class Database:
    DB_NAME = "database.db"

    @staticmethod
    def init_db():
        """إنشاء كافة الجداول الأساسية لقاعدة البيانات عند بدء التشغيل"""
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        
        # 1. جدول المستخدمين (الآيدي، الإيميل، كلمة المرور، الرصيد، حالة الحظر)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT DEFAULT NULL,
                password TEXT DEFAULT NULL,
                balance REAL DEFAULT 0.0,
                is_banned INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. جدول الإعدادات العامة (لتخزين مفتاح الـ API وإعدادات البوت ديناميكياً)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # 3. جدول المعاملات المالية (للأرصدة، الإيداعات، ومتابعة عمليات الشراء)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                amount REAL,
                type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 4. جدول تذاكر الدعم الفني
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    # ==================== دوال الإعدادات (Settings) ====================
    @staticmethod
    def get_setting(key: str, default=None):
        """جلب إعداد معين من قاعدة البيانات"""
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

    @staticmethod
    def set_setting(key: str, value: str):
        """حفظ أو تحديث إعداد معين في قاعدة البيانات"""
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    # ==================== دوال المستخدمين (Users) ====================
    @staticmethod
    def get_or_create_user(user_id: str):
        """التحقق من وجود المستخدم أو إنشائه تلقائياً إذا كان جديداً"""
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, balance, is_banned FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
            conn.commit()
            user = (user_id, 0.0, 0)
            
        conn.close()
        return user  # (user_id, balance, is_banned)

    @staticmethod
    def update_user_balance(user_id: str, amount: float, tx_type: str = 'deposit'):
        """تحديث رصيد المستخدم وتسجيل المعاملة المالية"""
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)", (user_id, amount, tx_type))
        conn.commit()
        conn.close()

    # ==================== نظام تحويل الأرصدة (Transfer) ====================
    @staticmethod
    def transfer_balance_by_identifier(sender_id: str, recipient_identifier: str, amount: float):
        """
        تحويل رصيد من مستخدم لآخر عبر الآيدي (user_id) أو البريد الإلكتروني (email)
        """
        if amount <= 0:
            return False, "❌ مبلغ التحويل غير صالح."
            
        conn = sqlite3.connect(Database.DB_NAME)
        cursor = conn.cursor()
        
        # 1. فحص رصيد المرسل
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
        sender_row = cursor.fetchone()
        if not sender_row or sender_row[0] < amount:
            conn.close()
            return False, "❌ رصيدك الحالي غير كافٍ لإتمام عملية التحويل."
            
        # 2. البحث عن المستخدم المستلم (بالآيدي أو الإيميل)
        cursor.execute("SELECT user_id, balance FROM users WHERE user_id = ? OR email = ?", (recipient_identifier, recipient_identifier))
        recipient_row = cursor.fetchone()
        
        if not recipient_row:
            conn.close()
            return False, "❌ لم يتم العثور على المستخدم المستلم (تأكد من الآيدي أو الإيميل المدخل)."
            
        recipient_id = recipient_row[0]
        
        if sender_id == recipient_id:
            conn.close()
            return False, "❌ لا يمكنك تحويل الرصيد إلى نفس حسابك الشخصي."
            
        # 3. تنفيذ الخصم والإضافة وتوثيق العمليات المالية
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
        cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)", (sender_id, amount, 'spend_transfer'))
        
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient_id))
        cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)", (recipient_id, amount, 'deposit_transfer'))
        
        conn.commit()
        conn.close()
        return True, f"✅ تمت عملية التحويل بنجاح بقيمة `{amount}$` إلى المستخدم (ID: `{recipient_id}`)."
