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
REQUIRED_CHANNEL = "@SPEDERCH"
LOG_CHANNEL_ID = "@SIM_NUMBERS"  # ضع هنا معرف قناتك الخاصة بالأرشيف

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
    waiting_for_sub_amount = State()
    waiting_for_coupon_code = State()
    waiting_for_coupon_amount = State()
    waiting_for_sms_api_key = State()
    waiting_for_new_country_id = State()
    waiting_for_new_country_name = State()

admin_temp_data = {}
captcha_storage = {}
temp_auth_data = {}

# قاموس الدول مع الأعلام
# قاموس جميع الدول مع الأعلام والأسماء العربية
# قاموس جميع الدول مرتبة مع الأعلام والأسماء العربية
COUNTRY_NAMES = {
    "0": "🇷🇺 روسيا",
    "1": "🇺🇸 الولايات المتحدة",
    "2": "🇰🇿 كازاخستان",
    "3": "🇨🇳 الصين",
    "4": "🇵🇭 الفلبين",
    "5": "🇮🇳 الهند",
    "6": "🇮🇩 إندونيسيا",
    "7": "🇲🇾 ماليزيا",
    "8": "🇰🇪 كينيا",
    "9": "🇻🇳 فيتنام",
    "10": "🇰🇬 قيرغيزستان",
    "11": "🇹🇿 تنزانيا",
    "12": "🇱🇰 سريلانكا",
    "13": "🇮🇩 إندونيسيا",
    "14": "🇵🇰 باكستان",
    "15": "🇬🇧 المملكة المتحدة",
    "16": "🇸🇦 السعودية",
    "17": "🇾🇪 اليمن",
    "18": "🇷🇼 رواندا",
    "19": "🇪🇬 مصر",
    "20": "🇮🇳 الهند",
    "21": "🇲🇦 المغرب",
    "22": "🇳🇬 نيجيريا",
    "23": "🇲🇴 ماكاو",
    "24": "🇵🇱 بولندا",
    "25": "🇦🇹 أستراليا",
    "26": "🇮🇷 إيران",
    "27": "🇰🇵 كوريا الشمالية",
    "28": "🇩🇿 الجزائر",
    "29": "🇹🇼 تايوان",
    "30": "🇪🇸 إسبانيا",
    "31": "🇸🇾 سوريا",
    "32": "🇷🇴 رومانيـا",
    "33": "🇨🇴 كولومبيا",
    "34": "🇪🇪 إستونيا",
    "35": "🇦🇿 أذربيجان",
    "36": "🇨🇦 كندا",
    "37": "🇲🇦 المغرب",
    "38": "🇬🇭 غانا",
    "39": "🇦🇷 الأرجنتين",
    "40": "🇫🇷 فرنسا",
    "41": "🇧🇷 البرازيل",
    "42": "🇧🇬 بلغاريا",
    "43": "🇩🇪 ألمانيا",
    "44": "🇱🇹 ليتوانيا",
    "45": "🇮🇹 إيطاليا",
    "46": "🇪🇸 إسبانيا",
    "47": "🇲🇼 ملاوي",
    "48": "🇳🇱 هولندا",
    "49": "🇱🇻 لاتفيا",
    "50": "🇸🇪 السويد",
    "51": "🇲🇽 المكسيك",
    "52": "🇧🇷 البرازيل",
    "53": "🇯🇴 الأردن",
    "54": "🇫🇮 فنلندا",
    "55": "🇻🇪 فنزويلا",
    "56": "🇿🇦 جنوب أفريقيا",
    "57": "🇷🇸 صربيا",
    "58": "🇮🇶 العراق",
    "59": "🇹🇷 تركيا",
    "60": "🇨🇿 التشيك",
    "61": "🇺🇦 أوكرانيا",
    "62": "🇸🇰 سلوفاكيا",
    "63": "🇰🇼 الكويت",
    "64": "🇸🇦 السعودية",
    "65": "🇦🇪 الإمارات",
    "66": "🇧🇭 البحرين",
    "67": "🇴🇲 عمان",
    "68": "🇶🇦 قطر",
    "69": "🇸🇩 السودان",
    "70": "🇱🇾 ليبيا",
    "71": "🇹🇳 تونس",
    "72": "🇱🇧 لبنان",
    "73": "🇺🇦 أوكرانيا",
}


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
# 3. الأوامر والتحقق الإجباري
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
# 5. قسم الأرقام الوهمية (عرض الدول بالأعلام العربية)
# ----------------------------------------------------
@dp.callback_query_handler(text="buy_sim")
async def buy_sim_menu(call: types.CallbackQuery):
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if not api_key:
        keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        await call.message.edit_text("⚠️ **عذراً، لم يتم ضبط مفتاح API الخاص بموقع SMSBower من قبل المشرف.**", reply_markup=keyboard, parse_mode="Markdown")
        return

    try:
        prices_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices"
        response = requests.get(prices_url, timeout=8)
        data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        if data and isinstance(data, dict):
            admin_temp_data[f"prices_{call.from_user.id}"] = data
    except Exception as e:
        logging.error(f"Error fetching prices: {e}")

    for country_id, country_name in COUNTRY_NAMES.items():
        keyboard.insert(InlineKeyboardButton(country_name, callback_data=f"sel_country_{country_id}"))
        
    keyboard.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main"))
    
    try:
        await call.message.edit_text(
            "📱 **قسم الأرقام الوهمية والتفعيل:**\n\n"
            "اختر **الدولة** المطلوبة من الأزرار أدناه لعرض الخدمات والسيرفرات المتوفرة:",
            reply_markup=keyboard, 
            parse_mode="Markdown"
        )
    except:
        await call.message.answer(
            "📱 **قسم الأرقام الوهمية والتفعيل:**\n\n"
            "اختر **الدولة** المطلوبة من الأزرار أدناه لعرض الخدمات والسيرفرات المتوفرة:",
            reply_markup=keyboard, 
            parse_mode="Markdown"
        )

