import logging
import requests
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ⚙️ إعدادات البوت 
# ==========================================
BOT_TOKEN = "5418318795:AAG3lt5CD7OYl4kgCNkReX5r7CwSy8ljZ0I"
API_URL = "https://smsbower.app/stubs/handler_api.php" # الرابط القياسي المعتمد لأغلب لوحات الأرقام

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
# استخدام MemoryStorage لتفعيل نظام انتظار الرسائل (FSM)
dp = Dispatcher(bot, storage=MemoryStorage())

# ==========================================
# 🗄️ إعداد قاعدة البيانات (SQLite)
# ==========================================
conn = sqlite3.connect('bot_users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT
    )
''')
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
        params = {'api_key': api_key, 'action': 'getBalance'}
        try:
            response = requests.get(API_URL, params=params).text
            if "ACCESS_BALANCE" in response:
                return response.split(":")[1]
            return None
        except:
            return None

    @staticmethod
    def get_number(api_key, service, country_id):
        params = {'api_key': api_key, 'action': 'getNumber', 'service': service, 'country': country_id}
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
        InlineKeyboardButton("📱 شراء رقم تليجرام", callback_data="buy_tg"),
        InlineKeyboardButton("💰 رصيدي بالموقع", callback_data="check_balance"),
        InlineKeyboardButton("🔑 إضافة / تغيير الـ API", callback_data="set_api")
    )
    return kb

def countries_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🇷🇺 روسيا (ID: 0)", callback_data="country_0"),
        InlineKeyboardButton("🇺🇸 أمريكا (ID: 12)", callback_data="country_12"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    )
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
    text = "أهلاً بك في بوت الأرقام الوهمية 🚀\nالرجاء إضافة مفتاح API الخاص بك من الموقع لتبدأ."
    await message.answer(text, reply_markup=main_menu())

# --- نظام إضافة الـ API ---
@dp.callback_query_handler(lambda c: c.data == 'set_api')
async def set_api_btn(call: types.CallbackQuery):
    await call.message.edit_text("أرسل الآن مفتاح API الخاص بك من موقع SMSBower:\n(يمكنك إيجاده في إعدادات حسابك بالموقع)")
    await UserStates.waiting_for_api.set()

@dp.message_handler(state=UserStates.waiting_for_api)
async def receive_api_key(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    wait_msg = await message.answer("⏳ جاري التحقق من مفتاح الـ API...")
    
    # اختبار الـ API عبر محاولة جلب الرصيد
    balance = SmsBower.get_balance(api_key)
    
    if balance is not None:
        save_api_key(message.from_user.id, api_key)
        await wait_msg.edit_text(f"✅ تم ربط حسابك بنجاح!\n💰 رصيدك الحالي: {balance}\n\nيمكنك الآن البدء بشراء الأرقام.", reply_markup=main_menu())
        await state.finish()
    else:
        await wait_msg.edit_text("❌ مفتاح API غير صحيح أو لا يوجد اتصال بالموقع.\nالرجاء إرسال المفتاح الصحيح مرة أخرى:")
        # يبقى في حالة الانتظار حتى يرسل مفتاح صحيح

# --- بقية الأوامر (تستخدم الـ API الخاص بالمستخدم) ---
@dp.callback_query_handler(lambda c: c.data == 'check_balance')
async def balance_btn(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    if not user_api:
        return await call.answer("⚠️ يجب عليك إضافة مفتاح API الخاص بك أولاً!", show_alert=True)
    
    balance = SmsBower.get_balance(user_api)
    if balance:
        await call.message.edit_text(f"💰 رصيد حسابك في الموقع: {balance}", reply_markup=main_menu())
    else:
        await call.answer("❌ فشل جلب الرصيد، تأكد من صحة الـ API.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == 'buy_tg')
async def buy_tg_btn(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    if not user_api:
        return await call.answer("⚠️ يجب عليك إضافة مفتاح API الخاص بك أولاً!", show_alert=True)
    
    await call.message.edit_text("اختر الدولة المطلوبة للحصول على رقم تليجرام:", reply_markup=countries_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('country_'))
async def process_country(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    country_id = call.data.split('_')[1]
    
    await call.answer("⏳ جاري طلب الرقم من الموقع...", show_alert=True)
    order = SmsBower.get_number(user_api, service="tg", country_id=country_id)
    
    if order:
        text = f"✅ **تم استخراج الرقم بنجاح!**\n\n📞 الرقم: `+{order['number']}`\n\nاطلب الكود ثم اضغط على التحديث أدناه."
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=check_sms_menu(order['id']))
    else:
        await call.message.edit_text("❌ الرصيد غير كافٍ أو لا توجد أرقام متاحة لهذه الدولة.", reply_markup=countries_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('check_sms_'))
async def process_check_sms(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    activation_id = call.data.split('_')[2]
    
    status = SmsBower.get_sms(user_api, activation_id)
    if status == "WAITING":
        await call.answer("⏳ لم يصل الكود بعد، انتظر ثواني وحاول التحديث...", show_alert=True)
    elif status:
        await call.message.edit_text(f"📬 **وصل الكود!**\n\nكود التفعيل هو: `{status}`", parse_mode="Markdown")
    else:
        await call.answer("⚠️ حدث خطأ أو انتهى وقت الرقم.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('cancel_'))
async def cancel_number(call: types.CallbackQuery):
    user_api = get_api_key(call.from_user.id)
    activation_id = call.data.split('_')[1]
    requests.get(API_URL, params={'api_key': user_api, 'action': 'setStatus', 'status': 8, 'id': activation_id})
    await call.message.edit_text("تم إلغاء الرقم بنجاح. ♻️", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == 'back_main')
async def back_main_btn(call: types.CallbackQuery):
    await call.message.edit_text("القائمة الرئيسية:", reply_markup=main_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
