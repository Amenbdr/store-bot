import os
import random
import logging
import threading
import requests
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont

from database import load_db, save_db, DEFAULT_PRICES

# ----------------------------------------------------
# 1. خادم الويب (Heartbeat) لمنع التوقف على Render
# ----------------------------------------------------
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ----------------------------------------------------
# 2. إعدادات البوت الأساسية
# ----------------------------------------------------
API_TOKEN = "5418318795:AAE_s0NJw9IE1JWg6x9JuWQpl0MHDjcFCf8"
ADMIN_IDS = [5396793642]
REQUIRED_CHANNEL = "@SIM_NUMBERS" # قناة الاشتراك الإجباري

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_reg_email = State()
    waiting_for_reg_otp = State()
    waiting_for_reg_password = State()
    waiting_for_login_email = State()
    waiting_for_login_password = State()
    waiting_for_coupon_code = State()

class AdminStates(StatesGroup):
    waiting_for_add_id = State()
    waiting_for_add_amount = State()
    waiting_for_coupon_code = State()
    waiting_for_coupon_amount = State()
    waiting_for_country_name = State()
    waiting_for_country_price = State()
    waiting_for_country_stock = State()
    waiting_for_sms_api_key = State()

admin_temp_data = {}
captcha_storage = {}
temp_auth_data = {}

def get_main_menu(user_id):
    menu_keyboard = InlineKeyboardMarkup(row_width=2)
    menu_keyboard.add(InlineKeyboardButton("⭐ الخدمات المطلوبة أكثر", callback_data="top_services"))
    menu_keyboard.add(
        InlineKeyboardButton("💖 خدمات الرشق 98", callback_data="buy_smm"),
        InlineKeyboardButton("🎁 شحن ألعاب 🎮", callback_data="buy_games")
    )
    menu_keyboard.add(
        InlineKeyboardButton("📞 أرقام وهمية وتفعيل", callback_data="buy_sim"),
        InlineKeyboardButton("🛍️ متجر المنتجات الرقمية", callback_data="digital_store")
    )
    menu_keyboard.add(
        InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        InlineKeyboardButton("📝 سجل طلباتي", callback_data="my_orders")
    )
    menu_keyboard.add(
        InlineKeyboardButton("🔍 بحث عن خدمة", callback_data="search_service"),
        InlineKeyboardButton("🔄 حالة الطلب", callback_data="order_status")
    )
    menu_keyboard.add(InlineKeyboardButton("💰 شحن الرصيد برقم (كارت)", callback_data="recharge_balance"))
    
    if user_id in ADMIN_IDS:
        menu_keyboard.add(InlineKeyboardButton("⚙️ لوحة تحكم المشرفين", callback_data="admin_panel"))
        
    return menu_keyboard

def generate_captcha_image(number_str):
    img = Image.new('RGB', (220, 80), color=(30, 30, 30))
    d = ImageDraw.Draw(img)
    for _ in range(6):
        x1 = random.randint(0, 220)
        y1 = random.randint(0, 80)
        x2 = random.randint(0, 220)
        y2 = random.randint(0, 80)
        d.line([x1, y1, x2, y2], fill=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)), width=2)
    try:
        font = ImageFont.load_default()
    except:
        font = None
    d.text((45, 20), number_str, fill=(255, 255, 255), font=font)
    bio = BytesIO()
    bio.name = 'captcha.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# ----------------------------------------------------
