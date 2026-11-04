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

async def admin_dashboard(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("⛔ لا تملك صلاحية الوصول للوحة الأدمن!", show_alert=True)
        
    total_users = db.get_all_users_count()
    text = (
        "⚙️ **لوحة التحكم الخاصة بالإدارة**\n\n"
        f"👥 إجمالي العملاء المسجلين: **{total_users} عميل**\n\n"
        "اختر الإجراء المطلوب من الأزرار أدناه:"
    )
    await call.message.edit_text(text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")

async def manage_servers_menu(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: 
        return
    
    await call.answer()
    servers = db.get_custom_servers()
    text = "🖥 **إدارة السيرفرات وهامش الربح**\n\nالسيرفرات الحالية وهامش الربح المضاف لكل سيرفر:\n\n"
    kb = InlineKeyboardMarkup(row_width=1)
    
    if servers:
        for s in servers:
            text += f"🔹 **{s['server_name']}** -> ربح إضافي: **+{s['margin_value']}$**\n"
            kb.add(InlineKeyboardButton(f"✏️ تعديل ربح: {s['server_name']}", callback_data=f"admin_edit_margin_{s['id']}"))
    else:
        text += "❌ لا توجد سيرفرات مضافة حالياً.\n"
        
    kb.add(InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin"))
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

async def edit_margin_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: 
        return
    
    await call.answer()
    server_id = int(call.data.split('_')[3])
    await state.update_data(target_server_id=server_id)
    
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 إلغاء", callback_data="admin_servers")
    )
    await call.message.edit_text("💰 أرسل الآن **مبلغ الربح الإضافي** الجديد (مثال: `0.15` أو `0.20` $):", reply_markup=kb, parse_mode="Markdown")
    await AdminStates.waiting_for_margin_value.set()

async def edit_margin_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        margin_value = float(message.text)
        if margin_value < 0: 
            raise ValueError
    except ValueError:
        return await message.answer("❌ يرجى إرسال رقم صحيح (مثال: 0.15):")
        
    data = await state.get_data()
    db.update_server_margin(data['target_server_id'], margin_value)
    await state.finish()
    
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin")
    )
    await message.answer(f"✅ تم تحديث هامش الربح للسيرفر بنجاح إلى **+{margin_value}$**.", reply_markup=kb, parse_mode="Markdown")

async def admin_stats_handler(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("⛔ غير مسموح.", show_alert=True)
    
    await call.answer()
    total_users = db.get_all_users_count()
    servers = db.get_custom_servers()
    
    text = (
        "📊 **إحصائيات النظام الشاملة**\n\n"
        f"👥 إجمالي المستخدمين: `{total_users}`\n"
        f"⚙️ السيرفرات النشطة: `{len(servers)}`\n"
        f"🟢 حالة البوت: يعمل بكفاءة تامة 🚀"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="section_admin")
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

async def start_add_balance(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: 
        return
    await call.answer()
    await call.message.edit_text("➕ أرسل الآن **ID العميل** المراد إضافة الرصيد له:", parse_mode="Markdown")
    await AdminStates.waiting_for_add_id.set()

async def process_add_id(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text.isdigit(): 
        return await message.answer("❌ يرجى إرسال ID صحيح (أرقام فقط):")
    
    user_id = int(message.text)
    user = db.get_user(user_id)
    if not user: 
        return await message.answer("❌ العميل غير موجود في قاعدة البيانات!")
        
    await state.update_data(target_user_id=user_id)
    await message.answer(f"👤 العميل: {user['full_name']}\n💰 رصيده الحالي: {user['balance']}$\n\nأرسل **المبلغ المراد إضافته** ($):")
    await AdminStates.waiting_for_add_amount.set()

async def process_add_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(message.text)
        if amount <= 0: 
            raise ValueError
    except ValueError:
        return await message.answer("❌ أدخل مبلغ صحيح أكبر من الصفر:")
        
    data = await state.get_data()
    db.update_balance(data['target_user_id'], amount)
    await state.finish()
    await message.answer(f"✅ تم إضافة **{amount}$** لحساب العميل بنجاح.", parse_mode="Markdown")

async def start_deduct_balance(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: 
        return
    await call.answer()
    await call.message.edit_text("➖ أرسل **ID العميل** المراد الخصم منه:", parse_mode="Markdown")
    await AdminStates.waiting_for_deduct_id.set()

async def process_deduct_id(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text.isdigit(): 
        return await message.answer("❌ ID غير صحيح:")
        
    user_id = int(message.text)
    user = db.get_user(user_id)
    if not user: 
        return await message.answer("❌ العميل غير موجود!")
        
    await state.update_data(target_user_id=user_id)
    await message.answer(f"👤 العميل: {user['full_name']}\n💰 رصيده الحالي: {user['balance']}$\n\nأرسل **المبلغ المراد خصمه** ($):")
    await AdminStates.waiting_for_deduct_amount.set()

async def process_deduct_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(message.text)
        if amount <= 0: 
            raise ValueError
    except ValueError:
        return await message.answer("❌ أدخل مبلغ صحيح:")
        
    data = await state.get_data()
    db.update_balance(data['target_user_id'], -amount)
    await state.finish()
    await message.answer("✅ تم خصم المبلغ من حساب العميل بنجاح.", parse_mode="Markdown")

async def start_broadcast(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: 
        return
    await call.answer()
    await call.message.edit_text("📢 أرسل الرسالة المراد إذاعتها لجميع العملاء (نص، صورة، أو وسائط):")
    await AdminStates.waiting_for_broadcast.set()

async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
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
    await message.answer(f"✅ انتهت الإذاعة بنجاح!\n📤 تم الإرسال: {success}\n❌ فشل الإرسال: {failed}")

def register_admin_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(admin_dashboard, lambda c: c.data == "section_admin", state='*')
    dp.register_callback_query_handler(manage_servers_menu, lambda c: c.data == "admin_servers", state='*')
    dp.register_callback_query_handler(admin_stats_handler, lambda c: c.data == "admin_stats", state='*')
    dp.register_callback_query_handler(edit_margin_start, lambda c: c.data.startswith("admin_edit_margin_"), state='*')
    dp.register_message_handler(edit_margin_process, state=AdminStates.waiting_for_margin_value)
    
    dp.register_callback_query_handler(start_add_balance, lambda c: c.data == "admin_add_balance", state='*')
    dp.register_message_handler(process_add_id, state=AdminStates.waiting_for_add_id)
    dp.register_message_handler(process_add_amount, state=AdminStates.waiting_for_add_amount)
    
    dp.register_callback_query_handler(start_deduct_balance, lambda c: c.data == "admin_deduct_balance", state='*')
    dp.register_message_handler(process_deduct_id, state=AdminStates.waiting_for_deduct_id)
    dp.register_message_handler(process_deduct_amount, state=AdminStates.waiting_for_deduct_amount)
    
    dp.register_callback_query_handler(start_broadcast, lambda c: c.data == "admin_broadcast", state='*')
    dp.register_message_handler(process_broadcast, content_types=types.ContentType.ANY, state=AdminStates.waiting_for_broadcast)
