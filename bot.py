import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# استيراد الملفات البرمجية للمشروع
from database import Database
from user_numbers import get_countries_pagination_keyboard, get_fake_servers_keyboard

# توكن البوت (يمكنك استبداله بالتوكن الخاص بك أو وضعه كمتغير بيئي)
API_TOKEN = "5418318795:AAHWxQB3X43nun5UkUOzzaZoL89lpPHvmp8"

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# قائمة أيدي المشرفين (ضع الآيدي الخاص بك هنا)
ADMIN_IDS = [5396793642]  # استبدل هذا بالآيدي الخاص بك

# تهيئة قاعدة البيانات عند بدء التشغيل
Database.init_db()

# ==================== تعريف الحالات (FSM) ====================
class TransferStates(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_amount = State()

class AdminAPIState(StatesGroup):
    waiting_for_api_key = State()


# ==================== القائمة الرئيسية ====================
async def get_main_menu_keyboard(is_admin: bool = False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    # السطر الأول
    keyboard.add(
        types.InlineKeyboardButton("🟢 حسابات واتساب", callback_data="srv_wa"),
        types.InlineKeyboardButton("🔵 حسابات تليجرام", callback_data="srv_tg")
    )
    # السطر الثاني
    keyboard.add(
        types.InlineKeyboardButton("🚀 قسم الرشق", callback_data="section_boost"),
        types.InlineKeyboardButton("🎮 قسم الألعاب", callback_data="menu_games")
    )
    # السطر الثالث
    keyboard.add(
        types.InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="user_settings"),
        types.InlineKeyboardButton("📞 الدعم الفني", callback_data="support_ticket")
    )
    # زر المشرف
    if is_admin:
        keyboard.add(types.InlineKeyboardButton("👑 لوحة التحكم (الإدارة)", callback_data="admin_panel"))
    return keyboard


# ==================== معالجة أمر /start ====================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = Database.get_or_create_user(user_id)
    
    if user_data[2] == 1:  # التحقق من الحظر
        await message.answer("❌ عذراً، حسابك محظور من استخدام البوت.")
        return
        
    is_admin = message.from_user.id in ADMIN_IDS
    keyboard = await get_main_menu_keyboard(is_admin)
    
    await message.answer(
        f"مرحباً بك يا غالي في بوت الخدمات الرقمية والتفعيل الأقوى! 🖤\n"
        f"رصيدك الحالي: `{user_data[1]:.2f} $`\n\n"
        f"اختر ما يناسبك من القائمة أدناه:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ==================== تصفح الأرقام والدول ====================
@dp.callback_query_handler(lambda c: c.data in ["srv_wa", "srv_tg"])
async def process_service_selection(query: types.CallbackQuery):
    service_type = "wa" if query.data == "srv_wa" else "tg"
    keyboard, text = await get_countries_pagination_keyboard(service_type, page=1)
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("p_"))
async def process_pagination(query: types.CallbackQuery):
    parts = query.data.split("_")
    service_type = parts[1]
    page = int(parts[2])
    keyboard, text = await get_countries_pagination_keyboard(service_type, page=page)
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("cnt_"))
async def process_country_selection(query: types.CallbackQuery):
    parts = query.data.split("_")
    service_type = parts[1]
    country_id = int(parts[2])
    
    service_code = "whatsapp" if service_type == "wa" else "telegram"
    service_name = "واتساب" if service_type == "wa" else "تليجرام"
    
    keyboard = await get_fake_servers_keyboard(service_code, country_id, service_name)
    await query.message.edit_text(f"🖥 **اختر السيرفر المناسب لدولة #{country_id}:**", reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("back_cnt_"))
async def back_to_countries(query: types.CallbackQuery):
    service_code = query.data.split("_")[2]
    service_type = "wa" if service_code == "whatsapp" else "tg"
    keyboard, text = await get_countries_pagination_keyboard(service_type, page=1)
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()


