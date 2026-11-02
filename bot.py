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
# 1. إعدادات البوت والاتصال الأساسية (ملف موحد)
# ==========================================
API_TOKEN = "5418318795:AAE_s0NJw9IE1JWg6x9JuWQpl0MHDjcFCf8"  # ضع توكن بوتك هنا فقط
ADMIN_IDS = [5396793642]  # ضع آيدي المشرف الخاص بك هنا

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# قاعدة البيانات والإعدادات في مكان واحد لعدم حدوث أي تضارب
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
    "custom_prices": {},
    "user_balances": {},
    "sms_history": {},
    "user_logs": {}
}

def load_db():
    return database

def save_db(db):
    global database
    database = db

# ==========================================
# 2. القواميس الشاملة وحالات الحوار (FSM)
# ==========================================
COUNTRY_NAMES = {
    "0": "روسيا 🇷🇺", "1": "الولايات المتحدة 🇺🇸", "2": "كازاخستان 🇰🇿", "3": "الصين 🇨🇳",
    "4": "الفلبين 🇵🇭", "5": "الهند 🇮🇳", "6": "إندونيسيا 🇮🇩", "7": "ماليزيا 🇲🇾",
    "8": "كينيا 🇰🇪", "9": "فيتنام 🇻🇳", "10": "قيرغيزستان 🇰🇬", "11": "تنزانيا 🇹🇿",
    "12": "سريلانكا 🇱🇰", "14": "باكستان 🇵🇰", "15": "المملكة المتحدة 🇬🇧", "16": "السعودية 🇸🇦",
    "17": "اليمن 🇾🇪", "18": "رواندا 🇷🇼", "19": "مصر 🇪🇬", "22": "المغرب 🇲🇦"
}

SERVICES_CODES = {
    "wa": "واتساب", "tg": "تيليجرام", "ig": "انستقرام", "go": "جوجل",
    "fb": "فيسبوك", "tw": "تويتر", "vi": "فايبر", "imo": "إيمو", "tik": "تيك توك"
}

class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_login_email = State()
    waiting_for_signup_email = State()

class TransferStates(StatesGroup):
    waiting_for_receiver_email = State()
    waiting_for_transfer_amount = State()
    waiting_for_transfer_confirm = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_api_key = State()
    waiting_for_service_price = State()

# ==========================================
# 3. دوال الـ API والبريد الإلكتروني
# ==========================================
def get_smsbower_balance(api_key):
    try:
        url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getBalance"
        res = requests.get(url, timeout=10)
        if res.status_code == 200 and "ACCESS_BALANCE" in res.text:
            return res.text.split(":")[-1]
    except Exception as e:
        logging.error(f"Balance check error: {e}")
    return "0.0"

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
# 4. أمر البداية والقوائم الرئيسية
# ==========================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    db = load_db()
    
    if user_id in db.get("verified_users", []) or user_id in ADMIN_IDS:
        await show_main_menu(message)
    else:
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ أنا انسان (تخطي التحقق)", callback_data="verify_captcha_success")
        )
        await message.answer("🔒 أهلاً بك! يرجى إتمام التحقق الأمني (الكابتشا) للمرة الأولى فقط للمتابعة:", reply_markup=keyboard)
        await UserStates.waiting_for_captcha.set()

