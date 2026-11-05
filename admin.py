import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    init_db, get_user, update_user_language, save_user_credentials, 
    get_total_users_count, get_profit_margin, set_profit_margin,
    find_user_by_identifier, update_user_balance, log_user_activity, get_user_logs
)
from admin import show_admin_panel

TELEGRAM_BOT_TOKEN = "5418318795:AAHKA5Lh4cEdaZZAlTAd4ra7x-hfx80XHVs"
REQUIRED_CHANNEL = "@SIM_NUMBERS"       # قناة الاشتراك الإجباري
ORDERS_LOG_CHANNEL = "@SPEDERCH"    # قناة الطلبات العامة المشفرة
ADMIN_ID = 5396793642
FOXRELOAD_API_KEY = "dmk_SLDMDj7c85zyzMGiCN56JGFYsu0Dyc_cuFL9DWxcpEA"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class BotStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_target = State()
    waiting_for_new_margin = State()
    admin_get_user = State()
    admin_get_amount = State()

def mask_target_info(info: str) -> str:
    info = str(info).strip()
    if info.isdigit():
        if len(info) > 6:
            return info[:3] + "****" + info[-3:]
        return "***" + info[-2:] if len(info) > 2 else "****"
    else:
        if len(info) > 4:
            return info[:3] + "****" + info[-2:]
        return "@****"

async def send_order_to_foxreload(product_id: str):
    url = "https://public-api.foxreload.com/api/orders/"
    headers = {
        "X-API-Key": FOXRELOAD_API_KEY,
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"items": [{"itemId": product_id, "quantity": 1}]}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                res_data = await response.json()
                if response.status in [200, 201]:
                    return True, res_data
                return False, res_data
        except Exception as e:
            return False, str(e)

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if not await check_subscription(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 اشترك في القناة الرسمية", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")
        builder.button(text="🔄 تحقق من الاشتراك", callback_data="check_sub")
        builder.adjust(1)
        return await message.answer("⚠️ يجب عليك الاشتراك في قناة البوت أولاً!", reply_markup=builder.as_markup())
    await show_language_selection(message)

async def show_language_selection(message_or_callback):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇸🇦 العربية", callback_data="lang_ar")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    text = "اختر لغتك المفضلة / Choose your language:"
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    update_user_language(callback.from_user.id, lang)
    await show_main_menu(callback, lang)

async def show_main_menu(callback: types.CallbackQuery, lang: str):
    user = callback.from_user
    user_data = get_user(user.id)
    is_admin = user_data[3] if user_data else 0
    balance = user_data[4] if user_data else 0.0
    
    builder = InlineKeyboardBuilder()
    if lang == "ar":
        builder.button(text="⭐ خدمات تليجرام (نجوم واشتراكات)", callback_data="telegram_services")
        builder.button(text="📋 سجل عملهاتي وطلباتي", callback_data="my_orders_log")
        builder.button(text="📧 إدخال / تعديل بريدي", callback_data="set_email")
        builder.button(text="👤 عرض بياناتي ورصيدي", callback_data="my_email")
        if is_admin:
            builder.button(text="⚙️ لوحة تحكم الأدمن", callback_data="admin_panel")
        builder.button(text="🌐 تغيير اللغة", callback_data="change_lang")
        builder.adjust(1, 1, 1, 1, 1, 1)
        text = f"مرحباً بك، **{user.first_name}** 👋\n💰 رصيدك الحالي: `{balance}$`\nاختر الخدمة المطلوبة:"
    else:
        builder.button(text="⭐ Telegram Services", callback_data="telegram_services")
        builder.button(text="📋 My Orders History", callback_data="my_orders_log")
        builder.button(text="📧 Set / Update Email", callback_data="set_email")
        builder.button(text="👤 View My Info & Balance", callback_data="my_email")
        if is_admin:
            builder.button(text="⚙️ Admin Panel", callback_data="admin_panel")
        builder.button(text="🌐 Change Language", callback_data="change_lang")
        builder.adjust(1, 1, 1, 1, 1, 1)
        text = f"Welcome, **{user.first_name}** 👋\n💰 Balance: `{balance}$`\nChoose a service:"
        
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await show_language_selection(callback)
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