# 3. الأوامر والتحقق الإجباري (قناة + كابتشا + إيميل)
# ----------------------------------------------------
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    db = load_db()
    str_user_id = str(user_id)
    
    if REQUIRED_CHANNEL:
        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
            if member.status in ['left', 'kicked']:
                sub_kb = InlineKeyboardMarkup(row_width=1)
                sub_kb.add(
                    InlineKeyboardButton(f"📢 قناة البوت الرسمية", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"),
                    InlineKeyboardButton("✅ تحقق من الانضمام", callback_data="check_subscription")
                )
                await message.answer(
                    "❌ **عذراً عزيزي!**\n\n"
                    f"يجب عليك الاشتراك في قناة البوت ({REQUIRED_CHANNEL}) أولاً لتتمكن من استخدامه.\n\n"
                    "يرجى الاشتراك ثم الضغط على زر (تحقق من الانضمام) بالأسفل 👇",
                    reply_markup=sub_kb, parse_mode="Markdown"
                )
                return
        except Exception:
            pass

    if str_user_id not in db.get("verified", {}):
        rand_num = str(random.randint(10000, 99999))
        captcha_storage[user_id] = rand_num
        photo = generate_captcha_image(rand_num)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔄 تغيير الصورة", callback_data="refresh_captcha"))
        await message.answer_photo(
            photo=photo, 
            caption="♻️ - **يرجى كتابة الرقم الموجود في الصورة أعلاه وإرساله إلينا للتحقق من أنك لست روبوتاً.**", 
            reply_markup=kb, 
            parse_mode="Markdown"
        )
        await UserStates.waiting_for_captcha.set()
        return

    user_data = db["users"].get(str_user_id, {"balance": 0.0, "name": user_name, "email": None})
    if not user_data.get("email"):
        reg_kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("📝 تسجيل حساب جديد بالإيميل (إجباري)", callback_data="register_email"),
            InlineKeyboardButton("🔑 تسجيل الدخول بإيميل سابق", callback_data="login_email")
        )
        await message.answer(
            "⚠️ **مرحباً بك! لتتمكن من استخدام المتجر واستعراض الأقسام، يرجى ربط حسابك ببريد إلكتروني (إيميل) وكلمة مرور أولاً:**",
            reply_markup=reg_kb, parse_mode="Markdown"
        )
        return

    balance = user_data.get("balance", 0.0)
    email = user_data.get("email", "غير مسجل")
    
    welcome_text = (
        f"👋 مرحباً ، تفاصِيل حسابك 👇.\n\n"
        f"📱 ⌯ الحساب : `{email}` 🤖.\n"
        f"🏦 ⌯ الرصيد : `$ {balance:.2f}` 💸.\n"
        f"💼 ⌯ نوع الحساب : عادي 📲 .\n\n"
        f"🎛 ⌯ تحكم بالبوت عبر الأزرار في الأسفل .\n"
        f"💬 ⌯ آخر الأخبار: 👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.callback_query_handler(text="check_subscription")
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    await send_welcome(call.message, state)

@dp.callback_query_handler(text="refresh_captcha", state=UserStates.waiting_for_captcha)
async def refresh_captcha_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    rand_num = str(random.randint(10000, 99999))
    captcha_storage[user_id] = rand_num
    photo = generate_captcha_image(rand_num)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔄 تغيير الصورة", callback_data="refresh_captcha"))
    try:
        await call.message.edit_media(types.InputMediaPhoto(media=photo, caption="♻️ - **أدخل الرقم الجديد الظاهر في الصورة:**", parse_mode="Markdown"), reply_markup=kb)
    except:
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption="♻️ - **أدخل الرقم الجديد الظاهر في الصورة:**", reply_markup=kb, parse_mode="Markdown")

@dp.message_handler(state=UserStates.waiting_for_captcha)
async def process_captcha_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text.strip() == captcha_storage.get(user_id):
        db = load_db()
        if "verified" not in db: db["verified"] = {}
        db["verified"][str(user_id)] = True
        save_db(db)
        await message.answer("✅ **تم التحقق بنجاح!**", parse_mode="Markdown")
        await state.finish()
        await send_welcome(message, state)
    else:
        await message.answer("❌ **الرمز غير صحيح!** أعد كتابة الأرقام الظاهرة في الصورة:")

