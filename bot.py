import asyncio
import logging
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# استيراد الملفات المنظمة
from database import init_db, get_user, update_user_language, save_user_if_not_exists, get_total_users_count
from admin import show_admin_panel

TELEGRAM_BOT_TOKEN = "5418318795:AAHKA5Lh4cEdaZZAlTAd4ra7x-hfx80XHVs"  # ضع توكن بوتك هنا
REQUIRED_CHANNEL = "@SIM_NUMBERS"       # معرف قناتك الإجبارية
ADMIN_ID = 5396793642                            # ضع الآيدي الخاص بك كأدمن

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class OrderState(StatesGroup):
    waiting_for_target = State()

# التحقق من الاشتراك الإجباري
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    # توليد وحفظ الإيميل وكلمة المرور للعميل تلقائياً في قاعدة البيانات
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"user_{user_id}_{random_str}@foxmail.com"
    password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=12))
    
    is_admin_flag = 1 if user_id == ADMIN_ID else 0
    save_user_if_not_exists(user_id, username, email, password, is_admin_flag)
    
    if not await check_subscription(user_id):
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 اشترك في القناة الرسمية", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")
        builder.button(text="🔄 تحقق من الاشتراك", callback_data="check_sub")
        builder.adjust(1)
        return await message.answer(
            "⚠️ **عذراً، يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه!**\n\n"
            f"📌 القناة: {REQUIRED_CHANNEL}\n👇 بعد الانضمام اضغط زر التحقق:",
            reply_markup=builder.as_markup(), parse_mode="Markdown"
        )
    
    await show_language_selection(message)

async def show_language_selection(message_or_callback):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇸🇦 العربية", callback_data="lang_ar")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    
    text = "مرحباً بك! يرجى اختيار لغتك المفضلة:\nWelcome! Choose your language:"
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
    
    builder = InlineKeyboardBuilder()
    if lang == "ar":
        builder.button(text="⭐ خدمات تليجرام (نجوم واشتراكات)", callback_data="telegram_services")
        builder.button(text="📧 إيميلي الخاص وكلمة المرور", callback_data="my_email")
        if is_admin:
            builder.button(text="⚙️ لوحة تحكم الأدمن", callback_data="admin_panel")
        builder.button(text="🌐 تغيير اللغة", callback_data="change_lang")
        builder.adjust(1, 1, 1, 1)
        text = f"مرحباً بك، **{user.first_name}** 👋\nاختر الخدمة المطلوبة من القائمة:"
    else:
        builder.button(text="⭐ Telegram Services (Stars & Premium)", callback_data="telegram_services")
        builder.button(text="📧 My Email & Password", callback_data="my_email")
        if is_admin:
            builder.button(text="⚙️ Admin Panel", callback_data="admin_panel")
        builder.button(text="🌐 Change Language", callback_data="change_lang")
        builder.adjust(1, 1, 1, 1)
        text = f"Welcome, **{user.first_name}** 👋\nChoose a service from below:"
        
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await show_language_selection(callback)
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("عذراً، هذا القسم مخصص للمشرف فقط.", show_alert=True)
    total_users = get_total_users_count()
    await show_admin_panel(callback, total_users)

@dp.callback_query(F.data == "admin_refresh")
async def process_admin_refresh(callback: types.CallbackQuery):
    total_users = get_total_users_count()
    await show_admin_panel(callback, total_users)

@dp.callback_query(F.data == "my_email")
async def process_my_email(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    email, password, lang = user_data[0], user_data[1], user_data[2]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    if lang == "ar":
        text = f"🔐 **بيانات بريدك الإلكتروني الخاص:**\n\n📧 البريد: `{email}`\n🔑 كلمة المرور: `{password}`"
    else:
        text = f"🔐 **Your Email Credentials:**\n\n📧 Email: `{email}`\n🔑 Password: `{password}`"
        
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_menu")
async def process_back_menu(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    await show_main_menu(callback, user_data[2] if user_data else "ar")

@dp.callback_query(F.data == "change_lang")
async def process_change_lang(callback: types.CallbackQuery):
    await show_language_selection(callback)

async def main():
    init_db()
    logging.info("Clean Structured Bot & Admin Panel started successfully.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