# --- عرض سجل العمليات والطلبات الخاصة بالمستخدم ---
@dp.callback_query(F.data == "my_orders_log")
async def show_user_activity_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logs = get_user_logs(user_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    if not logs:
        return await callback.message.edit_text(
            "📋 **سجل عملياتك وطلباتك:**\n\nعذراً، ليس لديك أي عمليات شحن سابقة حتى الآن.",
            reply_markup=builder.as_markup(), parse_mode="Markdown"
        )
    
    log_text = "📋 **آخر عمليات الشحن والطلبات الخاصة بك:**\n\n"
    for idx, (service, target, cost, created_at) in enumerate(logs, 1):
        log_text += (
            f"*{idx}. الخدمة:* {service}\n"
            f"👤 *المستهدف:* `{target}`\n"
            f"💵 *التكلفة:* `{cost}$`\n"
            f"🕒 *الوقت والتاريخ:* `{created_at}`\n"
            "-----------------------------------\n"
        )
        
    await callback.message.edit_text(log_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- لوحة الأدمن ---
@dp.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("عذراً، للمشرفين فقط.", show_alert=True)
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_refresh")
async def process_admin_refresh(callback: types.CallbackQuery):
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_edit_margin")
async def process_edit_margin(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(BotStates.waiting_for_new_margin)
    current = get_profit_margin()
    await callback.message.answer(f"📈 هامش الربح الحالي: `{current}%`\nأدخل النسبة الجديدة:", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_new_margin)
async def save_new_margin(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        new_margin = float(message.text.strip())
        set_profit_margin(new_margin)
        await state.clear()
        await message.answer(f"✅ تم تحديث هامش الربح ليصبح: `{new_margin}%`", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً أو عشرياً:")

@dp.callback_query(F.data == "admin_manage_balance")
async def admin_manage_balance_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ إضافة رصيد لمستخدم", callback_data="bal_op_add")
    builder.button(text="➖ خصم رصيد من مستخدم", callback_data="bal_op_sub")
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    await callback.message.edit_text("💵 **إدارة أرصدة العملاء:**\nاختر العملية المطلوبة:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bal_op_"))
async def admin_ask_user(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    op = callback.data.split("_")[2]
    await state.update_data(balance_op=op)
    await state.set_state(BotStates.admin_get_user)
    op_text = "إضافة رصيد إلى" if op == "add" else "خصم رصيد من"
    await callback.message.answer(f"👤 **{op_text} عميل:**\nأدخل معرف المستخدم (User ID) أو الإيميل:", parse_mode="Markdown")

@dp.message(BotStates.admin_get_user)
async def admin_receive_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    user = find_user_by_identifier(message.text.strip())
    if not user:
        return await message.answer("❌ لم يتم العثور على المستخدم. حاول مجدداً:")
    await state.update_data(target_user_id=user[0])
    await state.set_state(BotStates.admin_get_amount)
    await message.answer(f"✅ المستخدم: `{user[1]}` (الرصيد: `{user[2]}$`)\nأدخل المبلغ المراد:", parse_mode="Markdown")

@dp.message(BotStates.admin_get_amount)
async def admin_receive_amount(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        update_user_balance(data.get("target_user_id"), amount, data.get("balance_op"))
        await state.clear()
        await message.answer("✅ تم تحديث رصيد المستخدم بنجاح!", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً للمبلغ:")

# --- خدمات تليجرام وحفظ السجل للأعضاء ---
@dp.callback_query(F.data == "telegram_services")
async def process_telegram_services(callback: types.CallbackQuery):
    margin = get_profit_margin()
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ شحن نجوم تليجرام (Stars)", callback_data="service_stars_ID")
    builder.button(text="💎 اشتراك تليجرام مميز (Premium)", callback_data="service_premium_ID")
    builder.button(text="🔙 العودة", callback_data="back_to_menu")
    builder.adjust(1)
    await callback.message.edit_text(f"⭐ **اختر خدمة تليجرام:**\n(هامش الربح المفعل: `{margin}%`)", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("service_"))
async def ask_for_target_id(callback: types.CallbackQuery, state: FSMContext):
    service_type = callback.data.split("_")[1]
    product_id = "YOUR_STARS_PRODUCT_ID" if service_type == "stars" else "YOUR_PREMIUM_PRODUCT_ID"
    service_name = "⭐ نجوم تليجرام (Stars)" if service_type == "stars" else "💎 اشتراك تليجرام Premium"
    
    await state.update_data(product_id=product_id, service_name=service_name)
    await state.set_state(BotStates.waiting_for_target)
    await callback.message.answer("📥 أدخل معرف المستخدم (User ID) أو اليوزر المراد الشحن له:")

@dp.message(BotStates.waiting_for_target)
async def process_target_id(message: types.Message, state: FSMContext):
    target_info = message.text.strip()
    data = await state.get_data()
    service_name = data.get("service_name", "خدمة تليجرام")
    
    await message.answer("⏳ جاري إرسال الطلب وتنفيذه...")
    success, result = await send_order_to_foxreload(data.get("product_id"))
    
    if success:
        order_cost = 1.0  # التكلفة الافتراضية للطلب
        
        # 1. حفظ العملية في سجل المستخدم الشخصي مع الوقت والتاريخ
        log_user_activity(message.from_user.id, service_name, target_info, order_cost)
        
        # 2. إرسال الشعار المشفر إلى قناة الطلبات العامة
        masked_target = mask_target_info(target_info)
        try:
            log_text = (
                f"🚀 **عملية شحن ناجحة جديدة!**\n\n"
                f"📦 الخدمة: `{service_name}`\n"
                f"👤 المستهدف: `{masked_target}` (مشفر للخصوصية)\n"
                f"🟢 الحالة: `مكتمل بنجاح ✅`"
            )
            await bot.send_message(chat_id=ORDERS_LOG_CHANNEL, text=log_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send log to orders channel: {e}")
        
        await message.answer(f"✅ **تم تنفيذ الطلب بنجاح!**\n👤 المستهدف: `{target_info}`", parse_mode="Markdown")
    else:
        await message.answer("❌ فشل تنفيذ الطلب عبر الـ API.")
    await state.clear()

# --- إدخال الإيميل للمستخدم ---
@dp.callback_query(F.data == "set_email")
async def start_entering_email(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_email)
    await callback.message.answer("📧 أدخل بريدك الإلكتروني (يجب أن ينتهي بـ `@gmail.com`):")

@dp.message(BotStates.waiting_for_email)
async def process_user_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not email.endswith("@gmail.com"):
        return await message.answer("❌ يجب أن ينتهي بـ `@gmail.com`. حاول مجدداً:")
    await state.update_data(email=email)
    await state.set_state(BotStates.waiting_for_password)
    await message.answer("🔑 أدخل كلمة المرور الخاصة بريدك:")

@dp.message(BotStates.waiting_for_password)
async def process_user_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    save_user_credentials(message.from_user.id, message.from_user.username or "No", data.get("email"), password)
    await state.clear()
    await message.answer("✅ تم حفظ بيانات بريدك بنجاح!")

@dp.callback_query(F.data == "my_email")
async def process_my_email(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    if not user_data or not user_data[0]:
        return await callback.answer("⚠️ لم تقم بإدخال بريدك بعد!", show_alert=True)
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    await callback.message.edit_text(
        f"📧 البريد: `{user_data[0]}`\n🔑 كلمة المرور: `{user_data[1]}`\n💰 رصيدك: `{user_data[4]}$`", 
        reply_markup=builder.as_markup(), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_menu")
async def process_back_menu(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    await show_main_menu(callback, user_data[2] if user_data else "ar")

@dp.callback_query(F.data == "change_lang")
async def process_change_lang(callback: types.CallbackQuery):
    await show_language_selection(callback)

async def main():
    init_db()
    logging.info("Bot started with user activity log history feature.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
