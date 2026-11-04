import logging
import requests
import sqlite3
import math
import asyncio
import os
from aiohttp import web
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
            params = {'api_key': api_key, 'action': 'getBalance'}
            response = requests.get(API_URL, params=params).text
            if "ACCESS_BALANCE" in response:
                return response.split(":")[1]
            return None
        except:
            return None

    @staticmethod
    def get_prices(api_key, service, country_id):
        params = {'api_key': api_key, 'action': 'getPrices', 'service': service, 'country': country_id}
        try:
            response = requests.get(API_URL, params=params).json()
            if str(country_id) in response and service in response[str(country_id)]:
                return response[str(country_id)][service]
            return None
        except:
            return None

    @staticmethod
    def get_number(api_key, service, country_id, operator):
        params = {'api_key': api_key, 'action': 'getNumber', 'service': service, 'country': country_id, 'operator': operator}
        try:
            response = requests.get(API_URL, params=params).text
            if "ACCESS_NUMBER" in response:
                parts = response.split(":")
                return {"id": parts[1], "number": parts[2]}
            return None
        except:
            return None

    @staticmethod
    def get_sms(api_key, activation_id):
        params = {'api_key': api_key, 'action': 'getStatus', 'id': activation_id}
        try:
            response = requests.get(API_URL, params=params).text
            if "STATUS_OK" in response:
                return response.split(":")[1]
            elif "STATUS_WAIT_CODE" in response:
                return "WAITING"
            return None
        except:
            return None

# ==========================================
# 📱 واجهات البوت وحالات FSM
# ==========================================
class UserStates(StatesGroup):
    waiting_for_api = State()

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💬 واتساب", callback_data="service_wa"),
        InlineKeyboardButton("✈️ تليجرام", callback_data="service_tg")
    )
    kb.add(
        InlineKeyboardButton("💰 رصيدي بالموقع", callback_data="check_balance"),
        InlineKeyboardButton("🔑 إعداد الـ API", callback_data="set_api")
    )
    return kb

def countries_menu(service_id, page=0):
    kb = InlineKeyboardMarkup(row_width=2)
    items_per_page = 12
    country_items = list(COUNTRIES.items())
    total_pages = math.ceil(len(country_items) / items_per_page)
    
    start = page * items_per_page
    end = start + items_per_page
    current_countries = country_items[start:end]
    
    buttons = []
    for c_id, c_name in current_countries:
        buttons.append(InlineKeyboardButton(c_name, callback_data=f"cntry_{service_id}_{c_id}"))
    kb.add(*buttons)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{service_id}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{service_id}_{page+1}"))
        
    if nav_buttons:
        kb.row(*nav_buttons)
        
    kb.add(InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="back_main"))
    return kb

def check_sms_menu(activation_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔄 تحديث / جلب الكود", callback_data=f"check_sms_{activation_id}"),
        InlineKeyboardButton("❌ إلغاء الرقم", callback_data=f"cancel_{activation_id}")
    )
    return kb

# ==========================================
# 🤖 أوامر البوت الأساسية
# ==========================================
@dp.message_handler(commands=['start'], state='*')
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("أهلاً بك في بوت الأرقام الوهمية الاحترافي 🚀\nاختر التطبيق الذي تريد تفعيله:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == 'set_api')
async def set_api_btn(call: types.CallbackQuery):
    await call.message.edit_text("أرسل الآن مفتاح API الخاص بك من الموقع:")
    await UserStates.waiting_for_api.set()

@dp.message_handler(state=UserStates.waiting_for_api)
async def receive_api_key(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    wait_msg = await message.answer("⏳ جاري التحقق من مفتاح الـ API...")
    balance = SmsBower.get_balance(api_key)
    if balance is not None:
        save_api_key(message.from_user.id, api_key)
        await wait_msg.edit_text(f"✅ تم ربط الحساب بنجاح!\n💰 رصيدك: {balance}\nيمكنك الآن شراء الأرقام.", reply_markup=main_menu())
        await state.finish()
    else:
        await wait_msg.edit_text("❌ مفتاح API غير صحيح! أ