@dp.callback_query_handler(text="verify_captcha_success", state=UserStates.waiting_for_captcha)
async def process_captcha(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    db = load_db()
    if user_id not in db["verified_users"]:
        db["verified_users"].append(user_id)
        save_db(db)
    await state.finish()
    await call.message.delete()
    await show_main_menu(call.message)

async def show_main_menu(message_or_call):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🛒 قسم الأرقام الوهمية والتفعيل", callback_data="buy_sim"),
        types.InlineKeyboardButton("⚙️ الإعدادات الشخصية", callback_data="user_settings_menu"),
        types.InlineKeyboardButton("📊 رصيدي وسجلاتي", callback_data="user_profile_stats")
    )
    
    user_id = message_or_call.from_user.id if hasattr(message_or_call, 'from_user') else message_or_call.chat.id
    if user_id in ADMIN_IDS:
        keyboard.add(types.InlineKeyboardButton("🛠 لوحة تحكم المشرف", callback_data="admin_panel"))
        
    text = "🏠 **القائمة الرئيسية للبوت الشامل:**\nاختر ما يناسبك من الخيارات أدناه:"
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_call.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# ==========================================
# 5. تصفح الأرقام والدول
# ==========================================
@dp.callback_query_handler(text="buy_sim")
async def buy_sim_menu(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for srv_code, srv_name in SERVICES_CODES.items():
        keyboard.insert(types.InlineKeyboardButton(srv_name, callback_data=f"buy_app_{srv_code}_0"))
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main"))
    await call.message.edit_text("🛒 **اختر التطبيق المراد تفعيل رقم له:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('buy_app_'))
async def show_countries_for_buying(call: types.CallbackQuery):
    parts = call.data.split('_')
    serv_code = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    try:
        response = requests.get(f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices", timeout=10)
        data = response.json() if response.status_code == 200 else None
        if not data or not isinstance(data, dict):
            await call.answer("⚠️ فشل جلب البيانات من المزود.", show_alert=True)
            return
            
        matched = [cid for cid, srv in data.items() if isinstance(srv, dict) and serv_code in srv]
        PER_PAGE = 12
        total_pages = (len(matched) + PER_PAGE - 1) // PER_PAGE
        current_countries = matched[page * PER_PAGE : (page + 1) * PER_PAGE]
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cid in current_countries:
            cname = COUNTRY_NAMES.get(str(cid), f"دولة ({cid})")
            keyboard.insert(types.InlineKeyboardButton(cname, callback_data=f"get_num_{cid}_{serv_code}"))
            
        nav = []
        if page > 0: nav.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"buy_app_{serv_code}_{page - 1}"))
        if page < total_pages - 1: nav.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"buy_app_{serv_code}_{page + 1}"))
        if nav: keyboard.row(*nav)
        
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع للتطبيقات", callback_data="buy_sim"))
        await call.message.edit_text(f"🌍 **تطبيق ({SERVICES_CODES.get(serv_code, serv_code)}) - صفحة {page+1}/{total_pages}**\nاختر الدولة:", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await call.answer(f"❌ خطأ في الاتصال: {e}", show_alert=True)

# ==========================================
# 6. نظام الشراء وجلب الكود
# ==========================================
@dp.callback_query_handler(lambda c: c.data.startswith('get_num_'))
async def buy_number_from_api(call: types.CallbackQuery):
    parts = call.data.split('_')
    cid = parts[2]
    serv_code = parts[3]
    user_id = call.from_user.id
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    
    try:
        buy_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={serv_code}&country={cid}"
        res = requests.get(buy_url, timeout=10)
        
        if res.status_code != 200 or "ACCESS_NUMBER" not in res.text:
            await call.answer("⚠️ عذراً، لا توجد أرقام متاحة لهذه الخدمة حالياً.", show_alert=True)
            return
            
        resp_parts = res.text.split(':')
        activation_id = resp_parts[1]
        phone_number = resp_parts[2]
        
        if "sms_history" not in db: db["sms_history"] = {}
        db["sms_history"][str(user_id)] = {
            "activation_id": activation_id,
            "phone": phone_number,
            "service": serv_code,
            "country": cid
        }
        save_db(db)
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("🔄 جلب كود التحقق (SMS)", callback_data=f"check_sms_{activation_id}"),
            types.InlineKeyboardButton("❌ إلغاء الطلب", callback_data="back_to_main")
        )
        
        await call.message.edit_text(
            f"✅ **تم شراء الرقم بنجاح!**\n\n"
            f"📱 **الرقم:** `{phone_number}`\n"
            f"🆔 **معرف التفعيل:** `{activation_id}`\n\n"
            f"قم بإدخال الرقم ثم اضغط على زر (جلب كود التحقق):",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception as e:
        await call.answer(f"❌ خطأ: {e}", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('check_sms_'))
async def check_sms_code(call: types.CallbackQuery):
    activation_id = call.data.split('_')[2]
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    
    try:
        status_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
        res = requests.get(status_url, timeout=10)
        
        if res.status_code == 200:
            if "STATUS_WAIT_CODE" in res.text:
                await call.answer("⏳ جاري انتظار وصول الكود...", show_alert=True)
            elif "STATUS_OK" in res.text:
                sms_code = res.text.split(':')[-1]
                user_id = call.from_user.id
                user_data = db.get("sms_history", {}).get(str(user_id), {})
                phone = user_data.get("phone", "غير معروف")
                
                keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main"))
                await call.message.edit_text(
                    f"🎉 **تم استقبال كود التحقق بنجاح!**\n\n"
                    f"📱 **الرقم:** `{phone}`\n"
                    f"🔑 **الكود:** `{sms_code}`",
                    reply_markup=keyboard, parse_mode="Markdown"
                )
            else:
                await call.answer(f"📌 حالة الطلب: {res.text}", show_alert=True)
        else:
            await call.answer("⚠️ فشل الاتصال بالموقع.", show_alert=True)
    except Exception as e:
        await call.answer(f"❌ خطأ: {e}", show_alert=True)

# ==========================================
# 7. لوحة تحكم المشرف وإدارة الأسعار
# ==========================================
@dp.callback_query_handler(text="admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("⚙️ إدارة السيرفرات والأسعار الحقيقية", callback_data="admin_servers_manager"),
        types.InlineKeyboardButton("📢 إذاعة رسالة للمستخدمين", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main")
    )
    await call.message.edit_text("🛠 **لوحة تحكم المشرف:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="admin_servers_manager")
async def admin_servers_manager_menu(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for srv_code, srv_name in SERVICES_CODES.items():
        keyboard.add(types.InlineKeyboardButton(f"تعديل سيرفرات {srv_name}", callback_data=f"adm_app_{srv_code}_0"))
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_panel"))
    await call.message.edit_text("⚙️ **إدارة السيرفرات (اختر التطبيق):**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('adm_app_'))
async def admin_show_countries_paginated(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    parts = call.data.split('_')
    serv_code = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    try:
        response = requests.get(f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices", timeout=10)
        data = response.json() if response.status_code == 200 else None
        if not data or not isinstance(data, dict):
            await call.answer("⚠️ فشل جلب البيانات.", show_alert=True)
            return
        
        matched = [cid for cid, srv in data.items() if isinstance(srv, dict) and serv_code in srv]
        PER_PAGE = 12
        total_pages = (len(matched) + PER_PAGE - 1) // PER_PAGE
        current_countries = matched[page * PER_PAGE : (page + 1) * PER_PAGE]
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cid in current_countries:
            cname = COUNTRY_NAMES.get(str(cid), f"دولة ({cid})")
            keyboard.insert(types.InlineKeyboardButton(cname, callback_data=f"adm_c_serv_{cid}_{serv_code}"))
            
        nav = []
        if page > 0: nav.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"adm_app_{serv_code}_{page - 1}"))
        if page < total_pages - 1: nav.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"adm_app_{serv_code}_{page + 1}"))
        if nav: keyboard.row(*nav)
        
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_servers_manager"))
        await call.message.edit_text(f"🌍 **تطبيق ({serv_code.upper()}) - صفحة {page+1}/{total_pages}**\nاختر الدولة:", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await call.answer(f"❌ خطأ: {e}", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('adm_c_serv_'))
async def admin_show_servers_with_real_prices(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    parts = call.data.split('_')
    cid = parts[3]
    serv_code = parts[4]
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    try:
        response = requests.get(f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices", timeout=10)
        data = response.json() if response.status_code == 200 else None
        
        if not data or str(cid) not in data:
            await call.answer("⚠️ لا توجد بيانات متاحة.", show_alert=True)
            return
            
        service_info = data[str(cid)].get(serv_code, {})
        if not service_info:
            await call.answer("⚠️ لا توجد سيرفرات متاحة.", show_alert=True)
            return
            
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for operator_name, details in service_info.items():
            real_price = details.get('cost', '0.0')
            count = details.get('count', 0)
            btn_text = f"🔌 {operator_name} | السعر: {real_price}$ | المتاح: {count}"
            keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=f"sel_srv_price_{cid}_{serv_code}_{operator_name}"))
            
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع للدول", callback_data=f"adm_app_{serv_code}_0"))
        cname = COUNTRY_NAMES.get(str(cid), f"دولة ({cid})")
        await call.message.edit_text(f"🌐 **الدولة:** {cname}\n📱 **الخدمة:** {serv_code.upper()}\n\n📋 **اختر السيرفر لتعديل سعره:**", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await call.answer(f"❌ خطأ: {e}", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('sel_srv_price_'))
async def admin_select_operator_for_price(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    parts = call.data.split('_')
    cid = parts[3]
    serv_code = parts[4]
    operator_name = parts[5]
    
    async with state.proxy() as data:
        data['edit_cid'] = cid
        data['edit_serv'] = serv_code
        data['edit_operator'] = operator_name
        
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ إلغاء", callback_data="admin_servers_manager"))
    await call.message.edit_text(f"⚙️ **تعديل سعر سيرفر الموقع ({operator_name}):**\n\nأرسل السعر الجديد:", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_service_price.set()

@dp.message_handler(state=AdminStates.waiting_for_service_price)
async def admin_save_new_price(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        new_price = float(message.text.strip().replace(',', '.'))
        if new_price < 0: raise ValueError()
        
        async with state.proxy() as data:
            cid = data.get('edit_cid')
            serv_code = data.get('edit_serv')
            operator = data.get('edit_operator')
            
        db = load_db()
        if "custom_prices" not in db: db["custom_prices"] = {}
        if cid not in db["custom_prices"]: db["custom_prices"][cid] = {}
        if serv_code not in db["custom_prices"][cid]: db["custom_prices"][cid][serv_code] = {}
        
        db["custom_prices"][cid][serv_code][operator] = new_price
        save_db(db)
        
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة للإدارة", callback_data="admin_servers_manager"))
        await message.answer(f"✅ **تم تحديث سعر السيرفر ({operator}) بنجاح إلى: `{new_price}$`**", reply_markup=kb, parse_mode="Markdown")
        await state.finish()
    except:
        await message.answer("⚠️ خطأ! أرسل رقماً صالحاً (مثال: `1.5`):")

# ==========================================
# 8. إعدادات المستخدم والتحويلات
# ==========================================
@dp.callback_query_handler(text="user_settings_menu")
async def user_settings_menu(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("⚠️ تعديل كلمة سر الحساب", callback_data="set_pass"),
        types.InlineKeyboardButton("🔔 مسح سجلات الأرقام", callback_data="set_clear"),
        types.InlineKeyboardButton("🔄 تحويل رصيد لحساب آخر", callback_data="user_transfer_start"),
        types.InlineKeyboardButton("🚪 تسجيل خروج", callback_data="set_logout"),
        types.InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")
    )
    await call.message.edit_text("⚙️ **[ قسم الإعدادات الخاصة بالبوت: ]**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="user_transfer_start")
async def transfer_start(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu"))
    await call.message.edit_text("💸 **تحويل رصيد:**\n\n📧 أرسل **البريد الإلكتروني** للمستلم:", reply_markup=kb, parse_mode="Markdown")
    await TransferStates.waiting_for_receiver_email.set()

@dp.message_handler(state=TransferStates.waiting_for_receiver_email)
async def transfer_get_email(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['receiver_email'] = message.text.strip()
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu"))
    await message.answer("💵 أرسل **المبلغ** المراد تحويله (مثال: `5`):", reply_markup=kb, parse_mode="Markdown")
    await TransferStates.waiting_for_transfer_amount.set()

@dp.message_handler(state=TransferStates.waiting_for_transfer_amount)
async def transfer_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0: raise ValueError()
        async with state.proxy() as data:
            data['transfer_amount'] = amount
            receiver = data['receiver_email']
        kb = types.InlineKeyboardMarkup(row_width=2).add(
            types.InlineKeyboardButton("✅ تأكيد التحويل", callback_data="confirm_transfer_yes"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="user_settings_menu")
        )
        await message.answer(f"📋 **ملخص التحويل:**\n- إلى: `{receiver}`\n- المبلغ: `{amount}$`\n\nهل أنت متأكد؟", reply_markup=kb, parse_mode="Markdown")
        await TransferStates.waiting_for_transfer_confirm.set()
    except:
        await message.answer("⚠️ مبلغ غير صالح! أرسل رقماً صحيحاً (مثال: `5`):")

@dp.callback_query_handler(text="confirm_transfer_yes", state=TransferStates.waiting_for_transfer_confirm)
async def transfer_execute(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="user_settings_menu"))
    await call.message.edit_text("✅ **تم تحويل المبلغ بنجاح!**", reply_markup=kb, parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="user_profile_stats")
async def user_profile_stats(call: types.CallbackQuery):
    user_id = call.from_user.id
    db = load_db()
    balance = db.get("user_balances", {}).get(str(user_id), 0.0)
    history = db.get("sms_history", {}).get(str(user_id), {})
    
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_main"))
    await call.message.edit_text(
        f"📊 **سجلاتي ورصيدي:**\n\n"
        f"💰 **الرصيد:** `{balance}$`\n"
        f"📱 **آخر رقم:** `{history.get('phone', 'لا يوجد')}`",
        reply_markup=kb, parse_mode="Markdown"
    )

@dp.callback_query_handler(text="set_logout")
async def user_logout(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    keyboard = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("🔄 تسجيل الدخول من جديد", callback_data="verify_captcha_success")
    )
    await call.message.edit_text("🚪 **تم تسجيل خروجك بنجاح.**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="set_clear")
async def clear_user_history(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    db = load_db()
    if "sms_history" in db and user_id in db["sms_history"]:
        db["sms_history"].pop(user_id)
        save_db(db)
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="user_settings_menu"))
    await call.message.edit_text("🔔 **تم مسح السجلات بنجاح.**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(text="admin_broadcast")
async def admin_broadcast_prompt(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await call.message.edit_text("📢 **إذاعة رسالة جماعية:**\n\nأرسل النص للإذاعة:", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_broadcast_message.set()

@dp.message_handler(state=AdminStates.waiting_for_broadcast_message)
async def admin_execute_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    broadcast_text = message.text
    db = load_db()
    verified_users = db.get("verified_users", [])
    
    success_count = 0
    for uid in verified_users:
        try:
            await bot.send_message(uid, f"📢 **إشعار من الإدارة:**\n\n{broadcast_text}", parse_mode="Markdown")
            success_count += 1
        except Exception:
            pass
            
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 لوحة المشرف", callback_data="admin_panel"))
    await message.answer(f"✅ **تم الإرسال بنجاح إلى `{success_count}` مستخدم.**", reply_markup=kb, parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="set_pass")
async def user_change_password_prompt(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="user_settings_menu"))
    await call.message.edit_text("⚠️ **تعديل كلمة السر:** تواصل مع الدعم الفني.", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(text="back_to_main")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await show_main_menu(call.message)

@dp.message_handler(content_types=['text'])
async def handle_unexpected_messages(message: types.Message):
    user_id = message.from_user.id
    db = load_db()
    if user_id in db.get("verified_users", []) or user_id in ADMIN_IDs:
        await message.answer("ℹ️ يرجى استخدام الأزرار التفاعلية.")
    else:
        await message.answer("🔒 يرجى إتمام التحقق عبر /start أولاً.")

# ==========================================
# 9. التشغيل النهائي (ملف التشغيل الأوحد)
# ==========================================
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
