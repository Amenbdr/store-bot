import time
import threading
import requests
from telebot import TeleBot, types
from flask import Flask

# ==================== إعدادات سيرفر الويب الوهمي ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
# ====================================================================

# ==================== الإعدادات الأساسية للبوت ====================
TELEGRAM_BOT_TOKEN = "5418318795:AAG3lt5CD7OYl4kgCNkReX5r7CwSy8ljZ0I"
API_URL = "https://smsbower.app/stubs/handler_api.php"

bot = TeleBot(TELEGRAM_BOT_TOKEN)

USER_API_KEYS = {}
USER_STATES = {}

# قائمة الـ 12 دولة الأساسية مع أسمائها بالعربية وأعلامها ومعرفاتها الرقمية
POPULAR_COUNTRIES = [
    {"id": "0", "name": "🇷🇺 روسيا", "eng": "russia"},
    {"id": "1", "name": "🇺🇦 أوكرانيا", "eng": "ukraine"},
    {"id": "2", "name": "🇰🇿 كازاخستان", "eng": "kazakhstan"},
    {"id": "3", "name": "🇨🇳 الصين", "eng": "china"},
    {"id": "5", "name": "🇺🇸 الولايات المتحدة", "eng": "usa"},
    {"id": "6", "name": "🇨🇦 كندا", "eng": "canada"},
    {"id": "12", "name": "🇬🇧 بريطانيا", "eng": "uk"},
    {"id": "15", "name": "🇵🇱 بولندا", "eng": "poland"},
    {"id": "16", "name": "🇫🇷 فرنسا", "eng": "france"},
    {"id": "22", "name": "🇮🇳 الهند", "eng": "india"},
    {"id": "32", "name": "🇮🇩 إندونيسيا", "eng": "indonesia"},
    {"id": "36", "name": "🇪🇬 مصر", "eng": "egypt"}
]

# دالة الفحص التلقائي لوصول كود الـ SMS في الخلفية مطابقة لتوثيق getStatus
def auto_check_sms(chat_id, api_key, activation_id, phone):
    max_attempts = 60  
    attempt = 0

    while attempt < max_attempts:
        time.sleep(5)
        attempt += 1

        params = {
            'api_key': api_key,
            'action': 'getStatus',
            'id': activation_id
        }
        try:
            res = requests.get(API_URL, params=params, timeout=10)
            status_text = res.text.strip()

            if "STATUS_CANCEL" in status_text:
                bot.send_message(chat_id, f"❌ تم إلغاء التفعيل للرقم `{phone}`.", parse_mode="Markdown")
                return
            
            elif "STATUS_WAIT_RETRY" in status_text or "STATUS_WAIT_CODE" in status_text:
                continue

            elif ":" in status_text or len(status_text) > 0:
                parts = status_text.split(":")
                code = parts[-1] if len(parts) > 1 else status_text

                if "NO_ACTIVATION" not in code and "BAD_KEY" not in code:
                    bot.send_message(
                        chat_id,
                        f"🎉 **لقد وصل رمز التفعيل للرقم `{phone}`!**\n\n🔑 **الرمز:** `{code}`",
                        parse_mode="Markdown"
                    )
                    return
                
        except Exception:
            pass

    bot.send_message(
        chat_id, 
        f"⏰ انتهت مهلة الانتظار (5 دقائق) ولم يتم رصد رمز للرقم `{phone}` تلقائياً.",
        parse_mode="Markdown"
    )

# 1. أمر البداية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_set_key = types.InlineKeyboardButton("🔑 إدخال/تحديث مفتاح API", callback_data="set_api_key")
    btn_balance = types.InlineKeyboardButton("💰 فحص الرصيد", callback_data="check_balance")
    btn_services = types.InlineKeyboardButton("📱 شراء رقم جديد", callback_data="main_menu")
    
    markup.add(btn_set_key, btn_balance, btn_services)
    
    bot.reply_to(
        message, 
        "مرحباً بك في بوت خدمات الأرقام السريع!\n\nيرجى أولاً إدخال مفتاح الـ API الخاص بك من موقع SMSBower للبدء:", 
        reply_markup=markup
    )