# ----------------------------------------------------
# 6. اختيار الدولة ثم عرض الخدمات والأسعار المخصصة
# ----------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith('sel_country_'))
async def process_country_selection(call: types.CallbackQuery):
    country_id = call.data.split('_')[2]
    user_id = call.from_user.id
    
    data = admin_temp_data.get(f"prices_{user_id}")
    if not data or country_id not in data:
        await call.answer("⚠️ انتهت صلاحية البيانات، يرجى إعادة اختيار الدولة.", show_alert=True)
        return
        
    services = data[country_id]
    country_name = COUNTRY_NAMES.get(str(country_id), f"دولة ({country_id})")
    
    db = load_db()
    custom_prices = db.get("custom_prices", {"wa": 0.50, "tg": 0.50, "ig": 0.40})
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    target_services = {"wa": "واتساب 🟢", "tg": "تيليجرام 🔵", "ig": "انستقرام 🟣"}
    
    available_count = 0
    for serv_code, serv_info in services.items():
        if isinstance(serv_info, dict):
            stock = serv_info.get('count', 0)
            
            if stock > 0 and serv_code in target_services:
                serv_display_name = target_services[serv_code]
                display_price = custom_prices.get(serv_code, 0.50)
                
                btn_text = f"{serv_display_name} | 💰 السعر: {display_price}$ | 📦 المتاح: {stock}"
                keyboard.add(InlineKeyboardButton(btn_text, callback_data=f"buy_serv_{country_id}_{serv_code}_{display_price}"))
                available_count += 1

    keyboard.add(InlineKeyboardButton("🔙 رجوع لقائمة الدول", callback_data="buy_sim"))
    
    if available_count == 0:
        await call.answer("⚠️ لا توجد أرقام متوفرة حالياً لهذه الدولة!", show_alert=True)
        return
        
    await call.message.edit_text(
        f"🌍 **الدولة المحددة:** {country_name}\n\n"
        f"اختر **الخدمة (السيرفر)** المطلوبة أدناه لإتمام الشراء:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ----------------------------------------------------
# 7. تأكيد الشراء التلقائي وتفعيل الطلب
# ----------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith('buy_serv_'))
async def process_server_buy_request(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split('_')
    country_id = parts[2]
    service_code = parts[3]
    price = float(parts[4])
    
    item_name = "واتساب 🟢" if service_code == "wa" else ("تيليجرام 🔵" if service_code == "tg" else "انستقرام 🟣")
    country_name = COUNTRY_NAMES.get(str(country_id), f"دولة {country_id}")
    
    admin_temp_data[str(call.from_user.id)] = {
        "item": f"{item_name} - {country_name}",
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
        InlineKeyboardButton("❌ إلغاء", callback_data="buy_sim")
    )
    
    await call.message.edit_text(
        f"🛒 **تأكيد عملية الشراء:**\n\n"
        f"📦 الخدمة: **{item_name}**\n"
        f"🌍 الدولة: **{country_name}**\n"
        f"💵 السعر المطلوب: `{price}$`\n"
        f"💰 رصيدك الحالي: `{user_balance}$`\n\n"
        f"هل أنت متأكد من رغبتك في خصم المبلغ وشراء الرقم فوراً؟",
        reply_markup=confirm_kb, parse_mode="Markdown"
    )

@dp.callback_query_handler(text="confirm_sms_yes")
async def execute_sms_order(call: types.CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    order_info = admin_temp_data.get(user_id)
    
    if not order_info:
        await call.answer("⚠️ انتهت صلاحية الطلب، حاول مرة أخرى.", show_alert=True)
        await send_welcome(call.message, state)
        return
        
    price = order_info["price"]
    country_id = order_info["country_id"]
    service_code = order_info["service_code"]
    item_name = order_info["item"]
    country_name = COUNTRY_NAMES.get(str(country_id), f"دولة {country_id}")
    
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    
    if not api_key:
        await call.answer("❌ مفتاح API غير متوفر!", show_alert=True)
        return
        
    if db["users"].get(user_id, {}).get("balance", 0.0) < price:
        await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)
        return
        
    buy_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={service_code}&country={country_id}"
    
    try:
        response = requests.get(buy_url, timeout=15)
        res_text = response.text.strip()
        
        if "ACCESS_NUMBER" in res_text:
            res_parts = res_text.split(":")
            activation_id = res_parts[1]
            phone_number = res_parts[2]
            
            db["users"][user_id]["balance"] -= price
            save_db(db)
            
            if "active_orders" not in db: db["active_orders"] = {}
            db["active_orders"][user_id] = {
                "activation_id": activation_id,
                "phone": phone_number,
                "item": item_name,
                "price": price,
                "country_name": country_name
            }
            save_db(db)
            
            order_kb = InlineKeyboardMarkup(row_width=1)
            order_kb.add(
                InlineKeyboardButton("🔄 تغير الرقم", callback_data="buy_sim"),
                InlineKeyboardButton("✳️ تحديث.", callback_data="check_sms_code"),
                InlineKeyboardButton("⚠️ إلغاء.", callback_data="cancel_sms_order"),
                InlineKeyboardButton("🔙 رجوع.", callback_data="back_to_main")
            )
            
            success_text = (
                f"☑️ | تم شراء رقم جديد\n\n"
                f"☑️ | الدولة : {country_name}\n"
                f"☑️ | التطبيق : {item_name}\n\n"
                f"☎️ | الرقم : `+{phone_number}`\n"
                f"🌐 | الحالة : Pending ⋯\n"
                f"💵 | السعر : `{price} P`\n"
                f"☑️ | اضغط على الرقم لنسخه!\n"
                f"🛜 | أدخل الرقم في التطبيق لوصول الكود، ثم اضغط على زر تحديث."
            )
            
            await call.message.edit_text(success_text, reply_markup=order_kb, parse_mode="Markdown")
        else:
            await call.answer(f"❌ عذراً، فشل الشراء من الموقع: {res_text}", show_alert=True)
            
    except Exception as e:
        await call.answer(f"❌ حدث خطأ في الاتصال بالموقع: {str(e)}", show_alert=True)
        
    if user_id in admin_temp_data:
        del admin_temp_data[user_id]
        
    await state.finish()

@dp.callback_query_handler(text="cancel_sms_order")
async def cancel_sms_order_handler(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    db = load_db()
    if "active_orders" in db and user_id in db["active_orders"]:
        del db["active_orders"][user_id]
        save_db(db)
    await call.answer("⚠️ تم إلغاء الطلب.", show_alert=True)
    await back_to_main_menu(call, FSMContext(dp, storage, call.from_user.id, call.message.chat.id))

# ----------------------------------------------------
# 8. جلب كود التحقق وإرسال التقرير الاحترافي للقناة
# ----------------------------------------------------
@dp.callback_query_handler(text="check_sms_code")
async def check_sms_code_handler(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    db = load_db()
    
    order_data = db.get("active_orders", {}).get(user_id)
    if not order_data:
        await call.answer("⚠️ لا يوجد لديك طلب نشط حالياً!", show_alert=True)
        return
        
    activation_id = order_data["activation_id"]
    phone_number = order_data["phone"]
    item_name = order_data.get("item", "واتساب")
    price = order_data.get("price", 0.0)
    country_name = order_data.get("country_name", "الدولة")
    
    api_key = db.get("settings", {}).get("smsbower_api_key")
    if not api_key:
        await call.answer("❌ مفتاح API غير متوفر!", show_alert=True)
        return
        
    status_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={activation_id}"
    
    try:
        response = requests.get(status_url, timeout=10)
        res_text = response.text.strip()
        
        if "STATUS_WAIT_CODE" in res_text:
            await call.answer("⏳ لم تصل رسالة التحقق بعد، انتظر قليلاً ثم حاول مجدداً.", show_alert=True)
            
        elif "STATUS_OK" in res_text or ":" in res_text:
            sms_code = res_text.split(":")[-1]
            
            await call.answer("🔔 تنبيه! الكود وصل بنجاح!", show_alert=True)
            
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(
                InlineKeyboardButton("🔄 طلب كود آخر", callback_data="buy_sim"),
                InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")
            )
            
            formatted_text = (
                f"🔔 **تنبيه!** 📨\n"
                f"الكود للرقم: `+{phone_number}`\n"
                f"أصبح جاهزاً الآن.\n\n"
                f"> 🎁 **تهانينا! وصل كودك.**\n"
                f"> ☎️ **الرقم:** `+{phone_number}`\n"
                f"> 📨 **الكود:** `{sms_code}`\n"
                f"> 💰 **السعر:** `{price} USD`\n"
                f"> ↪️ **التطبيق:** `{item_name}`\n\n"
                f"> 🔄 **تم تحديث الكود.**"
            )
            
            try:
                await call.message.edit_text(formatted_text, reply_markup=kb, parse_mode="Markdown")
            except:
                await call.message.answer(formatted_text, reply_markup=kb, parse_mode="Markdown")
                
            # إرسال التقرير الاحترافي للقناة بتنسيق مطابق تماماً للصورة
            try:
                masked_phone = f"...{phone_number[-8:]}" if len(phone_number) > 8 else phone_number
                masked_user = f"...{user_id[-7:]}" if len(user_id) > 7 else user_id
                
                channel_kb = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🤖 شراء رقم من نفس السيرفر 🌐", url=f"https://t.me/{(await bot.get_me()).username}")
                )
                
                log_text = (
                    f"『 **SUPER SIM BOT** 』 ≡ تفعيلات - 📢\n\n"
                    f"☑️ - تم شراء رقم من البوت بنجاح 🔊\n\n"
                    f"🌐 - السيرفر : العروض\n"
                    f"🇸🇦 - الدولة : {country_name}\n"
                    f"✅ - تطبيق : {item_name}\n"
                    f"☎️ - الرقم : `+{masked_phone}`\n"
                    f"💵 - السعر : `{price:.2f} P`\n"
                    f"🆔 - العميل : `{masked_user}`\n\n"
                    f"📬 - رسالة الكود : {{ `{sms_code}` }} +"
                )
                await bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text, reply_markup=channel_kb, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Failed to send log to channel: {e}")
                
            if user_id in db["active_orders"]:
                del db["active_orders"][user_id]
                save_db(db)
                
        else:
            await call.answer(f"ℹ️ حالة الطلب حالياً: {res_text}", show_alert=True)
            
    except Exception as e:
        await call.answer(f"❌ حدث خطأ أثناء الاتصال بالموقع: {str(e)}", show_alert=True)

# ----------------------------------------------------
# الألعاب وأقسام الشحن
# ----------------------------------------------------
@dp.callback_query_handler(text="buy_games")
async def buy_games_menu(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("PUBG Mobile 🎮", callback_data="game_pubg"),
        InlineKeyboardButton("Free Fire 🔥", callback_data="game_ff"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
    )
    await call.message.edit_text("🎮 **قسم الألعاب**\n\nاختر اللعبة:", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="game_pubg")
async def pubg_packages(call: types.CallbackQuery):
    db = load_db()
    prices = db.get("prices", DEFAULT_PRICES)
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(f"60 شدة - {prices.get('pubg_60', 1.0)}$", callback_data="buy_item_pubg_60"),
        InlineKeyboardButton(f"325 شدة - {prices.get('pubg_325', 5.0)}$", callback_data="buy_item_pubg_325"),
        InlineKeyboardButton("🔙 رجوع", callback_data="buy_games")
    )
    await call.message.edit_text("🎮 **باقات PUBG:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="game_ff")
async def ff_packages(call: types.CallbackQuery):
    db = load_db()
    prices = db.get("prices", DEFAULT_PRICES)
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(f"100 جوهرة - {prices.get('ff_100', 1.0)}$", callback_data="buy_item_ff_100"),
        InlineKeyboardButton(f"310 جوهرة - {prices.get('ff_310', 3.0)}$", callback_data="buy_item_ff_310"),
        InlineKeyboardButton("🔙 رجوع", callback_data="buy_games")
    )
    await call.message.edit_text("🔥 **باقات Free Fire:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text=["top_services", "buy_smm", "digital_store", "my_orders", "search_service", "order_status"])
async def dummy_sections(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    await call.message.edit_text("⚙️ هذا القسم قيد التطوير.", reply_markup=kb)

@dp.callback_query_handler(text="recharge_balance")
async def recharge_balance_start(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await call.message.edit_text("💳 أرسل **كود الكارت** لشحن الرصيد:", reply_markup=keyboard, parse_mode="Markdown")
    await UserStates.waiting_for_coupon_code.set()

@dp.message_handler(state=UserStates.waiting_for_coupon_code)
async def process_coupon_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    db = load_db()
    user_id = str(message.from_user.id)
    
    if "coupons" in db and code in db["coupons"]:
        amount = db["coupons"][code]
        db["users"][user_id]["balance"] += float(amount)
        del db["coupons"][code]
        save_db(db)
        await message.answer(f"✅ تم شحن رصيدك بـ `{amount}$` بنجاح!", reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown")
        await state.finish()
    else:
        await message.answer("⚠️ الكود غير صالح:")

# ----------------------------------------------------
# 9. لوحة تحكم المشرفين المتكاملة وإدارة الدول والأسعار
# ----------------------------------------------------
@dp.callback_query_handler(text="admin_panel")
async def open_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    
    admin_keyboard = InlineKeyboardMarkup(row_width=2)
    admin_keyboard.add(
        InlineKeyboardButton("🚫 حذف دولة", callback_data="adm_del_country"),
        InlineKeyboardButton("↗️ إضافة دولة", callback_data="adm_add_country_custom")
    )
    admin_keyboard.add(
        InlineKeyboardButton("♨️ خصم رصيد", callback_data="adm_sub_balance"),
        InlineKeyboardButton("♻️ إضافة رصيد", callback_data="adm_add_balance")
    )
    admin_keyboard.add(
        InlineKeyboardButton("⚙️ إدارة السيرفرات والأسعار", callback_data="admin_servers_manager"),
        InlineKeyboardButton("👤 إحصائيات البوت 🌐", callback_data="adm_stats")
    )
    admin_keyboard.add(
        InlineKeyboardButton("👥 عدد المشتركين", callback_data="adm_users_count"),
        InlineKeyboardButton("✉️ إذاعة نشر", callback_data="adm_broadcast")
    )
    admin_keyboard.add(
        InlineKeyboardButton("⤵️ رفع وحذف API", callback_data="sms_section_menu"),
        InlineKeyboardButton("🎂 فحص رصيد الموقع", callback_data="check_sms_balance")
    )
    admin_keyboard.add(
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")
    )
    
    admin_text = f" اهلا وسهلا مطوري AMEN - BADR 🖤.\n\n هذه هي قائمة التحكم الخاصة بك في البوت 👤."
    
    try:
        await call.message.edit_text(admin_text, reply_markup=admin_keyboard, parse_mode="Markdown")
    except:
        await call.message.answer(admin_text, reply_markup=admin_keyboard, parse_mode="Markdown")

# إدارة السيرفرات والأسعار من لوحة التحكم
@dp.callback_query_handler(text="admin_servers_manager")
async def admin_servers_manager_handler(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    
    db = load_db()
    custom_prices = db.get("custom_prices", {"wa": 0.50, "tg": 0.50, "ig": 0.40})
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"🟢 واتساب (WA) - السعر: {custom_prices.get('wa', 0.50)}$", callback_data="edit_price_wa"),
        InlineKeyboardButton(f"🔵 تيليجرام (TG) - السعر: {custom_prices.get('tg', 0.50)}$", callback_data="edit_price_tg"),
        InlineKeyboardButton(f"🟣 انستقرام (IG) - السعر: {custom_prices.get('ig', 0.40)}$", callback_data="edit_price_ig")
    )
    keyboard.add(InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_panel"))
    
    await call.message.edit_text(
        "⚙️ **قسم إدارة السيرفرات والأسعار:**\n\n"
        "اختر السيرفر لتعديل سعر البيع للمستخدمين:",
        reply_markup=keyboard, parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('edit_price_'))
async def edit_service_price_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    serv_code = call.data.split('_')[2]
    
    async with state.proxy() as data:
        data['editing_serv_code'] = serv_code
        
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_servers_manager"))
    await call.message.edit_text(
        f"💰 **تعديل سعر السيرفر (`{serv_code.upper()}`):**\n\nأرسل السعر الجديد بالدولار (مثال: `0.50`):",
        reply_markup=kb, parse_mode="Markdown"
    )
    await AdminStates.waiting_for_coupon_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_coupon_amount)
async def save_new_service_price(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        new_price = float(message.text.strip())
        data = await state.get_data()
        serv_code = data.get('editing_serv_code')
        
        db = load_db()
        if "custom_prices" not in db: db["custom_prices"] = {}
        db["custom_prices"][serv_code] = new_price
        save_db(db)
        
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع لإدارة السيرفرات", callback_data="admin_servers_manager"))
        await message.answer(f"✅ **تم تحديث السعر بنجاح إلى:** `{new_price}$`", reply_markup=kb, parse_mode="Markdown")
        await state.finish()
    except Exception as e:
        await message.answer("⚠️ قيمة غير صالحة، أرسل رقماً صحيحاً للسعر (مثال: 0.50):")

# إدارة الدول (إضافة / حذف)
@dp.callback_query_handler(text="adm_add_country_custom")
async def adm_add_country_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    await state.finish()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await call.message.edit_text("🌍 **إضافة دولة جديدة:**\n\nأرسل **أيدي (ID) الدولة** في موقع SMSBower:", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_new_country_id.set()

@dp.message_handler(state=AdminStates.waiting_for_new_country_id)
async def adm_add_country_id_step(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    country_id = message.text.strip()
    async with state.proxy() as data:
        data['new_country_id'] = country_id
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await message.answer("📝 أرسل **اسم الدولة مع العلم** (مثال: `🇸🇦 السعودية`):", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_new_country_name.set()

@dp.message_handler(state=AdminStates.waiting_for_new_country_name)
async def adm_add_country_name_step(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    country_name = message.text.strip()
    data = await state.get_data()
    country_id = data.get('new_country_id')
    
    COUNTRY_NAMES[country_id] = country_name
    db = load_db()
    if "custom_countries" not in db: db["custom_countries"] = {}
    db["custom_countries"][country_id] = country_name
    save_db(db)
    
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لوحة المشرفين", callback_data="admin_panel"))
    await message.answer(f"✅ **تمت إضافة الدولة ({country_name}) بنجاح!**", reply_markup=kb, parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="adm_del_country")
async def adm_del_country_menu(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardMarkup(row_width=2)
    for c_id, c_name in COUNTRY_NAMES.items():
        kb.insert(InlineKeyboardButton(f"🗑️ {c_name}", callback_data=f"del_c_{c_id}"))
    kb.add(InlineKeyboardButton("🔙 رجوع لوحة التحكم", callback_data="admin_panel"))
    await call.message.edit_text("🗑️ **اختر الدولة المراد حذفها:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('del_c_'))
async def process_delete_country(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    c_id = call.data.split('_')[2]
    if c_id in COUNTRY_NAMES:
        removed_name = COUNTRY_NAMES.pop(c_id)
        db = load_db()
        if "custom_countries" in db and c_id in db["custom_countries"]:
            del db["custom_countries"][c_id]
            save_db(db)
        await call.answer(f"✅ تم حذف ({removed_name}) بنجاح!", show_alert=True)
        await adm_del_country_menu(call)

# إدارة الأرصدة عبر المشرفين
@dp.callback_query_handler(text="adm_add_balance")
async def adm_add_1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    await state.finish()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await call.message.edit_text("أرسل أيدي المستخدم المراد إضافة رصيد له:", reply_markup=kb)
    await AdminStates.waiting_for_add_id.set()

@dp.message_handler(state=AdminStates.waiting_for_add_id)
async def adm_add_2(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = message.text.strip()
        async with state.proxy() as data:
            data['target_id'] = target_id
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
        await message.answer("أرسل المبلغ المراد إضافته (بالدولار):", reply_markup=kb)
        await AdminStates.waiting_for_add_amount.set()
    except Exception as e:
        await message.answer(f"⚠️ خطأ: {e}")

@dp.message_handler(state=AdminStates.waiting_for_add_amount)
async def adm_add_3(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        target_id = data.get('target_id')
        db = load_db()
        if target_id not in db["users"]: db["users"][target_id] = {"balance": 0.0, "name": "User"}
        db["users"][target_id]["balance"] += amount
        save_db(db)
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لوحة المشرفين", callback_data="admin_panel"))
        await message.answer(f"✅ تمت إضافة `{amount}$` للمستخدم `{target_id}` بنجاح.", reply_markup=kb, parse_mode="Markdown")
        await state.finish()
    except:
        await message.answer("⚠️ أرسل رقماً صحيحاً للمبلغ:")

@dp.callback_query_handler(text="adm_sub_balance")
async def adm_sub_1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return
    await state.finish()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await call.message.edit_text("أرسل أيدي المستخدم المراد خصم رصيد منه:", reply_markup=kb)
    await AdminStates.waiting_for_sub_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_sub_amount)
async def adm_sub_2(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        target_id = message.text.strip()
        db = load_db()
        if target_id in db["users"]:
            current_bal = db["users"][target_id].get("balance", 0.0)
            db["users"][target_id]["balance"] = max(0.0, current_bal - 1.0)
            save_db(db)
            await message.answer(f"✅ تم خصم 1$ بنجاح للمستخدم `{target_id}`. الرصيد الجديد: `{db['users'][target_id]['balance']}$`")
        else:
            await message.answer("⚠️ المستخدم غير موجود.")
        await state.finish()
    except Exception as e:
        await message.answer(f"⚠️ حدث خطأ: {e}")

@dp.callback_query_handler(text="sms_section_menu")
async def sms_section_menu(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    status_display = f"`{api_key}`" if api_key else "❌ غير مُعين"
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ إضافة / تعديل المفتاح", callback_data="set_sms_api"),
        InlineKeyboardButton("🗑️ حذف المفتاح", callback_data="delete_sms_api")
    )
    keyboard.add(InlineKeyboardButton("💰 فحص رصيد الموقع عبر API", callback_data="check_sms_balance"))
    keyboard.add(InlineKeyboardButton("🔙 رجوع لوحة المشرفين", callback_data="admin_panel"))
    
    await call.message.edit_text(f"🌐 **إدارة SMSBower API**\n\nالمفتاح الحالي: {status_display}", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="set_sms_api")
async def set_sms_api_start(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="sms_section_menu"))
    await call.message.edit_text("🔑 أرسل مفتاح الـ API الجديد:", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_sms_api_key.set()

@dp.message_handler(state=AdminStates.waiting_for_sms_api_key)
async def save_sms_api_key(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    new_api_key = message.text.strip()
    db = load_db()
    if "settings" not in db: db["settings"] = {}
    db["settings"]["smsbower_api_key"] = new_api_key
    save_db(db)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="sms_section_menu"))
    await message.answer(f"✅ تم حفظ المفتاح بنجاح: `{new_api_key}`", reply_markup=kb, parse_mode="Markdown")
    await state.finish()

@dp.callback_query_handler(text="delete_sms_api")
async def delete_sms_api_key(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    db = load_db()
    if "settings" in db and "smsbower_api_key" in db["settings"]:
        db["settings"]["smsbower_api_key"] = None
        save_db(db)
    await call.answer("🗑️ تم حذف المفتاح بنجاح!", show_alert=True)
    await sms_section_menu(call)

@dp.callback_query_handler(text="check_sms_balance")
async def check_smsbower_balance(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    db = load_db()
    api_key = db.get("settings", {}).get("smsbower_api_key")
    if not api_key:
        await call.answer("⚠️ لم يتم تعيين مفتاح API بعد!", show_alert=True)
        return
    api_url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    try:
        response = requests.get(api_url, timeout=10)
        result_text = response.text.strip()
        if "ACCESS_BALANCE" in result_text or result_text.replace('.', '', 1).isdigit():
            balance_val = result_text.split(":")[-1] if ":" in result_text else result_text
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لوحة المشرفين", callback_data="admin_panel"))
            await call.message.edit_text(f"📊 **رصيد موقع SMSBower:**\n\n💰 `{balance_val}`", reply_markup=kb, parse_mode="Markdown")
        else:
            await call.answer(f"⚠️ رد غير متوقع: {result_text}", show_alert=True)
    except Exception as e:
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)

@dp.callback_query_handler(text=["adm_stats", "adm_users_count", "adm_broadcast"])
async def admin_dummy_actions(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    action_name = call.data
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع لوحة التحكم", callback_data="admin_panel"))
    if action_name == "adm_users_count":
        db = load_db()
        await call.message.edit_text(f"👥 إجمالي المشتركين: `{len(db.get('users', {}))}` مشترك.", reply_markup=kb, parse_mode="Markdown")
    elif action_name == "adm_stats":
        db = load_db()
        await call.message.edit_text(f"📊 الطلبات النشطة: `{len(db.get('active_orders', {}))}`", reply_markup=kb, parse_mode="Markdown")
    else:
        await call.message.edit_text("⚙️ هذا القسم مفعل وجاهز.", reply_markup=kb, parse_mode="Markdown")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
