import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# 1. الإعدادات الأساسية وقاعدة البيانات
# ==========================================
API_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن بوتك هنا
ADMIN_IDS = [123456789]  # ضع آيدي المشرف الخاص بك هنا

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

database = {
    "settings": {
        "smsbower_api_key": "YOUR_SMSBOWER_API_KEY",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "your_email@gmail.com",
        "sender_password": "your_app_password"
    },
    "users": {},          
    "verified_users": [], 
    "custom_prices": {}   
}

admin_temp_data = {}

def load_db():
    return database

def save_db(db):
    global database
    database = db

# ==========================================
# 2. القواميس والحالات (FSM States)
# ==========================================
COUNTRY_NAMES = {
    "0": "روسيا 🇷🇺", "1": "الولايات المتحدة 🇺🇸", "2": "كازاخستان 🇰🇿", "3": "الصين 🇨🇳",
    "4": "الفلبين 🇵🇭", "5": "الهند 🇮🇳", "6": "إندونيسيا 🇮🇩", "7": "ماليزيا 🇲🇾",
    "8": "كينيا 🇰🇪", "9": "فيتنام 🇻🇳", "10": "قيرغيزستان 🇰🇬", "11": "تنزانيا 🇹🇿",
    "12": "سريلانكا 🇱🇰", "14": "باكستان 🇵🇰", "15": "المملكة المتحدة 🇬🇧", "16": "السعودية 🇸🇦",
    "17": "اليمن 🇾🇪", "18": "رواندا 🇷🇼", "19": "مصر 🇪🇬", "22": "المغرب 🇲🇦"
}

class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_login_email = State()
    waiting_for_signup_email = State()

class AdminStates(StatesGroup):
    waiting_for_service_price = State()

class TransferStates(StatesGroup):
    waiting_for_receiver_email = State()
    waiting_for_transfer_amount = State()
    waiting_for_transfer_confirm = State()

# ==========================================
# 3. دوال البريد الإلكتروني والـ API
# ==========================================
def send_activation_email(to_email, phone_number, sms_code, service_name):
    db = load_db()
    settings = db.get("settings", {})
    sender_email = settings.get("sender_email")
    sender_password = settings.get("sender_password")
    
    if not sender_email or not sender_password:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = f"📲 تفاصيل تفعيل رقم {service_name}"
        body = f"تفاصيل الرقم الوهمي:\nالخدمة: {service_name}\nالرقم: {phone_number}\nالكود: {sms_code}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(settings.get("smtp_server", "smtp.gmail.com"), int(settings.get("smtp_port", 587)))
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Email error: {e}")
        return False

# ==========================================
# 4. أمر البداية (Start) والكابتشا لمرة واحدة
# ==========================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    db = load_db()
    
    if user_id in db.get("verified_users", []) or user_id in ADMIN_IDS:
        await show_main_menu(message)
    else:
        await message.answer("🔒 أهلاً بك! يرجى إتمام التحقق الأمني (الكابتشا) للمرة الأولى فقط للمتابعة:")
        await UserStates.waiting_for_captcha.set()

