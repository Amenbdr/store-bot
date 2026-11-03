import time
import threading
import requests
from telebot import TeleBot, types
from flask import Flask

app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

TELEGRAM_BOT_TOKEN = "5418318795:AAG3lt5CD7OYl4kgCNkReX5r7CwSy8ljZ0I"
API_URL = "https://smsbower.app/stubs/handler_api.php"

bot = TeleBot(TELEGRAM_BOT_TOKEN)
USER_API_KEYS = {}
USER_STATES = {}

COUNTRIES = {
    "sa": {"name": "السعودية", "flag": "🇸🇦", "code": "sa"},
    "eg": {"name": "مصر", "flag": "🇪🇬", "code": "eg"},
    "ae": {"name": "الإمارات", "flag": "🇦🇪", "code": "ae"},
    "usa": {"name": "أمريكا", "flag": "🇺🇸", "code": "usa"},
    "ru": {"name": "روسيا", "flag": "🇷🇺", "code": "ru"},
    "uk": {"name": "بريطانيا", "flag": "🇬🇧", "code": "gb"}
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔑 إدخال/تحديث مفتاح API", callback_data="set_api_key"),
        types.InlineKeyboardButton("📱 شراء رقم جديد", callback_data="main_menu")
    )
    bot.reply_to(message, "مرحباً! أرسل مفتاح الـ API أولاً:", reply_markup=markup)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_for_api_key")
def receive_api_key(message):
    chat_id = message.chat.id
    api_key = message.text.strip()
    res = requests.get(API_URL, params={'api_key': api_key, 'action': 'getBalance'}, timeout=10)
    if ":" in res.text:
        USER_API_KEYS[chat_id] = api_key
        USER_STATES[chat_id] = None
        bot.reply_to(message, f"✅ تم الحفظ! الرصيد: {res.text.split(':')[-1]} $")
    else:
        bot.reply_to(message, "❌ المفتاح غير صحيح، حاول مجدداً:")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "set_api_key":
        USER_STATES[chat_id] = "waiting_for_api_key"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "✍️ أرسل مفتاح الـ API الآن:")

    elif data == "main_menu" or data == "back_to_services":
        if chat_id not in USER_API_KEYS:
            bot.answer_callback_query(call.id, "أدخل مفتاح API أولاً!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💬 واتساب", callback_data="service_wa"),
            types.InlineKeyboardButton("✈️ تليجرام", callback_data="service_tg")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="اختر التطبيق:", reply_markup=markup)

    elif data.startswith("service_"):
        service_code = data.split("_")[1]
        markup = types.InlineKeyboardMarkup(row_width=2)
        for key, c in COUNTRIES.items():
            markup.add(types.InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"select_{service_code}_{c['code']}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_services"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="اختر الدولة:", reply_markup=markup)

    elif data.startswith("select_"):
        _, service_code, country_code = data.split("_")
        bot.answer_callback_query(call.id, "جاري فحص الاستجابة...")

        params = {
            'api_key': USER_API_KEYS[chat_id],
            'action': 'getTopCountriesByService',
            'service': service_code
        }
        res = requests.get(API_URL, params=params)
        
        # طباعة الاستجابة الكاملة في الـ Logs لنراها بدقة
        print("--- RAW API RESPONSE ---")
        print(res.text)
        print("------------------------")

        bot.send_message(chat_id, f"📥 تم فحص الاستجابة وطباعتها في سجلات المنصة (Logs). الاستجابة المختصرة:\n`{res.text[:300]}`", parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