# 2. استقبال مفتاح الـ API
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_for_api_key")
def receive_api_key(message):
    chat_id = message.chat.id
    api_key = message.text.strip()
    
    params = {'api_key': api_key, 'action': 'getBalance'}
    try:
        res = requests.get(API_URL, params=params, timeout=10)
        if "ACCESS_BALANCE" in res.text or ":" in res.text:
            USER_API_KEYS[chat_id] = api_key
            USER_STATES[chat_id] = None 
            
            balance = res.text.split(":")[-1]
            bot.reply_to(message, f"✅ **تم حفظ مفتاح الـ API بنجاح!**\n💰 رصيدك الحالي: {balance} $", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ مفتاح الـ API غير صحيح أو منتهي الصلاحية. يرجى إرسال مفتاح صحيح:")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ أثناء الاتصال بالموقع. حاول لاحقاً.")

# 3. معالجة الأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "set_api_key":
        USER_STATES[chat_id] = "waiting_for_api_key"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "✍️ أرسل الآن **مفتاح الـ API (API Key)** الخاص بك في رسالة جديدة:")

    elif data == "check_balance":
        if chat_id not in USER_API_KEYS:
            bot.answer_callback_query(call.id, "يجب إدخال مفتاح API أولاً!", show_alert=True)
            return
            
        bot.answer_callback_query(call.id, "جاري فحص الرصيد...")
        res = requests.get(API_URL, params={'api_key': USER_API_KEYS[chat_id], 'action': 'getBalance'})
        if "ACCESS_BALANCE" in res.text or ":" in res.text:
            bal = res.text.split(":")[-1]
            bot.send_message(chat_id, f"💰 رصيدك الحالي: {bal} $")
        else:
            bot.send_message(chat_id, f"❌ خطأ في المفتاح أو استجابة الموقع: {res.text}")

    elif data == "main_menu" or data == "back_to_services":
        if chat_id not in USER_API_KEYS:
            bot.answer_callback_query(call.id, "يجب إدخال مفتاح API أولاً!", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_wa = types.InlineKeyboardButton("💬 واتساب (WhatsApp)", callback_data="service_wa")
        btn_tg = types.InlineKeyboardButton("✈️ تليجرام (Telegram)", callback_data="service_tg")
        btn_balance = types.InlineKeyboardButton("💰 فحص الرصيد", callback_data="check_balance")
        
        markup.add(btn_wa, btn_tg)
        markup.add(btn_balance)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="اختر التطبيق الذي تريد شراء رقم له:",
            reply_markup=markup
        )

    elif data.startswith("service_"):
        service_code = data.split("_")[1]
        service_name = "واتساب" if service_code == "wa" else "تليجرام"
        
        # الانتقال لعرض الصفحة الأولى (الصفحة رقم 0) من الدول الـ 12
        show_countries_page(chat_id, call.message.message_id, service_code, page=0)

    elif data.startswith("cpage_"):
        parts = data.split("_")
        service_code = parts[1]
        page = int(parts[2])
        show_countries_page(chat_id, call.message.message_id, service_code, page=page)

    elif data.startswith("select_country_"):
        parts = data.split("_")
        service_code = parts[2]
        country_id = parts[3]
        country_eng_name = parts[4]
        
        bot.answer_callback_query(call.id, "جاري جلب أسعار والمخزون والسيرفرات...")

        user_key = USER_API_KEYS[chat_id]
        params = {
            'api_key': user_key,
            'action': 'getTopCountriesByService',
            'service': service_code
        }
        
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            data_json = response.json()
            
            # البحث عن السيرفرات الخاصة بالدولة بالاسم الإنجليزي أو المعرف
            servers = data_json.get(country_eng_name, {})
            if not servers and isinstance(data_json, dict):
                for dk, dv in data_json.items():
                    if country_eng_name.lower() in dk.lower() or dk.lower() in country_eng_name.lower():
                        servers = dv
                        break

            markup = types.InlineKeyboardMarkup(row_width=1)
            
            if isinstance(servers, dict) and len(servers) > 0:
                for provider_id, info in servers.items():
                    if isinstance(info, dict):
                        price = info.get("price", "N/A")
                        count = info.get("count", "N/A")
                        button_text = f"🌐 سيرفر #{provider_id} | المخزون: {count} | السعر: {price} $"
                        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_{service_code}_{country_id}_{provider_id}"))
            else:
                # خيار الشراء المباشر في حال لم تتوفر تفاصيل السيرفرات مفصلة للمزودين
                markup.add(types.InlineKeyboardButton("🚀 شراء مباشر (سيرفر افتراضي)", callback_data=f"buy_{service_code}_{country_id}_0"))

            btn_back = types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data=f"service_{service_code}")
            markup.add(btn_back)

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"📊 **سيرفرات وأسعار ومخزون الدولة:**\nاختر السيرفر المناسب للشراء:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception:
            bot.answer_callback_query(call.id, "حدث خطأ في جلب بيانات السيرفرات.", show_alert=True)

    elif data.startswith("buy_"):
        parts = data.split("_")
        service = parts[1]
        country_numeric_id = parts[2]
        provider_id = parts[3] if len(parts) > 3 else "0"
        
        bot.answer_callback_query(call.id, "جاري طلب الرقم...")
        
        user_key = USER_API_KEYS[chat_id]
        
        buy_params = {
            'api_key': user_key,
            'action': 'getNumber',
            'service': service,
            'country': country_numeric_id,
            'providerIds': provider_id
        }
        res = requests.get(API_URL, params=buy_params)
        
        if "ACCESS_NUMBER" in res.text:
            res_parts = res.text.split(":")
            activation_id = res_parts[1]
            phone = res_parts[2] if len(res_parts) > 2 else "متاح"
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_cancel = types.InlineKeyboardButton("❌ إلغاء الرقم واسترداد الرصيد", callback_data=f"cancel_{activation_id}")
            markup.add(btn_cancel)

            bot.send_message(
                chat_id,
                f"✅ **تم شراء الرقم بنجاح!**\n\n"
                f"📱 **الرقم:** `{phone}`\n"
                f"🆔 **معرف التفعيل:** `{activation_id}`\n\n"
                f"🔄 **جاري مراقبة وصول كود الـ SMS تلقائياً...** سيتم إرساله هنا فور وصوله.",
                parse_mode="Markdown",
                reply_markup=markup
            )

            t = threading.Thread(target=auto_check_sms, args=(chat_id, user_key, activation_id, phone))
            t.daemon = True
            t.start()

        else:
            bot.send_message(chat_id, f"❌ تعذر شراء الرقم. السبب: {res.text}")

    elif data.startswith("cancel_"):
        activation_id = data.split("_")[1]
        bot.answer_callback_query(call.id, "جاري إلغاء الرقم...")

        params = {
            'api_key': USER_API_KEYS[chat_id],
            'action': 'setStatus',
            'status': 8,
            'id': activation_id
        }
        res = requests.get(API_URL, params=params)
        status_text = res.text.strip()

        if "ACCESS_CANCEL" in status_text or "ACCESS_OK" in status_text:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"🚫 **تم إلغاء الرقم بنجاح وإعادة رصيدك للحساب!**\n🆔 المعرف: `{activation_id}`",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                chat_id,
                f"⚠️ لا يمكن إلغاء الرقم حالياً (قد يكون مر وقت طويل أو وصل الكود بالفعل).\nالاستجابة: {status_text}"
            )

# دالة لعرض الدول بصفحات (كل صفحة تحتوي على 6 دول مع أزرار التالي والسابق)
def show_countries_page(chat_id, message_id, service_code, page=0):
    items_per_page = 6
    total_countries = len(POPULAR_COUNTRIES)
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    
    page_countries = POPULAR_COUNTRIES[start_idx:end_idx]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # إضافة أزرار الدول بنظام صفين
    row_buttons = []
    for c in page_countries:
        row_buttons.append(types.InlineKeyboardButton(c["name"], callback_data=
