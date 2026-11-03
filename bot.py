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

# دالة الفحص التلقائي لوصول الكود في الخلفية
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
    btn_services = types.InlineKeyboardButton("📱 قائمة الخدمات المتاحة", callback_data="main_menu")
    
    markup.add(btn_set_key, btn_balance, btn_services)
    
    bot.reply_to(
        message, 
        "مرحباً بك في بوت خدمات الأرقام!\n\nيرجى أولاً إدخال مفتاح الـ API الخاص بك من موقع SMSBower للبدء:", 
        reply_markup=markup
    )

# 2. استقبال النصوص (مفتاح الـ API)
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
        bot.reply_to(message, "❌ حدث خطأ أثناء الاتصال بالموقع للتأكد من المفتاح. حاول لاحقاً.")

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

        bot.answer_callback_query(call.id, "جاري جلب الخدمات المتاحة من الموقع...")
        
        # جلب قائمة الأسعار والخدمات مباشرة من الموقع لتفادي أي خطأ في اسم الخدمة
        try:
            res = requests.get(API_URL, params={'api_key': USER_API_KEYS[chat_id], 'action': 'getPrices'}, timeout=10)
            data_json = res.json()
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            # استخراج الأكواد الخاصة بالخدمات المتاحة في حسابك بالموقع
            services_found = set()
            if isinstance(data_json, dict):
                for country_id, services in data_json.items():
                    if isinstance(services, dict):
                        for s_code in services.keys():
                            services_found.add(s_code)

            # إذا نجحنا في جلب الأكواد ديناميكياً
            if len(services_found) > 0:
                for s_code in list(services_found)[:20]: # عرض أول 20 خدمة متاحة
                    markup.add(types.InlineKeyboardButton(f"📱 خدمة: {s_code}", callback_data=f"service_{s_code}"))
            else:
                # خيارات احتياطية في حال لم يعيد الموقع القائمة تلقائياً
                markup.add(types.InlineKeyboardButton("💬 واتساب", callback_data="service_wa"),
                           types.InlineKeyboardButton("✈️ تليجرام", callback_data="service_tg"))

            btn_balance = types.InlineKeyboardButton("💰 فحص الرصيد", callback_data="check_balance")
            markup.add(btn_balance)

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="اختر كود الخدمة المتاح المطلوب من القائمة:",
                reply_markup=markup
            )
        except Exception:
            # في حال حدوث خطأ، نعرض خيارات افتراضية دقيقة
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("💬 واتساب (wa)", callback_data="service_wa"),
                       types.InlineKeyboardButton("✈️ تليجرام (tg)", callback_data="service_tg"))
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="اختر الخدمة:",
                reply_markup=markup
            )

    elif data.startswith("service_"):
        service_code = data.split("_")[1]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_all = types.InlineKeyboardButton("🌐 عرض جميع الدول المتاحة", callback_data=f"countries_{service_code}")
        markup.add(btn_all)
        
        btn_back = types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_services")
        markup.add(btn_back)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"اختر طريقة عرض الدول لخدمة ({service_code}):",
            reply_markup=markup
        )

    elif data.startswith("countries_"):
        service_code = data.split("_")[1]
        bot.answer_callback_query(call.id, "جاري جلب الدول المتاحة...")

        user_key = USER_API_KEYS[chat_id]
        
        try:
            countries_res = requests.get(API_URL, params={'api_key': user_key, 'action': 'getCountries'}, timeout=10)
            countries_json = countries_res.json()
            
            params = {
                'api_key': user_key,
                'action': 'getTopCountriesByService',
                'service': service_code
            }
            response = requests.get(API_URL, params=params, timeout=10)
            data_json = response.json()

            markup = types.InlineKeyboardMarkup(row_width=2)
            if isinstance(data_json, dict):
                for country_name in data_json.keys():
                    country_numeric_id = country_name
                    if isinstance(countries_json, dict):
                        for k, v in countries_json.items():
                            if isinstance(v, dict):
                                if country_name.lower() in str(v.get("eng", "")).lower() or country_name.lower() in str(v.get("rus", "")).lower() or k.lower() == country_name.lower():
                                    country_numeric_id = str(v.get("id", k))
                                    break

                    markup.add(types.InlineKeyboardButton(f"🌍 {country_name.capitalize()}", callback_data=f"select_country_{service_code}_{country_numeric_id}_{country_name}"))

            btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            markup.add(btn_back)

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="اختر الدولة المطلوبة:",
                reply_markup=markup
            )
        except Exception:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء جلب قائمة الدول.")

    elif data.startswith("select_country_"):
        parts = data.split("_")
        service_code = parts[2]
        country_numeric_id = parts[3]
        country_name = "_".join(parts[4:])
        
        bot.answer_callback_query(call.id, "جاري جلب السيرفرات...")

        user_key = USER_API_KEYS[chat_id]
        params = {
            'api_key': user_key,
            'action': 'getTopCountriesByService',
            'service': service_code
        }
        
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            data_json = response.json()
            
            servers = data_json.get(country_name, {})
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            if isinstance(servers, dict):
                for provider_id, info in servers.items():
                    if isinstance(info, dict):
                        price = info.get("price", "N/A")
                        count = info.get("count", "N/A")
                        button_text = f"سيرفر #{provider_id} | الكمية: {count} | السعر: {price} $"
                        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_{service_code}_{country_numeric_id}_{provider_id}"))

            if len(markup.keyboard) == 0:
                bot.send_message(chat_id, "⚠️ لا توجد سيرفرات نشطة لهذه الدولة حالياً.")
                return

            bot.send_message(
                chat_id,
                f"إليك السيرفرات المتاحة لدولة `{country_name}`:\nاختر السيرفر للشراء:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء جلب السيرفرات.")

    elif data.startswith("buy_"):
        parts = data.split("_")
        service = parts[1]
        country_numeric_id = parts[2]
        provider_id = parts[3]
        
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

if __name__ == "__main__":
    keep_alive()
    print("🤖 البوت يعمل الآن بنجاح...")
    bot.infinity_polling()
