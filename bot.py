import logging
import requests
import sqlite3
import math
import os
from threading import Thread
from flask import Flask
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
# 🌍 قائمة الدول الشاملة
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
# 🗄️ قاعدة البيانات
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
# 🛠 كلاس SMSBower المحدث لضمان جلب كامل السيرفرات ودقة الشراء
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
            response = requests.get(API_URL, params=params)
            logging.info(f"API Response: {response.text}")
            
            data = response.json()
            if isinstance(data, dict):
                # استخراج بيانات الدولة المحددة
                if str(country_id) in data:
                    c_data = data[str(country_id)]
                    if isinstance(c_data, dict) and service in c_data:
                        service_data = c_data[service]
                        # إذا كانت البيانات تحتوي على عدة مشغلين (مثل server1, server2 أو مخزن كـ dict للمشغلين)
                        if isinstance(service_data, dict):
                            return service_data
                        else:
                            return {"any": service_data}
            return None
        except Exception as e:
            logging.error(f"Error fetching prices: {e}")
            return None

    @staticmethod
    def get_number(api_key, service, country_id, operator):
        # تمرير الدولة والمشغل والخدمة بدقة لضمان عدم اختلاف الدولة
        params = {
            'api_key': api_key, 
            'action': 'getNumber', 
            'service': service, 
            'country': country_id,
            'operator': operator
        }
        try:
            response = requests.get(API_URL, params=params).text
            logging.info(f"Get Number Response: {response}")
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
# 📱 واجهات البوت
# ==========================================
class UserStates(StatesGroup):
    waiting_for_api = State()

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💬 WhatsApp", callback_data="service_wa"),
        InlineKeyboardButton("✈️ Telegram", callback_data="service_tg")
    )
    kb.add(
        InlineKeyboardButton("💰 Account Balance", callback_data="check_balance"),
        InlineKeyboardButton("🔑 Set API Key", callback_data="set_api")
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
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{service_id}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{service_id}_{page+1}"))
        
    if nav_buttons:
        kb.row(*nav_buttons)
        
    kb.add(InlineKeyboardButton("🔙 Main Menu", callback_data="back_main"))
    return kb

def check_sms_menu(activation_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔄 Refresh Code", callback_data=f"check_sms_{activation_id}"),
        InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_{activation_id}")
    )
    return kb

# ==========================================
# 🤖 أوامر البوت
# ==========================================
@dp.message_handler(commands=['start'], state='*')
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Welcome to Virtual Numbers Bot 🚀\nPlease choose service:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == 'set_api')
async def set_api_btn(call: types.CallbackQuery):
    await call.message.edit_text("Please send your SMSBower API Key:")
    await UserStates.waiting_for_api.set()

@dp.message_handler(state=UserStates.waiting_for_api)
async def receive_api_key(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    wait_msg = await message.answer("⏳ Checking API Key...")
    balance = SmsBower.get_balance(api_key)
    if balance is not None:
        save_api_key(message.from_user.id, api_key)
        await wait_msg.edit_text(f"✅ Success!\n💰 Balance: {balance}\nYou can buy numbers now.", reply_markup=main_menu())
        await state.finish()
    else:
        await wait_msg.edit_text("❌ Invalid API Key! Please try again:")

@dp.callback_query_handler(lambda c: c.data == 'check_balance')
async def balance_btn(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    if not user_api: 
        return await call.answer("⚠️ Please set your API Key first!", show_alert=True)
    balance = SmsBower.get_balance(user_api)
    await call.message.edit_text(f"💰 Balance: {balance}" if balance else "❌ Error fetching balance.", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('service_'))
async def select_service(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    if not user_api: 
        return await call.answer("⚠️ Please set your API Key first!", show_alert=True)
    service_id = call.data.split('_')[1]
    app_name = "WhatsApp" if service_id == "wa" else "Telegram"
    await call.message.edit_text(f"Select country for {app_name}:\n(Page 1)", reply_markup=countries_menu(service_id, page=0))

@dp.callback_query_handler(lambda c: c.data.startswith('page_'))
async def process_page(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    if not user_api: 
        return await call.answer("⚠️ Please set your API Key first!", show_alert=True)
    parts = call.data.split('_')
    service_id, page = parts[1], int(parts[2])
    app_name = "WhatsApp" if service_id == "wa" else "Telegram"
    await call.message.edit_text(f"Select country for {app_name}:\n(Page {page + 1})", reply_markup=countries_menu(service_id, page=page))

@dp.callback_query_handler(lambda c: c.data.startswith('cntry_'))
async def process_country(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    _, service_id, country_id = call.data.split('_')
    
    await call.answer("⏳ Fetching servers...", show_alert=False)
    prices_data = SmsBower.get_prices(user_api, service_id, country_id)
    
    if not prices_data:
        return await call.answer("❌ No numbers available for this country.", show_alert=True)
        
    kb = InlineKeyboardMarkup(row_width=1)
    for operator, info in prices_data.items():
        if isinstance(info, dict):
            count = info.get('count', 0)
            price = info.get('cost', info.get('price', 0))
        else:
            continue
            
        if count > 0:
            kb.add(InlineKeyboardButton(f"Server {operator.upper()} | Price: {price}$ | Stock: {count}", callback_data=f"buy_{service_id}_{country_id}_{operator}"))
            
    kb.add(InlineKeyboardButton("🔙 Back to Countries", callback_data=f"service_{service_id}"))
    country_name = COUNTRIES.get(country_id, "Unknown")
    await call.message.edit_text(f"📊 Servers for {country_name}:\nSelect server:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def process_buy(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    parts = call.data.split('_')
    service_id = parts[1]
    country_id = parts[2]
    operator = parts[3]
    
    await call.answer("⏳ Ordering number...", show_alert=True)
    order = SmsBower.get_number(user_api, service_id, country_id, operator)
    
    if order:
        text = f"✅ Number Purchased Successfully!\n\n📞 Phone: `+{order['number']}`\n\nGet code in app then click refresh."
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=check_sms_menu(order['id']))
    else:
        await call.answer("❌ Order failed. Check balance or stock.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('check_sms_'))
async def process_check_sms(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    activation_id = call.data.split('_')[2]
    status = SmsBower.get_sms(user_api, activation_id)
    
    if status == "WAITING":
        await call.answer("⏳ SMS not received yet...", show_alert=True)
    elif status:
        await call.message.edit_text(f"📬 SMS Code Received!\n\nCode: `{status}`", parse_mode="Markdown")
    else:
        await call.answer("⚠️ Timeout or cancelled.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('cancel_'))
async def cancel_number(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    activation_id = call.data.split('_')[1]
    params = {'api_key': user_api, 'action': 'setStatus', 'status': 8, 'id': activation_id}
    requests.get(API_URL, params=params)
    await call.message.edit_text("Number cancelled successfully. ♻️", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == 'back_main')
async def back_main_btn(call: types.CallbackQuery):
    await call.message.edit_text("Main Menu:", reply_markup=main_menu())

# ==========================================
# 🌐 تشغيل خادم Flask في الخلفية
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    executor.start_polling(dp, skip_updates=True)