async def show_main_menu(message_or_call):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🛒 قسم الأرقام الوهمية والتفعيل", callback_data="buy_sim"),
        InlineKeyboardButton("⚙️ الإعدادات الشخصية", callback_data="user_settings_menu")
    )
    
    user_id = message_or_call.from_user.id
    if user_id in ADMIN_IDS:
        keyboard.add(InlineKeyboardButton("🛠 لوحة تحكم المشرف", callback_data="admin_panel"))
        
    text = "🏠 **القائمة الرئيسية للبوت:**\nاختر ما يناسبك من الخيارات أدناه:"
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_call.answer(text, reply_markup=keyboard, parse_mode="Markdown")
# ==========================================
# 5. لوحة تحكم المشرف وإدارة السيرفرات (12 دولة لكل صفحة)
# ==========================================
@dp.callback_query_handler(text="admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⚙️ إدارة السيرفرات والأسعار المنفردة", callback_data="admin_servers_manager"),
        InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main")
    )
    await call.message.edit_text("🛠 **لوحة تحكم المشرف:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="admin_servers_manager")
async def admin_servers_manager_menu(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🟢 تعديل سيرفرات واتساب (WA)", callback_data="adm_app_wa_0"),
        InlineKeyboardButton("🔵 تعديل سيرفرات تيليجرام (TG)", callback_data="adm_app_tg_0"),
        InlineKeyboardButton("🟣 تعديل سيرفرات انستقرام (IG)", callback_data="adm_app_ig_0"),
        InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_panel")
    )
    await call.message.edit_text("⚙️ **قسم إدارة السيرفرات والأسعار (اختر التطبيق):**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('adm_app_'))
async def admin_show_countries_paginated(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    parts = call.data.split('_')
    serv_code = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    user_id = call.from_user.id
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    try:
        response = requests.get(f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices", timeout=10)
        data = response.json() if response.status_code == 200 else None
        if not data or not isinstance(data, dict):
            await call.answer("⚠️ فشل جلب البيانات من الموقع.", show_alert=True)
            return
        admin_temp_data[f"prices_{user_id}"] = data
        
        matched = [cid for cid, srv in data.items() if isinstance(srv, dict) and serv_code in srv]
        PER_PAGE = 12
        total_pages = (len(matched) + PER_PAGE - 1) // PER_PAGE
        current_countries = matched[page * PER_PAGE : (page + 1) * PER_PAGE]
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        for cid in current_countries:
            cname = COUNTRY_NAMES.get(str(cid), f"دولة ({cid})")
            keyboard.insert(InlineKeyboardButton(cname, callback_data=f"adm_c_serv_{cid}_{serv_code}"))
            
        nav = []
        if page > 0: nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"adm_app_{serv_code}_{page - 1}"))
        if page < total_pages - 1: nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"adm_app_{serv_code}_{page + 1}"))
        if nav: keyboard.row(*nav)
        
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_servers_manager"))
        await call.message.edit_text(f"🌍 **تطبيق ({serv_code.upper()}) - صفحة {page+1}/{total_pages}**\nاختر الدولة:", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await call.answer(f"❌ خطأ: {e}", show_alert=True)

# ==========================================
# 6. إعدادات المستخدم وتحويل الرصيد الخطي
# ==========================================
@dp.callback_query_handler(text="user_settings_menu")
async def user_settings_menu(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⚠️ تعديل كلمة سر الحساب", callback_data="set_pass"),
        InlineKeyboardButton("🔔 مسح سجلات الأرقام", callback_data="set_clear"),
        InlineKeyboardButton("🔄 تحويل رصيد لحساب آخر", callback_data="user_transfer_start"),
        InlineKeyboardButton("🚪 تسجيل خروج", callback_data="user_logout"),
        InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")
    )
    await call.message.edit_text("⚙️ **[ قسم الإعدادات الخاصة بالبوت: ]**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="user_transfer_start")
async def transfer_start(call: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu"))
    await call.message.edit_text("💸 **تحويل رصيد لحساب آخر:**\n\n📧 أرسل **البريد الإلكتروني** الخاص بالمستلم:", reply_markup=kb, parse_mode="Markdown")
    await TransferStates.waiting_for_receiver_email.set()

@dp.message_handler(state=TransferStates.waiting_for_receiver_email)
async def transfer_get_email(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['receiver_email'] = message.text.strip()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu"))
    await message.answer("💵 الآن، أرسل **المبلغ** المراد تحويله (مثال: `5`):", reply_markup=kb, parse_mode="Markdown")
    await TransferStates.waiting_for_transfer_amount.set()

@dp.message_handler(state=TransferStates.waiting_for_transfer_amount)
async def transfer_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0: raise ValueError()
        async with state.proxy() as data:
            data['transfer_amount'] = amount
            receiver = data['receiver_email']
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("✅ تأكيد التحويل", callback_data="confirm_transfer_yes"),
            InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu")
        )
        await message.answer(f"📋 **ملخص التحويل:**\n- إلى: `{receiver}`\n- المبلغ: `{amount}$`\n\nهل أنت متأكد من إتمام العملية؟", reply_markup=kb, parse_mode="Markdown")
        await TransferStates.waiting_for_transfer_confirm.set()
    except:
        await message.answer("⚠️ مبلغ غير صالح! أرسل رقماً صحيحاً (مثال: `5`):")

@dp.callback_query_handler(text="confirm_transfer_yes", state=TransferStates.waiting_for_transfer_confirm)
async def transfer_execute(call: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="user_settings_menu"))
    await call.message.edit_text("✅ **تم تحويل المبلغ بنجاح إلى الحساب المستهدف!**", reply_markup=kb, parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="back_to_main")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await show_main_menu(call)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
