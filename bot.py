import logging
import json
import os
import asyncio
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
​إعداد السجلات
​logging.basicConfig(level=logging.INFO)
​---------------------------------------------------------
​الإعدادات الأساسية
​---------------------------------------------------------
​API_TOKEN = os.getenv("BOT_TOKEN", "5418318795:AAExmBwOEnNh6POj62mu15x339E1iIOW2y0")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "5396793642").split(",") if x.isdigit()]
​bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
​DB_FILE = "database.json"
​---------------------------------------------------------
​التعامل مع قاعدة البيانات Local JSON
​---------------------------------------------------------
​def load_db():
if os.path.exists(DB_FILE):
try:
with open(DB_FILE, "r", encoding="utf-8") as f:
return json.load(f)
except Exception as e:
logging.error(f"Error loading DB: {e}")
return {
"settings": {
"smsbower_api_key": ""
},
"users": {}
}
​def save_db(data):
try:
with open(DB_FILE, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=4)
except Exception as e:
logging.error(f"Error saving DB: {e}")
​---------------------------------------------------------
​قواميس الخدمات والدول
​---------------------------------------------------------
​SERVICES_CODES = {
"wa": "واتساب",
"tg": "تليجرام",
"ig": "انستغرام",
"fb": "فيسبوك",
"go": "جوجل / يوتيوب",
"tk": "تيك توك",
"mm": "تويتر / X",
"vi": "فايبر",
"vk": "VKontakte",
"ok": "Odnoklassniki"
}
​COUNTRY_NAMES = {
"0": "روسيا",
"1": "إنجلترا",
"2": "الصين",
"3": "الولايات المتحدة",
"16": "اليمن",
"29": "السعودية",
"73": "مصر",
"187": "الإمارات",
"4": "الفلبين",
"5": "إندونيسيا",
"6": "ماليزيا",
"7": "كينيا",
"8": "فيتنام",
"9": "قرغيزستان",
"10": "إسرائيل",
"11": "هونغ كونغ",
"12": "بولندا",
"13": "المملكة المتحدة",
"14": "مدغشقر",
"15": "الكونغو"
}
​---------------------------------------------------------
​حالات الأدمن (FSM)
​---------------------------------------------------------
​class AdminStates(StatesGroup):
waiting_for_api_key = State()
waiting_for_user_id = State()
waiting_for_balance = State()
​---------------------------------------------------------
​خادم وهمي لإبقاء Render حياً دون Port Timeout
​---------------------------------------------------------
​async def handle_ping(request):
return web.Response(text="Bot is running active and healthy!")
​async def start_background_web_server():
app = web.Application()
app.router.add_get('/', handle_ping)
app.router.add_get('/health', handle_ping)
​port = int(os.environ.get("PORT", 8080))
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, '0.0.0.0', port)
await site.start()
logging.info(f"Dummy Web Server running on port {port}")
​---------------------------------------------------------
​الأوامر الرئيسية
​---------------------------------------------------------
​@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
user_id = str(message.from_user.id)
db = load_db()
if user_id not in db["users"]:
db["users"][user_id] = {"balance": 0.0, "purchases": 0}
save_db(db)
​welcome_text = (
f"👋 أهلاً بك يا {message.from_user.first_name} في بوت تفعيل الأرقام!\n\n"
f"💰 رصيدك الحالي: {db['users'][user_id]['balance']} $"
)
​keyboard = types.InlineKeyboardMarkup(row_width=2)
keyboard.add(
types.InlineKeyboardButton("🛒 شراء رقم جديد", callback_data="buy_sim"),
types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
)
keyboard.add(
types.InlineKeyboardButton("💳 شحن الرصيد", callback_data="recharge_balance"),
types.InlineKeyboardButton("ℹ️ الدعم والتعليمات", callback_data="help_info")
)
if message.from_user.id in ADMIN_IDS:
keyboard.add(types.InlineKeyboardButton("⚙️ لوحة التحكم (أدمن)", callback_data="admin_panel"))
​await message.reply(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
​---------------------------------------------------------
​قوائم شراء وتصفح الخدمات والدول
​---------------------------------------------------------
​@dp.callback_query_handler(lambda c: c.data == "buy_sim")
async def buy_sim_menu(call: types.CallbackQuery):
keyboard = types.InlineKeyboardMarkup(row_width=2)
for srv_code, srv_name in SERVICES_CODES.items():
keyboard.insert(types.InlineKeyboardButton(srv_name, callback_data=f"buy_app_{srv_code}_0"))
keyboard.add(types.InlineKeyboardButton("🔙 الصفحة الرئيسية", callback_data="main_menu"))
​await call.message.edit_text("🛒 اختر التطبيق المطلوب للحصول على رقم:", reply_markup=keyboard, parse_mode="Markdown")
​@dp.callback_query_handler(lambda c: c.data.startswith('buy_app_'))
async def show_countries_for_buying(call: types.CallbackQuery):
parts = call.data.split('_')
serv_code = parts[2]
page = int(parts[3]) if len(parts) > 3 else 0
​db = load_db()
api_key = db.get("settings", {}).get("smsbower_api_key", "")
​if not api_key:
await call.answer("⚠️ لم يتم ضبط مفتاح API الخاص بالخدمة بعد. تواصل مع الأدمن.", show_alert=True)
return
​try:
url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getPrices"
resp = requests.get(url, timeout=10)
data = resp.json() if resp.status_code == 200 else None
​if not isinstance(data, dict):
await call.answer("⚠️ فشل جلب البيانات من المزود.", show_alert=True)
return
​matched = []
for cid, srv in data.items():
if not isinstance(srv, dict):
continue
if serv_code in srv:
matched.append(cid)
​PER_PAGE = 12
total_pages = (len(matched) + PER_PAGE - 1) // PER_PAGE if matched else 1
start_idx = page * PER_PAGE
end_idx = (page + 1) * PER_PAGE
current_countries = matched[start_idx:end_idx]
​keyboard = types.InlineKeyboardMarkup(row_width=2)
for cid in current_countries:
cname = COUNTRY_NAMES.get(str(cid), f"دولة ({cid})")
keyboard.insert(types.InlineKeyboardButton(cname, callback_data=f"get_num_{cid}_{serv_code}"))
​nav = []
if page > 0:
nav.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"buy_app_{serv_code}{page-1}"))
if page < total_pages - 1:
nav.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"buy_app{serv_code}_{page+1}"))
if nav:
keyboard.row(*nav)
​keyboard.add(types.InlineKeyboardButton("🔙 رجوع للتطبيقات", callback_data="buy_sim"))
​if not matched:
await call.answer("⚠️ لا توجد دول متاحة لهذا التطبيق حالياً.", show_alert=True)
return
​srv_title = SERVICES_CODES.get(serv_code, serv_code)
await call.message.edit_text(
f"🌍 تطبيق ({srv_title}) - صفحة {page+1}/{total_pages}\nاختر الدولة المطلوبة:",
reply_markup=keyboard,
parse_mode="Markdown"
)
except Exception as e:
logging.error(f"Error fetching prices: {e}")
await call.answer("❌ حدث خطأ أثنـاء الاتصال بالسيرفر.", show_alert=True)
​---------------------------------------------------------
​طلب الأرقام واستقبال الكود
​---------------------------------------------------------
​@dp.callback_query_handler(lambda c: c.data.startswith('get_num_'))
async def buy_number_action(call: types.CallbackQuery):
parts = call.data.split('_')
cid = parts[2]
serv_code = parts[3]
​user_id = str(call.from_user.id)
db = load_db()
api_key = db.get("settings", {}).get("smsbower_api_key", "")
​url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getNumber&service={serv_code}&country={cid}"
try:
resp = requests.get(url, timeout=10)
res_text = resp.text
​if "ACCESS_NUMBER" in res_text:
, id_order, number = res_text.split(":")
text = (
f"✅ تم طلب الرقم بنجاح!\n\n"
f"📱 الرقم: {number}\n"
f"🆔 معرف العملية: {id_order}\n\n"
f"⏳ بانتظار وصول كود التفعيل..."
)
keyboard = types.InlineKeyboardMarkup()
keyboard.add(types.InlineKeyboardButton("🔄 فحص كود SMS", callback_data=f"check_sms{id_order}"))
keyboard.add(types.InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"cancel_order_{id_order}"))
await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
else:
await call.answer(f"⚠️ لم يتم تجهيز رقم: {res_text}", show_alert=True)
except Exception as e:
await call.answer(f"❌ خطأ: {e}", show_alert=True)
​@dp.callback_query_handler(lambda c: c.data.startswith('check_sms_'))
async def check_sms_code(call: types.CallbackQuery):
id_order = call.data.split('_')[2]
db = load_db()
api_key = db.get("settings", {}).get("smsbower_api_key", "")
​url = f"https://smsbower.app/stubs/handler_api.php?api_key={api_key}&action=getStatus&id={id_order}"
try:
resp = requests.get(url, timeout=10)
res_text = resp.text
​if "STATUS_OK" in res_text:
code = res_text.split(":")[1]
await call.message.edit_text(f"🎉 وصل كود التفعيل!\n\n🔑 الكود: {code}", parse_mode="Markdown")
elif "STATUS_WAIT_CODE" in res_text:
await call.answer("⏳ لم يصل الكود بعد، يُرجى الانتظار...", show_alert=True)
else:
await call.answer(f"ℹ️ حالة الطلب: {res_text}", show_alert=True)
except Exception as e:
await call.answer(f"❌ خطأ: {e}", show_alert=True)
​---------------------------------------------------------
​لوحة التحكم والأدمن
​---------------------------------------------------------
​@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
if call.from_user.id not in ADMIN_IDS:
await call.answer("🚫 غير مسموح لك بالدخول هنا.", show_alert=True)
return
​db = load_db()
curr_key = db.get("settings", {}).get("smsbower_api_key", "غير مضبوط")
​text = (
"⚙️ لوحة تحكم الأدمن\n\n"
f"🔑 مفتاح SMSBower حالياً:\n{curr_key}"
)
keyboard = types.InlineKeyboardMarkup(row_width=1)
keyboard.add(
types.InlineKeyboardButton("🔑 تغيير مفتاح API", callback_data="change_api_key"),
types.InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu")
)
await call.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
​@dp.callback_query_handler(lambda c: c.data == "change_api_key")
async def request_api_key(call: types.CallbackQuery):
if call.from_user.id not in ADMIN_IDS:
return
await AdminStates.waiting_for_api_key.set()
await call.message.edit_text("📝 أرسل الآن مفتاح API الجديد الخاص بـ SMSBower:", parse_mode="Markdown")
​@dp.message_handler(state=AdminStates.waiting_for_api_key)
async def save_api_key(message: types.Message, state: FSMContext):
if message.from_user.id not in ADMIN_IDS:
return
​new_key = message.text.strip()
db = load_db()
db["settings"]["smsbower_api_key"] = new_key
save_db(db)
​await state.finish()
await message.reply(f"✅ تم حفظ مفتاح API الجديد بنجاح:\n{new_key}", parse_mode="Markdown")
​@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def back_to_main(call: types.CallbackQuery):
await send_welcome(call.message)
​---------------------------------------------------------
​تشغيل البوت والخادم
​---------------------------------------------------------
​async def on_startup(dp):
asyncio.create_task(start_background_web_server())
logging.info("Bot and Web Server successfully launched!")
​if name == 'main':
executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
