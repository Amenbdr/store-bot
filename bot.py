import time
import threading
import requests
from telebot import TeleBot, types

# ==================== الإعدادات الأساسية ====================
TELEGRAM_BOT_TOKEN = "5418318795:AAG31t5CD7OY14kgCNkRex5r7CwSy81jZOI"  # التوكن من BotFather

API_URL = "https://smsbower.app/stubs/handler_api.php"
# ==========================================================

bot = TeleBot(TELEGRAM_BOT_TOKEN)

# قاموس مؤقت لحفظ مفاتيح الـ API لكل مستخدم (مפתח القاموس هو معرف المستخدم chat_id)
# (ملاحظة: في المشاريع الكبيرة يفضل استبدال هذا بقاعدة بيانات مثل SQLite)
USER_API_KEYS = {}

# قاموس مؤقت لمتابعة حالة المستخدم (مثلاً: ينتظر إدخال مفتاح الـ API)
USER_STATES = {}

COUNTRIES = {
    "sa": {"name": "السعودية", "flag": "🇸🇦", "code": "sa"},
    "eg": {"name": "مصر", "flag": "🇪🇬", "code": "eg"},
    "ae": {"name": "الإمارات", "flag": "🇦🇪", "code": "ae"},
    "usa": {"name": "أمريكا", "flag": "🇺🇸", "code": "usa"},
    "ru": {"name": "روسيا", "flag": "🇷🇺", "code": "ru"},
    "uk": {"name": "بريطانيا", "flag": "🇬🇧", "code": "gb"}
}

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

            if "STATUS_OK" in status_text:
                code = status_text.split(":")[-1]
                bot.send_message(
                    chat_id,
                    f"🎉 **لقد وصل رمز التفعيل للرقم `{phone}`!**\n\n🔑 **الرمز:** `{code}`",
                    parse_mode="Markdown"
                )
                return
            
            elif "STATUS_CANCEL" in status_text:
                bot.send_message(chat_id, f"❌ تم إلغاء الرقم `{phone}` مسبقاً.", parse_mode="Markdown")
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
        "مرحباً بك في بوت خدمات الأرقام!\n\nيرجى أولاً إدخال مفتاح الـ API الخاص بك من موقع SMSBower للبدء:", 
        reply_markup=markup
    )

# 2. استقبال النصوص (مثل مفتاح الـ API عندما يطلبه البوت)
@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "waiting_for_api_key")
def receive_api_key(message):
    chat_id = message.chat.id
    api_key = message.text.strip()
    
    # اختبار صلاحية المفتاح عبر فحص الرصيد
    params = {'api_key': api_key, 'action': 'getBalance'}
    try:
        res = requests.get(API_URL, params=params, timeout=10)
        if "ACCESS_BALANCE" in res.text or ":" in res.text:
            # حفظ المفتاح للمستخدم
            USER_API_KEYS[chat_id] = api_key
            USER_STATES[chat_id] = None # إنهاء حالة الانتظار
            
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

    # طلب إدخال المفتاح
    if data == "set_api_key":
        USER_STATES[chat_id] = "waiting_for_api_key"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "✍️ أرسل الآن **مفتاح الـ API (API Key)** الخاص بك في رسالة جديدة:")

    # فحص الرصيد
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

    # القائمة الرئيسية لاختيار التطبيق
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

    # اختيار التطبيق -> عرض الدول مع الأعلام
    elif data.startswith("service_"):
        service_code = data.split("_")[1]
        service_name = "واتساب" if service_code == "wa" else "تليجرام"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        for key, c in COUNTRIES.items():
            btn_text = f"{c['flag']} {c['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"select_{service_code}_{c['code']}"))
        
        btn_back = types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_services")
        markup.add(btn_back)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"اختر الدولة لتطبيق ({service_name})[span_1](start_span)[span_1](end_span):",
            reply_markup=markup
        )

    # اختيار الدولة -> جلب السيرفرات والأسعار والمخزون
    elif data.startswith("select_"):
        _, service_code, country_code = data.split("_")
        bot.answer_callback_query(call.id, "جاري جلب السيرفرات المتاحة...")

        params = {
            'api_key': USER_API_KEYS[chat_id],
            'action': 'getTopCountriesByService',
            'service': service_code
        }
        
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            data_json = response.json()
            country_servers = data_json.get(country_code, {})
            
            if not country_servers:
                bot.send_message(chat_id, "⚠️ لا توجد سيرفرات أو أرقام متاحة لهذه الدولة حالياً.")
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for server_id, info in country_servers.items():
                price = info.get("price", "N/A")
                count = info.get("count", "N/A")
                button_text = f"سيرفر #{server_id} | الكمية: {count} | السعر: {price} $"
                markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_{service_code}_{country_code}_{server_id}"))
            
            country_info = COUNTRIES.get(country_code, {"name": country_code, "flag": "🌐"})
            bot.send_message(
                chat_id,
                f"إليك السيرفرات المتاحة لدولة {country_info['flag']} {country_info['name']}[span_2](start_span)[span_2](end_span):\nاختر السيرفر للشراء:",
                reply_markup=markup
            )
        except Exception:
            bot.send_message(chat_id, "❌ حدث خطأ أثناء الاتصال بالسيرفرات.")

    # شراء الرقم وتشغيل الفحص التلقائي
    elif data.startswith("buy_"):
        _, service, country, server_id = data.split("_")
        bot.answer_callback_query(call.id, "جاري طلب الرقم...")
        
        user_key = USER_API_KEYS[chat_id]
        buy_params = {
            'api_key': user_key,
            'action': 'getNumber',
            'service': service,
            'country': country,
            'providerIds': server_id
        }
        res = requests.get(API_URL, params=buy_params)
        
        if "ACCESS_NUMBER" in res.text:
            _, activation_id, phone = res.text.split(":")
            
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

            # تشغيل الفحص التلقائي في الخلفية مع تمرير مفتاح المستخدم الخاص به
            t = threading.Thread(target=auto_check_sms, args=(chat_id, user_key, activation_id, phone))
            t.daemon = True
            t.start()

        else:
            bot.send_message(chat_id, f"❌ تعذر شراء الرقم. السبب: {res.text}")

    # إلغاء الرقم واسترداد الرصيد
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
    print("🤖 البوت يعمل الآن ويطلب مفتاح API من المستخدمين...")
    bot.infinity_polling()
