import logging
import requests
import sqlite3
import math
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ⚙️ إعدادات البوت 
# ==========================================
BOT_TOKEN = "5418318795:AAEO50r0oNYrT3QCLafLDFzww1x2kfCO7Eg"
API_URL = "https://smsbower.app/stubs/handler_api.php"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ==========================================
# ==========================================
# 🌍 قائمة الدول الشاملة (تشمل جميع الدول العربية)
# ==========================================
COUNTRIES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "2": "🇰🇿 كازاخستان", "3": "🇨🇳 الصين",
    "4": "🇵🇭 الفلبين", "6": "🇮🇩 إندونيسيا", "12": "🇺🇸 أمريكا", "16": "🇬🇧 بريطانيا",
    "17": "🇲🇦 المغرب", "21": "🇪🇬 مصر", "22": "🇮🇳 الهند", "29": "🇵🇰 باكستان",
    "31": "🇿🇦 جنوب أفريقيا", "36": "🇨🇦 كندا", "43": "🇩🇪 ألمانيا", "46": "🇸🇪 السويد",
    "47": "🇮🇶 العراق", "48": "🇳🇱 هولندا", "53": "🇪🇸 إسبانيا", "58": "🇩🇿 الجزائر",
    "59": "🇸🇦 السعودية", "73": "🇧🇷 البرازيل", "78": "🇫🇷 فرنسا", "86": "🇮🇹 إيطاليا",
    "87": "🇾🇪 اليمن", "89": "🇹🇳 تونس", "94": "🇱🇧 لبنان", "95": "🇦🇪 الإمارات",
    "97": "🇵🇸 فلسطين", "100": "🇱🇾 ليبيا", "104": "🇸🇾 سوريا", "105": "🇸🇩 السودان",
    "106": "🇰🇼 الكويت", "107": "🇴🇲 عُمان", "111": "🇶🇦 قطر", "114": "🇲🇷 موريتانيا",
    "116": "🇯🇴 الأردن", "117": "🇵🇹 البرتغال", "145": "🇧🇭 البحرين", "161": "🇹🇷 تركيا"
}

# ==========================================
# 🗄️ إعداد قاعدة البيانات (SQLite)
# ==========================================
conn = sqlite3.connect('bot_users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, api_key TEXT)''')
conn.commit()

def save_api_key(user_id, api_key):
    cursor.execute("REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, api_key))
    conn.commit()

def get_api_key(user_id):
    cursor.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# ==========================================
# 🛠 كلاس للتعامل مع API موقع SMSBower
# ==========================================
class SmsBower:
    @staticmethod
    def get_balance(api_key):
        try:
            response = requests.get(API_URL, params={'api_key': api_key, 'action': 'getBalance'}).text
            if "ACCESS_BALANCE" in response:
                return response.split(":")[1]
            return None
        except:
            return None

    @staticmethod
    def get_prices(api_key, service, country_id):
        params = {'api_key': api_key, 'action': 'getPrices', 'service': service, 'country'
