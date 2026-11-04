from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
from database import db
from utils.keyboards import admin_main_keyboard

class AdminStates(StatesGroup):
    waiting_for_add_id = State()
    waiting_for_add_amount = State()
    waiting_for_deduct_id = State()
    waiting_for_deduct_amount = State()
    waiting_for_broadcast = State()
    waiting_for_margin_value = State()

# --- 1. فتح اللوحة الرئيسية للأدمن ---
async def admin_dashboard(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("⛔ لا تملك صلاحية الوصول!", show_alert=True)
        
    total_users = db.get_all_users_count()
    servers = db.get_custom_servers()
    text = (
        f"👑 **لوحة تحكم الإدارة**\n\n"
        f"👥 إجمالي العملاء: `{total_users}`\n"
        f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
        f"اختر الإجراء المطلوب من الأزرار أدناه:"
    )
    await call.message.edit_text(text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")

# --- 2. عرض السيرفرات ---
async def manage_servers_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    
    servers = db.get_custom_servers()
    text = "🖥 **إدارة السيرفرات وهامش الربح**\n\nالسيرفرات الحالية وهامش الربح المضاف:\n\n"
    kb = InlineKeyboardMarkup(row_width=1)
    
    if servers:
        for s in servers:
            text += f"🔹 **{s['server_name']}** -> ربح إضافي: **+{s['margin_value']}$**\n"
            kb.add(InlineKeyboardButton(f"✏️ تعديل ربح: {s['server_name']}", callback_data=f"admin_edit_margin_{s['id']}"))
    else:
        text += "❌ لا توجد سيرفرات مضافة حالياً.\n"
        
    kb.add(InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin"))
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# --- 3. إحصائيات النظام ---
async def admin_stats_handler(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    
    total_users = db.get_all_users_count()
    servers = db.get_custom_servers()
    text = (
        "📊 **إحصائيات النظام الشاملة**\n\n"
        f"👥 إجمالي العملاء: `{total_users}`\n"
        f"⚙️ السيرفرات النشطة: `{len(servers)}`\n"
        f"🟢 حالة البوت: يعمل بكفاءة 🚀"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin")
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# --- 4. تعديل الهامش ---
async def edit_margin_start(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    
    server_id = int(call.data.split('_')[3])
    await state.update_data(target_server_id=server_id)
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 إلغاء", callback_data="admin_servers")
    )
    await call.message.edit_text("💰 أرسل الآن **مبلغ الربح الإضافي** الجديد (مثال: `0.15`):", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_margin_value.set()

async def edit_margin_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        margin_value = float(message.text)
        if margin_value < 0: raise ValueError
    except ValueError:
        return await message.answer("❌ يرجى إرسال رقم صحيح (مثال: 0.15):")
        
    data = await state.get_data()
    db.update_server_margin(data['target_server_id'], margin_value)
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin")
    )
    await message.answer(f"✅ تم تحديث هامش الربح بنجاح إلى **+{margin_value}$**.", reply_markup=kb, parse_mode="Markdown")

# --- 5. إضافة رصيد ---
async def start_add_balance(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("➕ أرسل الآن **ID العميل** المراد إضافة الرصيد له:", parse_mode="Markdown")
    await AdminStates.waiting_for_add_id.set()

async def process_add_id(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    if not message.text.isdigit(): return await message.answer("❌ أرسل ID صحيح (أرقام فقط):")
    
    user_id = int(message.text)
    user = db.get_user(user_id)
    if not user: return await message.answer("❌ العميل غير موجود!")
        
    await state.update_data(target_user_id=user_id)
    await message.answer(f"👤 العميل: {user['full_name']}\n💰 رصيده: {user['balance']}$\n\nأرسل **المبلغ المراد إضافته** ($):")
    await AdminStates.waiting_for_add_amount.set()

async def process_add_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("❌ أدخل مبلغ صحيح:")
        
    data = await state.get_data()
    db.update_balance(data['target_user_id'], amount)
    await state.finish()
    await message.answer(f"✅ تم إضافة **{amount}$** بنجاح.", parse_mode="Markdown")

# --- 6. خصم رصيد ---
async def start_deduct_balance(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("➖ أرسل الآن **ID العميل** المراد الخصم منه:", parse_mode="Markdown")
    await AdminStates.waiting_for_deduct_id.set()

async def process_deduct_id(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    if not message.text.isdigit(): return await message.answer("❌ أرسل ID صحيح (أرقام فقط):")
    
    user_id = int(message.text)
    user = db.get_user(user_id)
    if not user: return await message.answer("❌ العميل غير موجود!")
        
    await state.update_data(target_user_id=user_id)
    await message.answer(f"👤 العميل: {user['full_name']}\n💰 رصيده الحالي: {user['balance']}$\n\nأرسل **المبلغ المراد خصمه** ($):")
    await AdminStates.waiting_for_deduct_amount.set()

async def process_deduct_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("❌ أدخل مبلغ صحيح:")
        
    data = await state.get_data()
    db.update_balance(data['target_user_id'], -amount)
    await state.finish()
    await message.answer(f"✅ تم خصم **{amount}$** من حساب العميل بنجاح.", parse_mode="Markdown")

# --- 7. الإذاعة ---
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    await call.message.edit_text("📢 أرسل الرسالة المراد إذاعتها للجميع:")
    await AdminStates.waiting_for_broadcast.set()

async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    users = db.get_all_users()
    await message.answer(f"⏳ جاري الإذاعة لـ {len(users)} عميل...")
    success, failed = 0, 0
    for user in users:
        try:
            await message.copy_to(chat_id=user['user_id'])
            success += 1
        except Exception:
            failed += 1
    await state.finish()
    await message.answer(f"✅ انتهت الإذاعة!\n تم: {success} |  فشل: {failed}")

# --- التسجيل الكامل للـ Handlers ---
def register_admin_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(admin_dashboard, lambda c: c.data == "section_admin", state='*')
    dp.register_callback_query_handler(manage_servers_menu, lambda c: c.data == "admin_servers", state='*')
    dp.register_callback_query_handler(admin_stats_handler, lambda c: c.data == "admin_stats", state='*')
    
    dp.register_callback_query_handler(edit_margin_start, lambda c: c.data.startswith("admin_edit_margin_"), state='*')
    dp.register_message_handler(edit_margin_process, state=AdminStates.waiting_for_margin_value)
    
    dp.register_callback_query_handler(start_add_balance, lambda c: c.data == "admin_add_balance", state='*')
    dp.register_message_handler(process_add_id, state=AdminStates.waiting_for_add_id)
    dp.register_message_handler(process_add_amount, state=AdminStates.waiting_for_add_amount)
    
    # هنا تم إضافة تسجيل دوال خصم الرصيد
    dp.register_callback_query_handler(start_deduct_balance, lambda c: c.data == "admin_deduct_balance", state='*')
    dp.register_message_handler(process_deduct_id, state=AdminStates.waiting_for_deduct_id)
    dp.register_message_handler(process_deduct_amount, state=AdminStates.waiting_for_deduct_amount)
    
    dp.register_callback_query_handler(start_broadcast, lambda c: c.data == "admin_broadcast", state='*')
    dp.register_message_handler(process_broadcast, content_types=types.ContentType.ANY, state=AdminStates.waiting_for_broadcast)