# ==================== الأقسام الإضافية والإعدادات ====================
@dp.callback_query_handler(lambda c: c.data == "section_boost")
async def process_boost_section(query: types.CallbackQuery):
    await query.answer("🚀 قسم الرشق والمتابعين.. تتوفر قريباً جداً في التحديث القادم!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "menu_games")
async def process_games_section(query: types.CallbackQuery):
    await query.answer("🎮 قسم شحن الألعاب قيد التطوير وسيتم إطلاقه قريباً!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "support_ticket")
async def process_support(query: types.CallbackQuery):
    await query.answer("📞 للتواصل مع الدعم الفني، يرجى مراسلة المشرف مباشرة.", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "user_settings")
async def process_user_settings(query: types.CallbackQuery):
    settings_keyboard = types.InlineKeyboardMarkup(row_width=1)
    settings_keyboard.add(
        types.InlineKeyboardButton("🔑 تغيير كلمة المرور", callback_data="set_change_password"),
        types.InlineKeyboardButton("🔄 تحويل الحساب / الرصيد", callback_data="set_transfer_account"),
        types.InlineKeyboardButton("🚪 تسجيل الخروج", callback_data="set_logout"),
        types.InlineKeyboardButton("🗑 حذف الحساب نهائياً", callback_data="set_delete_account"),
        types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_home")
    )
    text = "⚙️ **إعدادات الحساب الشخصية:**\n\nاختر الإجراء المناسب لإدارته:"
    await query.message.edit_text(text, reply_markup=settings_keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "back_home")
async def back_home(query: types.CallbackQuery):
    is_admin = query.from_user.id in ADMIN_IDS
    keyboard = await get_main_menu_keyboard(is_admin)
    await query.message.edit_text("🏠 **القائمة الرئيسية:**", reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "ignore")
async def ignore_callback(query: types.CallbackQuery):
    await query.answer()


# ==================== نظام تحويل الأرصدة ====================
@dp.callback_query_handler(lambda c: c.data == "set_transfer_account")
async def start_transfer_process(query: types.CallbackQuery):
    text = (
        "🔄 **تحويل الرصيد إلى مستخدم آخر:**\n\n"
        "الرجاء إرسال **آيدي (ID)** المستخدم أو **البريد الإلكتروني (Email)** المراد التحويل إليه:"
    )
    keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ إلغاء", callback_data="user_settings"))
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await TransferStates.waiting_for_recipient.set()
    await query.answer()

@dp.message_handler(state=TransferStates.waiting_for_recipient)
async def process_transfer_recipient(message: types.Message, state: FSMContext):
    recipient_input = message.text.strip()
    await state.update_data(recipient=recipient_input)
    await message.answer("💵 مميز! الآن أرسل **المبلغ** المراد تحويله (بالدولار، مثال: `5`):", parse_mode="Markdown")
    await TransferStates.waiting_for_amount.set()

@dp.message_handler(state=TransferStates.waiting_for_amount)
async def process_transfer_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إرسال رقم صحيح للمبلغ (مثال: `2` أو `10`):", parse_mode="Markdown")
        return
        
    data = await state.get_data()
    recipient = data.get("recipient")
    sender_id = str(message.from_user.id)
    
    success, result_message = Database.transfer_balance_by_identifier(sender_id, recipient, amount)
    await message.answer(result_message, parse_mode="Markdown")
    await state.finish()
    
    is_admin = message.from_user.id in ADMIN_IDS
    keyboard = await get_main_menu_keyboard(is_admin)
    await message.answer("ماذا ترغب أن تفعل أيضاً؟", reply_markup=keyboard)


# ==================== لوحة تحكم المشرف وإدارة الـ API ====================
@dp.callback_query_handler(lambda c: c.data == "admin_panel" and c.from_user.id in ADMIN_IDS)
async def admin_panel_handler(query: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔑 إعداد وتغيير مفتاح API الموقع", callback_data="admin_set_api"),
        types.InlineKeyboardButton("📊 تقارير الأرصدة والمستخدمين", callback_data="admin_balances"),
        types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_home")
    )
    await query.message.edit_text("⚙️ **لوحة التحكم الإدارية:**\nاختر القسم المطلوب للإدارة:", reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_set_api" and c.from_user.id in ADMIN_IDS)
async def ask_for_api_key(query: types.CallbackQuery):
    current_key = Database.get_setting("smsbower_api_key", "غير مسجل")
    text = (
        f"🔑 **إدارة مفتاح ربط الموقع (API Key):**\n\n"
        f"المفتاح الحالي: `{current_key}`\n\n"
        f"الرجاء إرسال مفتاح الـ API الجديد لموقع (SMSBower):"
    )
    keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 عودة لوحة التحكم", callback_data="admin_panel"))
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await AdminAPIState.waiting_for_api_key.set()
    await query.answer()

@dp.message_handler(state=AdminAPIState.waiting_for_api_key)
async def save_new_api_key(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    new_key = message.text.strip()
    Database.set_setting("smsbower_api_key", new_key)
    
    await message.answer(f"✅ **تم تحديث وحفظ مفتاح الـ API بنجاح!**\nالمفتاح الجديد: `{new_key}`", parse_mode="Markdown")
    await state.finish()
    
    is_admin = message.from_user.id in ADMIN_IDS
    keyboard = await get_main_menu_keyboard(is_admin)
    await message.answer("اختر الخطوة التالية:", reply_markup=keyboard)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