# ----------------------------------------------------
# 4. إدارة حسابات المستخدمين
# ----------------------------------------------------
@dp.callback_query_handler(text="my_account")
async def my_account_handler(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    db = load_db()
    user_data = db["users"].get(user_id, {"balance": 0.0, "email": None})
    balance = user_data.get("balance", 0.0)
    email = user_data.get("email")
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    if not email:
        keyboard.add(
            InlineKeyboardButton("📝 تسجيل حساب جديد بالإيميل", callback_data="register_email"),
            InlineKeyboardButton("🔑 تسجيل الدخول", callback_data="login_email")
        )
    else:
        keyboard.add(InlineKeyboardButton("🔒 تسجيل الخروج من الحساب", callback_data="logout_email"))
        
    keyboard.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main"))
    
    email_display = email if email else "غير مسجل"
    text = (
        f"👤 **إدارة حسابك الشخصي:**\n\n"
        f"🆔 أيدي التليجرام: `{user_id}`\n"
        f"📧 البريد الإلكتروني: `{email_display}`\n"
        f"💰 الرصيد الحالي: `{balance:.2f}$`"
    )
    try:
        await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except:
        await call.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="register_email")
async def reg_email_start(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    try:
        await call.message.edit_text("📝 **تسجيل حساب جديد**\n\nالرجاء إرسال **البريد الإلكتروني** الخاص بك:", reply_markup=kb, parse_mode="Markdown")
    except:
        await call.message.answer("📝 **تسجيل حساب جديد**\n\nالرجاء إرسال **البريد الإلكتروني** الخاص بك:", reply_markup=kb, parse_mode="Markdown")
    await UserStates.waiting_for_reg_email.set()

@dp.message_handler(state=UserStates.waiting_for_reg_email)
async def reg_email_step(message: types.Message, state: FSMContext):
    email = message.text.strip().lower()
    if "@" not in email or "." not in email:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
        await message.answer("⚠️ البريد غير صالح. أرسل إيميل صحيح:", reply_markup=kb)
        return
        
    db = load_db()
    for uid, udata in db["users"].items():
        if udata.get("email") and udata.get("email").lower() == email:
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
            await message.answer("⚠️ **هذا البريد الإلكتروني مسجل مسبقاً لحساب آخر!** أرسل بريداً مختلفاً:", reply_markup=kb)
            return
            
    otp_code = str(random.randint(1000, 9999))
    user_id = str(message.from_user.id)
    temp_auth_data[user_id] = {"email": email, "otp": otp_code}
    
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await message.answer(
        f"✉️ **تم إنشاء كود التحقق بنجاح!**\n\n"
        f"🔑 الكود الخاص بك هو: `{otp_code}`\n\n"
        f"الرجاء إرسال **كود التحقق (OTP)** المكون من 4 أرقام هنا:",
        reply_markup=kb, parse_mode="Markdown"
    )
    await UserStates.waiting_for_reg_otp.set()

@dp.message_handler(state=UserStates.waiting_for_reg_otp)
async def reg_otp_step(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    entered_otp = message.text.strip()
    
    saved_data = temp_auth_data.get(user_id)
    if not saved_data or entered_otp != saved_data.get("otp"):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
        await message.answer("⚠️ **كود التحقق غير صحيح!** أرسل الكود الصحيح:", reply_markup=kb)
        return
        
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await message.answer("✅ **تم التحقق من البريد بنجاح!**\n\nالآن أرسل **كلمة المرور** الجديدة لحسابك:", reply_markup=kb, parse_mode="Markdown")
    await UserStates.waiting_for_reg_password.set()

@dp.message_handler(state=UserStates.waiting_for_reg_password)
async def reg_pass_step(message: types.Message, state: FSMContext):
    password = message.text.strip()
    user_id = str(message.from_user.id)
    email = temp_auth_data.get(user_id, {}).get("email")
    
    db = load_db()
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0.0, "name": message.from_user.first_name}
        
    db["users"][user_id]["email"] = email
    db["users"][user_id]["password"] = password
    save_db(db)
    
    balance = db["users"][user_id]["balance"]
    welcome_text = (
        f"👋 مرحباً ، تفاصِيل حسابك 👇.\n\n"
        f"📱 ⌯ الحساب : `{email}` 🤖.\n"
        f"🏦 ⌯ الرصيد : `$ {balance:.2f}` 💸.\n"
        f"💼 ⌯ نوع الحساب : عادي 📲 .\n\n"
        f"🎛 ⌯ تحكم بالبوت عبر الأزرار في الأسفل .\n"
        f"💬 ⌯ آخر الأخبار: 👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="login_email")
async def login_email_start(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    try:
        await call.message.edit_text("🔑 **تسجيل الدخول**\n\nأرسل **البريد الإلكتروني** المسجل به:", reply_markup=kb, parse_mode="Markdown")
    except:
        await call.message.answer("🔑 **تسجيل الدخول**\n\nأرسل **البريد الإلكتروني** المسجل به:", reply_markup=kb, parse_mode="Markdown")
    await UserStates.waiting_for_login_email.set()

@dp.message_handler(state=UserStates.waiting_for_login_email)
async def login_email_step(message: types.Message, state: FSMContext):
    temp_auth_data[str(message.from_user.id)] = {"login_email": message.text.strip().lower()}
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await message.answer("🔑 الآن أرسل **كلمة المرور**:", reply_markup=kb)
    await UserStates.waiting_for_login_password.set()

@dp.message_handler(state=UserStates.waiting_for_login_password)
async def login_pass_step(message: types.Message, state: FSMContext):
    password = message.text.strip()
    user_id = str(message.from_user.id)
    email = temp_auth_data.get(user_id, {}).get("login_email")
    
    db = load_db()
    found = False
    for uid, udata in db["users"].items():
        if udata.get("email") and udata.get("email").lower() == email and udata.get("password") == password:
            found = True
            db["users"][user_id]["balance"] = udata.get("balance", 0.0)
            db["users"][user_id]["email"] = email
            db["users"][user_id]["password"] = password
            save_db(db)
            break
            
    if found:
        balance = db["users"][user_id]["balance"]
        welcome_text = (
            f"👋 مرحباً ، تفاصِيل حسابك 👇.\n\n"
            f"📱 ⌯ الحساب : `{email}` 🤖.\n"
            f"🏦 ⌯ الرصيد : `$ {balance:.2f}` 💸.\n"
            f"💼 ⌯ نوع الحساب : عادي 📲 .\n\n"
            f"🎛 ⌯ تحكم بالبوت عبر الأزرار في الأسفل .\n"
            f"💬 ⌯ آخر الأخبار: 👇"
        )
        await message.answer(welcome_text, reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown")
        await state.finish()
    else:
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("🔑 إعادة محاولة تسجيل الدخول", callback_data="login_email"),
            InlineKeyboardButton("📝 تسجيل حساب جديد", callback_data="register_email")
        )
        await message.answer("⚠️ البريد الإلكتروني أو كلمة المرور غير صحيحة!", reply_markup=kb)
        await state.finish()

@dp.callback_query_handler(text="logout_email")
async def logout_email(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    db = load_db()
    if user_id in db["users"]:
        db["users"][user_id]["email"] = None
        db["users"][user_id]["password"] = None
        save_db(db)
    await call.answer("تم تسجيل الخروج بنجاح", show_alert=True)
    await send_welcome(call.message, FSMContext(dp, storage, call.from_user.id, call.message.chat.id))

@dp.callback_query_handler(text="back_to_main")
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    db = load_db()
    user_data = db["users"].get(str(user_id), {})
    if not user_data.get("email"):
        await send_welcome(call.message, state)
        return
    balance = user_data.get("balance", 0.0)
    email = user_data.get("email", "غير مسجل")
    
    welcome_text = (
        f"👋 مرحباً ، تفاصِيل حسابك 👇.\n\n"
        f"📱 ⌯ الحساب : `{email}` 🤖.\n"
        f"🏦 ⌯ الرصيد : `$ {balance:.2f}` 💸.\n"
        f"💼 ⌯ نوع الحساب : عادي 📲 .\n\n"
        f"🎛 ⌯ تحكم بالبوت عبر الأزرار في الأسفل .\n"
        f"💬 ⌯ آخر الأخبار: 👇"
    )
    try:
        await call.message.edit_text(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    except:
        await call.message.delete()
        await call.message.answer(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.callback_query_handler(text="cancel_process", state="*")
async def cancel_process_callback(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await send_welcome(call.message, state)

# ----------------------------------------------------
# 5. قسم الأرقام الوهمية (واتساب وتيليجرام) عبر SMSBower API
# ----------------------------------------------------
@dp.callback_query_handler(text="buy_sim")
async def buy_sim_menu(call: types.CallbackQuery):
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    if not api_key:
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        try:
            await call.message.edit_text("⚠️ **عذراً، قسم الأرقام الوهمية غير متاح حالياً (لم يتم ضبط إعدادات API من قبل المشرف).**", reply_markup=keyboard, parse_mode="Markdown")
        except:
            await call.message.answer("⚠️ **عذراً، قسم الأرقام الوهمية غير متاح حالياً.**", reply_markup=keyboard, parse_mode="Markdown")
        return

    # جلب الدول والأسعار للواتساب والتيليجرام مباشرة من موقع SMSBower
    try:
        prices_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices"
        response = requests.get(prices_url, timeout=10)
        data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        
        if data:
            target_services = ["wa", "tg"]
            count = 0
            for country_id, services in data.items():
                if count >= 10: break # عرض أول 10 دول متوفرة
                for serv_code in target_services:
                    if serv_code in services:
                        serv_info = services[serv_code]
                        price = float(serv_info.get('cost', 1.0))
                        stock = serv_info.get('count', 0)
                        if stock > 0:
                            serv_name = "واتساب 🟢" if serv_code == "wa" else "تيليجرام 🔵"
                            btn_text = f"{serv_name} (دولة {country_id}) – ${price:.2f} · المتاح: {stock}"
                            # callback يحمل معلومات الشراء مباشرة: buy_api_{country_id}_{serv_code}_{price}
                            keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"buy_api_{country_id}_{serv_code}_{price}"))
                            count += 1
    except Exception as e:
        logging.error(f"Error fetching prices: {e}")
        
    keyboard.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main"))
    
    try:
        await call.message.edit_text("📱 **شراء أرقام واتساب وتيليجرام تلقائياً:**\n\nاختر الرقم المناسب:", reply_markup=keyboard, parse_mode="Markdown")
    except:
        await call.message.answer("📱 **شراء أرقام واتساب وتيليجرام تلقائياً:**\n\nاختر الرقم المناسب:", reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# 6. نظام تأكيد الشراء التلقائي وتفعيل الطلب
# ----------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith('buy_api_'))
async def process_api_buy_request(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split('_')
    country_id = parts[2]
    service_code = parts[3]
    price = float(parts[4])
    
    item_name = "واتساب 🟢" if service_code == "wa" else "تيليجرام 🔵"
    admin_temp_data[str(call.from_user.id)] = {
        "item": item_name,
        "price": price,
        "country_id": country_id,
        "service_code": service_code
    }
    
    db = load_db()
    user_id = str(call.from_user.id)
    user_balance = db["users"].get(user_id, {}).get("balance", 0.0)
    
    if user_balance < price:
        await call.answer("❌ رصيدك الحالي غير كافٍ لإتمام الشراء!", show_alert=True)
        return
        
    confirm_kb = InlineKeyboardMarkup(row_width=2)
    confirm_kb.add(
        InlineKeyboardButton("✅ تأكيد الشراء", callback_data="confirm_sms_yes"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")
    )
    
    await call.message.edit_text(
        f"🛒 **تأكيد عملية الشراء الفوري:**\n\n"
        f"📦 الخدمة: **{item_name} (دولة رقم {country_id})**\n"
        f"💵 السعر المطلوب: `{price}$`\n"
        f"💰 رصيدك الحالي: `{user_balance}$`\n\n"
        f"هل أنت متأكد من رغبتك في إتمام الشراء واستخراج الرقم فوراً؟",
        reply_markup=confirm_kb, parse_mode="Markdown"
    )

@dp.callback_query_handler(text="confirm_sms_yes")
async def execute_sms_order(call: types.CallbackQuery, state: FSMContext):
    
