import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ----------------------------------------------------
# 1. إعداد خادم الويب (Heartbeat) لمنع التوقف على Render
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

# تشغيل الخادم الوهمي في الخلفية
threading.Thread(target=run_server, daemon=True).start()

# ----------------------------------------------------
# 2. إعدادات البوت والبيانات
# ----------------------------------------------------
API_TOKEN = "5418318795:AAE_s0NJw9IE1JWg6x9JuWQpl0MHDjcFCf8"
ADMIN_IDS = [5396793642]

DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving database: {e}")

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# الحالات (States)
class UserStates(StatesGroup):
    waiting_for_recharge_amount = State()

class AdminStates(StatesGroup):
    waiting_for_add_id = State()
    waiting_for_add_amount = State()

admin_temp_data = {}

# القائمة الرئيسية
def get_main_menu(user_id):
    menu_keyboard = InlineKeyboardMarkup(row_width=2)
    menu_keyboard.add(InlineKeyboardButton("⭐ الخدمات المطلوبة أكثر", callback_data="top_services"))
    menu_keyboard.add(
        InlineKeyboardButton("💖 خدمات الرشق 98", callback_data="buy_smm"),
        InlineKeyboardButton("🎁 شحن ألعاب 🎮", callback_data="buy_games")
    )
    menu_keyboard.add(InlineKeyboardButton("🛍️ متجر المنتجات الرقمية", callback_data="digital_store"))
    menu_keyboard.add(
        InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        InlineKeyboardButton("📝 سجل طلباتي", callback_data="my_orders")
    )
    menu_keyboard.add(
        InlineKeyboardButton("🔍 بحث عن خدمة", callback_data="search_service"),
        InlineKeyboardButton("🔄 حالة الطلب", callback_data="order_status")
    )
    menu_keyboard.add(InlineKeyboardButton("💰 شحن الرصيد", callback_data="recharge_balance"))
    
    if user_id in ADMIN_IDS:
        menu_keyboard.add(InlineKeyboardButton("⚙️ لوحة تحكم المشرفين", callback_data="admin_panel"))
        
    return menu_keyboard

