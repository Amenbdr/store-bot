import os
import random
import logging
import threading
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
# 2. إعدادات البوت
# ----------------------------------------------------
API_TOKEN = "5418318795:AAE_s0NJw9IE1JWg6x9JuWQpl0MHDjcFCf8"
ADMIN_IDS = [5396793642]
REQUIRED_CHANNEL = "@SIM_NUMBERS"

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_coupon_code = State()
    waiting_for_target_input = State()
    waiting_for_reg_email = State()
    waiting_for_reg_otp = State()
    waiting_for_reg_password = State()
    waiting_for_login_email = State()
    waiting_for_login_password = State()

class AdminStates(StatesGroup):
    waiting_for_add_id = State()
    waiting_for_add_amount = State()
    waiting_for_coupon_code = State()
    waiting_for_coupon_amount = State()
    waiting_for_country_name = State()
    waiting_for_country_price = State()
    waiting_for_country_stock = State()

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
        InlineKeyboardButton("👤 حسابي وتسجيل الدخول", callback_data="my_account"),
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
# 3. الأوامر والتحقق
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
                    InlineKeyboardButton(f"📢 قناة البوت", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"),
                    InlineKeyboardButton("✅ تحقق من الانضمام", callback_data="check_subscription")
                )
                await message.answer(
                    "❌ **عذراً عزيزي!**\n\nيجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه والبدء في العمل.\n\nيرجى الاشتراك ثم الضغط على زر (تحقق من الانضمام) بالأسفل 👇",
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
        await message.answer_photo(photo=photo, caption="♻️ - **يرجى كتابة الرقم الموجود في الصورة أعلاه وإرساله إلينا للتحقق من أنك لست روبوتاً.**", reply_markup=kb, parse_mode="Markdown")
        await UserStates.waiting_for_captcha.set()
        return

    if str_user_id not in db["users"]:
        db["users"][str_user_id] = {"balance": 0.0, "name": user_name, "email": None}
        save_db(db)
        
    balance = db["users"][str_user_id].get("balance", 0.0)
    email = db["users"][str_user_id].get("email", "غير مسجل")
    
    welcome_text = (
        f"🌸 **متجر الخدمات الرقمية والألعاب**\n\n"
        f"أهلاً بك يا **{user_name}** 🌟\n"
        f"📧 الإيميل: `{email}`\n"
        f"💰 رصيدك الحالي: `{balance:.2f}` دولار أمريكي.\n\n"
        f"👇 اختر القسم الذي تريده من الأزرار أدناه:"
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
        if str(user_id) not in db["users"]:
            db["users"][str(user_id)] = {"balance": 0.0, "name": message.from_user.first_name, "email": None}
        save_db(db)
        await message.answer("✅ **تم التحقق بنجاح!**", parse_mode="Markdown")
        await state.finish()
        await send_welcome(message, state)
    else:
        await message.answer("❌ **الرمز غير صحيح!** أعد كتابة الأرقام الظاهرة في الصورة:")

# ----------------------------------------------------
# 4. إدارة الحسابات وتسجيل الدخول عبر الإيميل و OTP
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
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="register_email")
async def reg_email_start(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await call.message.edit_text("📝 **تسجيل حساب جديد**\n\nالرجاء إرسال **البريد الإلكتروني** الخاص بك لتلقي كود التحقق:", reply_markup=kb, parse_mode="Markdown")
    await UserStates.waiting_for_reg_email.set()

@dp.message_handler(state=UserStates.waiting_for_reg_email)
async def reg_email_step(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("⚠️ البريد غير صالح. أرسل إيميل صحيح:")
        return
        
    db = load_db()
    for uid, udata in db["users"].items():
        if udata.get("email") == email:
            await message.answer("⚠️ هذا البريد مسجل مسبقاً لحساب آخر. أرسل إيميل مختلف أو اضغط إلغاء:")
            return
            
    otp_code = str(random.randint(1000, 9999))
    user_id = str(message.from_user.id)
    temp_auth_data[user_id] = {"email": email, "otp": otp_code}
    
    logging.info(f"OTP Code for {email}: {otp_code}")
    
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await message.answer(
        f"✉️ **تم إرسال كود التحقق إلى بريدك الإلكتروني!**\n\n"
        f"(لغرض التجربة الكود هو: `{otp_code}`)\n\n"
        f"الرجاء كتابة **كود التحقق (OTP)** المكون من 4 أرقام هنا:",
        reply_markup=kb, parse_mode="Markdown"
    )
    await UserStates.waiting_for_reg_otp.set()

@dp.message_handler(state=UserStates.waiting_for_reg_otp)
async def reg_otp_step(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    entered_otp = message.text.strip()
    
    saved_data = temp_auth_data.get(user_id)
    if not saved_data or entered_otp != saved_data.get("otp"):
        await message.answer("⚠️ **كود التحقق غير صحيح!** أرسل الكود الصحيح:")
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
    
    await message.answer(
        f"🎉 **تم إنشاء حسابك بنجاح!**\n\n📧 الإيميل: `{email}`\n💰 رصيدك: `{db['users'][user_id]['balance']}$`",
        reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown"
    )
    await state.finish()

@dp.callback_query_handler(text="login_email")
async def login_email_start(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await call.message.edit_text("🔑 **تسجيل الدخول**\n\nأرسل **البريد الإلكتروني** المسجل به:", reply_markup=kb, parse_mode="Markdown")
    await UserStates.waiting_for_login_email.set()

@dp.message_handler(state=UserStates.waiting_for_login_email)
async def login_email_step(message: types.Message, state: FSMContext):
    temp_auth_data[str(message.from_user.id)] = {"login_email": message.text.strip()}
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
        if udata.get("email") == email and udata.get("password") == password:
            found = True
            db["users"][user_id]["balance"] = udata.get("balance", 0.0)
            db["users"][user_id]["email"] = email
            db["users"][user_id]["password"] = password
            save_db(db)
            break
            
    if found:
        await message.answer(
            f"✅ **تم تسجيل الدخول بنجاح!**\n\n📧 الإيميل: `{email}`\n💰 رصيدك: `{db['users'][user_id]['balance']}$`",
            reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ البريد الإلكتروني أو كلمة المرور غير صحيحة!", reply_markup=get_main_menu(int(user_id)))
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
    await my_account_handler(call)

@dp.callback_query_handler(text="back_to_main")
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    db = load_db()
    balance = db["users"].get(str(user_id), {}).get("balance", 0.0)
    await call.message.edit_text(f"🌸 **القائمة الرئيسية**\n\n💰 رصيدك الحالي: `{balance:.2f}` دولار أمريكي.", reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.callback_query_handler(text="cancel_process", state="*")
async def cancel_process_callback(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    db = load_db()
    balance = db["users"].get(str(user_id), {}).get("balance", 0.0)
    await call.message.edit_text(f"❌ **تم إلغاء العملية.**\n\n💰 رصيدك: `{balance:.2f}$`", reply_markup=get_main_menu(user_id), parse_mode="Markdown")

# ----------------------------------------------------
# 5. الألعاب والأرقام والأقسام الأخرى
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

@dp.callback_query_handler(text="buy_sim")
async def buy_sim_menu(call: types.CallbackQuery):
    db = load_db()
    countries = db.get("countries", {})
    keyboard = InlineKeyboardMarkup(row_width=1)
    if countries:
        for c_name, info in countries.items():
            stock = info.get("stock", 0)
            price = info.get("price", 0.0)
            if stock > 0:
                keyboard.add(InlineKeyboardButton(f"{c_name} | السعر: {price}$ | المخزون: {stock}", callback_data=f"buy_country_{c_name}"))
            else:
                keyboard.add(InlineKeyboardButton(f"{c_name} ❌ (نفذ المخزون)", callback_data="out_of_stock"))
    keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    await call.message.edit_text("📞 **قسم الأرقام الوهمية:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="out_of_stock")
async def out_of_stock_alert(call: types.CallbackQuery):
    await call.answer("عذراً، نفذ مخزون هذه الدولة!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('buy_country_') or c.data.startswith('buy_item_'))
async def process_buy_item(call: types.CallbackQuery, state: FSMContext):
    action = call.data.replace('buy_country_', '').replace('buy_item_', '')
    db = load_db()
    
    if action in db.get("countries", {}):
        price = db["countries"][action]["price"]
        item_name = f"رقم {action}"
        admin_temp_data[str(call.from_user.id)] = {"item": item_name, "price": price, "country": action}
    else:
        prices = db.get("prices", DEFAULT_PRICES)
        price = prices.get(action, 1.0)
        names = {"pubg_60": "60 شدة PUBG", "pubg_325": "325 شدة PUBG", "ff_100": "100 جوهرة FF", "ff_310": "310 جوهرة FF"}
        item_name = names.get(action, "خدمة")
        admin_temp_data[str(call.from_user.id)] = {"item": item_name, "price": price}
        
    user_id = str(call.from_user.id)
    if db["users"].get(user_id, {}).get("balance", 0.0) < price:
        await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)
        return
        
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process"))
    await call.message.edit_text(f"طلب: **{item_name}**\n💵 السعر: `{price}$`\n\nأرسل **البيانات المطلوبة (رقم أو أيدي)**:", reply_markup=keyboard, parse_mode="Markdown")
    await UserStates.waiting_for_target_input.set()

@dp.message_handler(state=UserStates.waiting_for_target_input)
async def confirm_order(message: types.Message, state: FSMContext):
    target_info = message.text.strip()
    user_id = str(message.from_user.id)
    order_info = admin_temp_data.get(user_id)
    
    if not order_info:
        await state.finish()
        await message.answer("حدث خطأ.", reply_markup=get_main_menu(int(user_id)))
        return
        
    price = order_info["price"]
    country_name = order_info.get("country")
    db = load_db()
    
    if country_name and db["countries"][country_name]["stock"] > 0:
        db["countries"][country_name]["stock"] -= 1
    elif country_name:
        await message.answer("❌ نفذ المخزون!")
        await state.finish()
        return
        
    db["users"][user_id]["balance"] -= price
    save_db(db)
    
    await message.answer(f"✅ **تم الطلب بنجاح!**\n💰 رصيدك المتبقي: `{db['users'][user_id]['balance']}$`", reply_markup=get_main_menu(int(user_id)), parse_mode="Markdown")
    await state.finish()

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
# 6. لوحة المشرفين
# ----------------------------------------------------
@dp.callback_query_handler(text="admin_panel")
async def open_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("➕ إضافة رصيد", callback_data="adm_add_balance"),
        InlineKeyboardButton("🎟️ إنشاء كارت شحن", callback_data="adm_create_coupon"),
        InlineKeyboardButton("🌍 إضافة دولة ومخزون", callback_data="adm_add_country"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")
    )
    await call.message.edit_text("⚙️ **لوحة التحكم:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="adm_add_country")
async def adm_country_1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("أرسل اسم الدولة (مثال: `🇫🇷 فرنسا`):", reply_markup=None)
    await AdminStates.waiting_for_country_name.set()

@dp.message_handler(state=AdminStates.waiting_for_country_name)
async def adm_country_2(message: types.Message, state: FSMContext):
    admin_temp_data['new_country_name'] = message.text.strip()
    await message.answer("أرسل السعر بالدولار:")
    await AdminStates.waiting_for_country_price.set()

@dp.message_handler(state=AdminStates.waiting_for_country_price)
async def adm_country_3(message: types.Message, state: FSMContext):
    admin_temp_data['new_country_price'] = float(message.text.strip())
    await message.answer("أرسل المخزون:")
    await AdminStates.waiting_for_country_stock.set()

@dp.message_handler(state=AdminStates.waiting_for_country_stock)
async def adm_country_4(message: types.Message, state: FSMContext):
    stock = int(message.text.strip())
    c_name = admin_temp_data.get('new_country_name')
    price = admin_temp_data.get('new_country_price')
    db = load_db()
    db["countries"][c_name] = {"price": price, "stock": stock}
    save_db(db)
    await message.answer(f"✅ تمت إضافة الدولة `{c_name}` بنجاح.")
    await state.finish()

@dp.callback_query_handler(text="adm_add_balance")
async def adm_add_1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("أرسل أيدي المستخدم:", reply_markup=None)
    await AdminStates.waiting_for_add_id.set()

@dp.message_handler(state=AdminStates.waiting_for_add_id)
async def adm_add_2(message: types.Message, state: FSMContext):
    admin_temp_data['target_id'] = int(message.text.strip())
    await message.answer("أرسل المبلغ:")
    await AdminStates.waiting_for_add_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_add_amount)
async def adm_add_3(message: types.Message, state: FSMContext):
    amount = float(message.text.strip())
    target_id = str(admin_temp_data.get('target_id'))
    db = load_db()
    if target_id not in db["users"]: db["users"][target_id] = {"balance": 0.0, "name": "User"}
    db["users"][target_id]["balance"] += amount
    save_db(db)
    await message.answer(f"✅ تمت الإضافة بنجاح.")
    await state.finish()

@dp.callback_query_handler(text="adm_create_coupon")
async def adm_coupon_1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("أرسل كود الكارت:", reply_markup=None)
    await AdminStates.waiting_for_coupon_code.set()

@dp.message_handler(state=AdminStates.waiting_for_coupon_code)
async def adm_coupon_2(message: types.Message, state: FSMContext):
    admin_temp_data['coupon_code'] = message.text.strip()
    await message.answer("أرسل القيمة بالدولار:")
    await AdminStates.waiting_for_coupon_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_coupon_amount)
async def adm_coupon_3(message: types.Message, state: FSMContext):
    amount = float(message.text.strip())
    code = admin_temp_data.get('coupon_code')
    db = load_db()
    db["coupons"][code] = amount
    save_db(db)
    await message.answer(f"✅ تم إنشاء الكود `{code}` بنجاح.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
