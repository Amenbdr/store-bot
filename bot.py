import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ضع توكن البوت الحقيقي هنا من BotFather
API_TOKEN = "5418318795:AAE_s0NJw9IE1JWg6x9JuWQpl0MHDjcFCf8"

# أيدي المشرف الخاص بك
ADMIN_IDS = [5396793642]

# قاموس لتخزين أرصدة المستخدمين مؤقتاً {user_id: balance}
user_balances = {}

# إعداد السجل (Logging)
logging.basicConfig(level=logging.INFO)

# تهيئة البوت والتخزين المؤقت للحالات
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# تعريف حالات المحادثة
class CheckoutState(StatesGroup):
    waiting_for_receipt = State()

class AdminStates(StatesGroup):
    waiting_for_add_id = State()
    waiting_for_add_amount = State()
    waiting_for_deduct_id = State()
    waiting_for_deduct_amount = State()
    waiting_for_ban_input = State()
    waiting_for_unban_input = State()

# متغير مؤقت لحفظ بيانات الإدارة أثناء العمليات
admin_temp_data = {}

# ----------------------------------------------------
# 1. أمر البدء (/start) وعرض الواجهة والأقسام
# ----------------------------------------------------
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # واجهة الأقسام والخدمات التي تظهر لجميع العملاء
    menu_keyboard = InlineKeyboardMarkup(row_width=2)
    menu_keyboard.add(
        InlineKeyboardButton("🎮 شدات ببجي (PUBG)", callback_data="buy_pubg"),
        InlineKeyboardButton("🔥 جواهر فري فاير (Free Fire)", callback_data="buy_freefire"),
        InlineKeyboardButton("📞 أرقام وهمية وتفعيل", callback_data="buy_sim"),
        InlineKeyboardButton("👤 حسابي / الرصيد", callback_data="my_account")
    )
    
    # إذا كان المستخدم هو المشرف، نضيف له زر لوحة التحكم في أسفل القائمة
    if user_id in ADMIN_IDS:
        menu_keyboard.add(InlineKeyboardButton("⚙️ لوحة تحكم المشرفين", callback_data="admin_panel"))
    
    welcome_text = (
        f"مرحباً بك يا **{user_name}** في متجرك الرقمي 🛒✨\n\n"
        "متجرنا موثق وسريع لتلبية طلبات الألعاب والخدمات الرقمية.\n"
        "الرجاء اختيار القسم أو الخدمة المطلوبة من الأزرار أدناه:"
    )
    
    await message.answer(welcome_text, reply_markup=menu_keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# 2. لوحة تحكم المشرفين الرئيسية
# ----------------------------------------------------
@dp.callback_query_handler(text="admin_panel")
async def open_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("عذراً، هذه اللوحة مخصصة للمشرفين فقط!", show_alert=True)
        return
        
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ إضافة رصيد لمستخدم", callback_data="adm_add_balance"),
        InlineKeyboardButton("➖ خصم رصيد من مستخدم", callback_data="adm_deduct_balance"),
        InlineKeyboardButton("🚫 حظر مستخدم", callback_data="adm_ban"),
        InlineKeyboardButton("✅ فك حظر مستخدم", callback_data="adm_unban"),
        InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main")
    )
    
    text = (
        "⚙️ **لوحة تحكم المشرفين الرئيسية**\n\n"
        "مرحباً بك يا مشرفنا. يمكنك إدارة أرصدة المستخدمين والتحكم بالنظام من الأزرار أدناه:"
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# 3. خطوات إضافة رصيد للمستخدم
# ----------------------------------------------------
@dp.callback_query_handler(text="adm_add_balance")
async def admin_add_bal_step1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text("➕ **إضافة رصيد**\n\nالرجاء إرسال **(ID)** المستخدم المراد إضافة الرصيد له:", reply_markup=None)
    await AdminStates.waiting_for_add_id.set()

@dp.message_handler(state=AdminStates.waiting_for_add_id)
async def admin_add_bal_step2(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(message.text.strip())
        admin_temp_data['target_id'] = target_id
        await message.answer("📥 ممتاز. الآن أرسل **المبلغ** المراد إضافته (مثلاً: 10 أو 5.5):")
        await AdminStates.waiting_for_add_amount.set()
    except Exception:
        await message.answer("⚠️ الرجاء إرسال أيدي (ID) صحيح ومكون من أرقام فقط.")
        await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_add_amount)
async def admin_add_bal_step3(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(message.text.strip())
        target_id = admin_temp_data.get('target_id')
        
        current_balance = user_balances.get(target_id, 0.0)
        user_balances[target_id] = current_balance + amount
        
        await message.answer(f"✅ **تمت العملية بنجاح!**\nتمت إضافة `{amount}$` إلى حساب المستخدم `{target_id}`.\nرصيده الحالي: `{user_balances[target_id]}$`", parse_mode="Markdown")
        
        try:
            await bot.send_message(target_id, f"🎉 **تمت إضافة رصيد إلى حسابك!**\nتم شحن مبلغ `{amount}$` بواسطة الإدارة.\nرصيدك الحالي: `{user_balances[target_id]}$`", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        await message.answer("⚠️ الرجاء إرسال مبلغ صحيح.")
    await state.finish()

# ----------------------------------------------------
# 4. خطوات خصم رصيد من المستخدم
# ----------------------------------------------------
@dp.callback_query_handler(text="adm_deduct_balance")
async def admin_deduct_bal_step1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text("➖ **خصم رصيد**\n\nالرجاء إرسال **(ID)** المستخدم المراد الخصم من رصيده:", reply_markup=None)
    await AdminStates.waiting_for_deduct_id.set()

@dp.message_handler(state=AdminStates.waiting_for_deduct_id)
async def admin_deduct_bal_step2(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(message.text.strip())
        admin_temp_data['target_id'] = target_id
        await message.answer("📤 ممتاز. الآن أرسل **المبلغ** المراد خصمه:")
        await AdminStates.waiting_for_deduct_amount.set()
    except Exception:
        await message.answer("⚠️ الرجاء إرسال أيدي (ID) صحيح.")
        await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_deduct_amount)
async def admin_deduct_bal_step3(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(message.text.strip())
        target_id = admin_temp_data.get('target_id')
        
        current_balance = user_balances.get(target_id, 0.0)
        if current_balance < amount:
            await message.answer(f"⚠️ تنبيه: رصيد المستخدم ({current_balance}$) أقل من المبلغ المراد خصمه ({amount}$)! تم الإلغاء.")
        else:
            user_balances[target_id] = current_balance - amount
            await message.answer(f"✅ **تم الخصم بنجاح!**\nتم خصم `{amount}$` من المستخدم `{target_id}`.\nرصيده الحالي: `{user_balances[target_id]}$`", parse_mode="Markdown")
            try:
                await bot.send_message(target_id, f"ℹ️ **تنبيه رصيد:**\nتم خصم مبلغ `{amount}$` من رصيدك بواسطة الإدارة.\nرصيدك الحالي: `{user_balances[target_id]}$`", parse_mode="Markdown")
            except Exception:
                pass
    except Exception:
        await message.answer("⚠️ الرجاء إرسال مبلغ صحيح.")
    await state.finish()

# ----------------------------------------------------
# 5. الحظر وفك الحظر
# ----------------------------------------------------
@dp.callback_query_handler(text="adm_ban")
async def admin_ban_prompt(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text("🚫 **حظر مستخدم**\nأرسل الآن (ID) الخاص بالمستخدم المراد حظره:", reply_markup=None)
    await AdminStates.waiting_for_ban_input.set()

@dp.message_handler(state=AdminStates.waiting_for_ban_input)
async def process_ban_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(message.text.strip())
        await message.answer(f"✅ تم حظر المستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
    except Exception:
        await message.answer("⚠️ الرجاء إرسال رقم أيدي صحيح.")
    await state.finish()

@dp.callback_query_handler(text="adm_unban")
async def admin_unban_prompt(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text("✅ **فك حظر مستخدم**\nأرسل الآن (ID) الخاص بالمستخدم لفك حظره:", reply_markup=None)
    await AdminStates.waiting_for_unban_input.set()

@dp.message_handler(state=AdminStates.waiting_for_unban_input)
async def process_unban_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(message.text.strip())
        await message.answer(f"✅ تم فك الحظر عن المستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
    except Exception:
        await message.answer("⚠️ الرجاء إرسال رقم أيدي صحيح.")
    await state.finish()

# ----------------------------------------------------
# 6. الأقسام والخدمات للعملاء
# ----------------------------------------------------
@dp.callback_query_handler(text="buy_pubg")
async def pubg_prices(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("60 شدة - 1$", callback_data="pay_pubg_60"),
        InlineKeyboardButton("325 شدة - 5$", callback_data="pay_pubg_325"),
        InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")
    )
    await call.message.edit_text("🎮 **قسم شدات ببجي موبايل**\nاختر الباقة المناسبة:", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="buy_freefire")
async def freefire_prices(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("100 جوهرة - 1$", callback_data="pay_ff_100"),
        InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")
    )
    await call.message.edit_text("🔥 **قسم جواهر فري فاير**\nاختر الباقة المناسبة:", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="buy_sim")
async def sim_prices(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🇺🇸 رقم أمريكي واتساب - 2$", callback_data="pay_sim_us"),
        InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_main")
    )
    await call.message.edit_text("📞 **قسم الأرقام الوهمية والتفعيل** (@SIM_NUMBERS)\nاختر الرقم المطلوب:", reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# 7. نظام الدفع اليدوي واستلام الإيصالات
# ----------------------------------------------------
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('pay_'))
async def process_checkout(call: types.CallbackQuery, state: FSMContext):
    item_code = call.data
    my_binance_pay_id = "459326037"
    
    text = (
        f"🛒 **إتمام عملية الشراء**\n"
        f"📦 **الطلب:** `{item_code}`\n\n"
        "الرجاء تحويل المبلغ إلى حساب باينانس باي التالي:\n"
        f"📌 **Binance Pay ID:** `{my_binance_pay_id}`\n\n"
        "بعد التحويل، **قم بإرسال صورة إيصال الدفع** هنا في المحادثة لتأكيد طلبك."
    )
    await call.message.answer(text, parse_mode="Markdown")
    await CheckoutState.waiting_for_receipt.set()
    await call.answer()

@dp.message_handler(state=CheckoutState.waiting_for_receipt, content_types=types.ContentTypes.PHOTO)
async def receive_receipt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "بدون معرف"
    photo_id = message.photo[-1].file_id
    orders_channel = "@SPEDERCH"
    
    caption = f"🔔 **طلب شراء جديد بانتظار التأكيد**\n\n👤 **المستخدم:** @{username}\n🆔 **الايدي:** `{user_id}`"
    
    admin_keyboard = InlineKeyboardMarkup(row_width=2)
    admin_keyboard.add(
        InlineKeyboardButton("✅ قبول وتسليم", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user_id}")
    )
    
    await bot.send_photo(chat_id=orders_channel, photo=photo_id, caption=caption, reply_markup=admin_keyboard, parse_mode="Markdown")
    await message.answer("✅ **تم إرسال إيصال الدفع بنجاح!**\nجاري مراجعة الطلب من قبل الإدارة وتسليمك المنتج في أقرب وقت.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('accept_') or c.data.startswith('reject_')))
async def admin_decision(call: types.CallbackQuery):
    action, target_user_id = call.data.split('_')
    target_user_id = int(target_user_id)
    
    if action == "accept":
        try:
            await bot.send_message(target_user_id, "🎉 **تم تأكيد دفعك بنجاح!**\nتم قبول طلبك، وجاري تسليم الخدمة لك الآن.")
        except Exception:
            pass
        await call.message.edit_caption(caption=call.message.caption + "\n\n✅ **حالة الطلب: تم القبول والتسليم بنجاح**", reply_markup=None)
        await call.answer("تم قبول الطلب!")
    elif action == "reject":
        try:
            await bot.send_message(target_user_id, "❌ **عذراً، تم رفض طلبك.**\nيرجى التواصل مع الدعم الفني للاستفسار.")
        except Exception:
            pass
        await call.message.edit_caption(caption=call.message.caption + "\n\n❌ **حالة الطلب: تم الرفض**", reply_markup=None)
        await call.answer("تم رفض الطلب.")

# ----------------------------------------------------
# 8. الحساب الشخصي والأزرار العامة
# ----------------------------------------------------
@dp.callback_query_handler(text="my_account")
async def user_account_info(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.username or "لا يوجد"
    balance = user_balances.get(user_id, 0.0)
    
    text = (
        f"👤 **معلومات حسابك الشخصي:**\n\n"
        f"🆔 الايدي: `{user_id}`\n"
        f"🏷 المعرف: @{username}\n"
        f"💰 رصيدك الحالي: `{balance}$`"
    )
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@dp.callback_query_handler(text="back_to_main")
async def back_to_main_menu(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    # القائمة الرئيسية للعملاء
    menu_keyboard = InlineKeyboardMarkup(row_width=2)
    menu_keyboard.add(
        InlineKeyboardButton("🎮 شدات ببجي (PUBG)", callback_data="buy_pubg"),
        InlineKeyboardButton("🔥 جواهر فري فاير (Free Fire)", callback_data="buy_freefire"),
        InlineKeyboardButton("📞 أرقام وهمية وتفعيل", callback_data="buy_sim"),
        InlineKeyboardButton("👤 حسابي / الرصيد", callback_data="my_account")
    )
    
    # إذا كان المستخدم هو المشرف، نضيف له زر لوحة التحكم أيضاً عند العودة
    if user_id in ADMIN_IDS:
        menu_keyboard.add(InlineKeyboardButton("⚙️ لوحة تحكم المشرفين", callback_data="admin_panel"))
        
    await call.message.edit_text("مرحباً بك مرة أخرى في القائمة الرئيسية 🛒✨\nاختر القسم المطلوب:", reply_markup=menu_keyboard, parse_mode="Markdown")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