# ----------------------------------------------------
# 3. الأوامر والأحداث
# ----------------------------------------------------
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    db = load_db()
    str_user_id = str(user_id)
    if str_user_id not in db:
        db[str_user_id] = {"balance": 0.0, "name": user_name}
        save_db(db)
        
    balance = db[str_user_id].get("balance", 0.0)
    
    welcome_text = (
        f"🌸 **قسم خدمات«الرشق»بطاقات»الألعاب**\n\n"
        f"أهلاً بك في بوابتك الشاملة لكل ما تحتاجه! 🌟\n"
        f"هنا يمكنك الوصول إلى:\n"
        f"◆ خدمات دعم السوشيال ميديا (الرشق)\n"
        f"◆ شحن الألعاب المباشر\n"
        f"◆ بطاقات الهدايا المتنوعة\n"
        f"◆ متجر المنتجات الرقمية (حسابات، اشتراكات، برامج)\n\n"
        f"💰 رصيدك الحالي: `{balance:.2f}` دولار أمريكي.\n\n"
        f"👇 اختر القسم الذي تريده من الأزرار أدناه:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.callback_query_handler(text="back_to_main")
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    db = load_db()
    balance = db.get(str(user_id), {}).get("balance", 0.0)
    
    welcome_text = (
        f"🌸 **القائمة الرئيسية**\n\n"
        f"💰 رصيدك الحالي: `{balance:.2f}` دولار أمريكي.\n\n"
        f"👇 اختر القسم الذي تريده من الأزرار أدناه:"
    )
    try:
        await call.message.edit_text(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    except Exception:
        await call.message.delete()
        await call.message.answer(welcome_text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")

# قسم شحن الرصيد
@dp.callback_query_handler(text="recharge_balance")
async def recharge_balance_start(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main")
    )
    text = (
        "💰 **شحن الرصيد**\n\n"
        "الرجاء إرسال المبلغ الذي تود إضافته إلى رصيدك بالدولار الأمريكي (مثال: 10 أو 4.5).\n\n"
        "🛑 **الحد الأدنى للشحن هو: 0.5$**"
    )
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await UserStates.waiting_for_recharge_amount.set()

@dp.message_handler(state=UserStates.waiting_for_recharge_amount)
async def process_recharge_amount(message: types.Message, state: FSMContext):
    if message.text == "إلغاء":
        await state.finish()
        await message.answer("تم إلغاء عملية شحن الرصيد.", reply_markup=get_main_menu(message.from_user.id))
        return
        
    try:
        amount = float(message.text.strip())
        if amount < 0.5:
            await message.answer("⚠️ عذراً، الحد الأدنى للشحن هو 0.5$ دولار. الرجاء إرسال مبلغ صحيح:")
            return
            
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        admin_notification = (
            f"🔔 **طلب شحن رصيد جديد!**\n\n"
            f"👤 المستخدم: {user_name}\n"
            f"🆔 الأيدي: `{user_id}`\n"
            f"💵 المبلغ المطلوب: `{amount}$`\n\n"
            f"قم بمراجعة التحويل وإضافة الرصيد له من لوحة التحكم."
        )
        
        for adm in ADMIN_IDS:
            try:
                await bot.send_message(adm, admin_notification, parse_mode="Markdown")
            except Exception:
                pass
                
        await message.answer(
            f"✅ **تم إرسال طلبك بنجاح!**\n\n"
            f"تم استلام طلب شحن بقيمة `{amount}$`. سيتم مراجعة العملية وإضافة الرصيد إلى حسابك فور تأكيد الدفع.",
            reply_markup=get_main_menu(user_id),
            parse_mode="Markdown"
        )
        await state.finish()
    except Exception:
        await message.answer("⚠️ الرجاء إرسال رقم صحيح يمثل المبلغ (مثال: 5 أو 10):")

@dp.callback_query_handler(text=["top_services", "buy_smm", "buy_games", "digital_store", "my_orders", "search_service", "order_status"])
async def dummy_sections(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 الرجوع إلى القائمة الرئيسية", callback_data="back_to_main"))
    await call.message.edit_text("⚙️ هذا القسم قيد التحديث وسيتم إطلاقه قريباً.", reply_markup=kb)

@dp.callback_query_handler(text="my_account")
async def my_account_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    db = load_db()
    balance = db.get(str(user_id), {}).get("balance", 0.0)
    text = f"👤 **معلومات حسابك:**\n\n🆔 الأيدي: `{user_id}`\n💰 الرصيد: `{balance:.2f}$`"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 الرجوع إلى القائمة الرئيسية", callback_data="back_to_main"))
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# لوحة التحكم للمشرف
@dp.callback_query_handler(text="admin_panel")
async def open_admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("عذراً، هذه اللوحة للمشرفين فقط!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ إضافة رصيد", callback_data="adm_add_balance"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")
    )
    await call.message.edit_text("⚙️ **لوحة تحكم المشرفين:**", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(text="adm_add_balance")
async def adm_add_1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text("أرسل أيدي (ID) المستخدم للإضافة له:", reply_markup=None)
    await AdminStates.waiting_for_add_id.set()

@dp.message_handler(state=AdminStates.waiting_for_add_id)
async def adm_add_2(message: types.Message, state: FSMContext):
    try:
        admin_temp_data['target_id'] = int(message.text.strip())
        await message.answer("الآن أرسل المبلغ المراد إضافته:")
        await AdminStates.waiting_for_add_amount.set()
    except:
        await message.answer("أيدي غير صحيح.")
        await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_add_amount)
async def adm_add_3(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        target_id = str(admin_temp_data.get('target_id'))
        db = load_db()
        if target_id not in db:
            db[target_id] = {"balance": 0.0, "name": "User"}
        db[target_id]["balance"] += amount
        save_db(db)
        await message.answer(f"✅ تمت إضافة {amount}$ بنجاح للمستخدم {target_id}")
        try:
            await bot.send_message(int(target_id), f"🎉 تمت إضافة رصيد بقيمة {amount}$ إلى حسابك بواسطة الإدارة!")
        except:
            pass
    except:
        await message.answer("خطأ في المبلغ.")
    await state.finish()

# تشغيل البوت نهائياً
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
