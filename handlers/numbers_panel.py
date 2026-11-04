import math
import asyncio
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DEFAULT_SMSBOWER_KEY
from database import db
from services.smsbower_api import SMSBowerService

sms_service = SMSBowerService(api_key=DEFAULT_SMSBOWER_KEY)

COUNTRIES_AR = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "2": "🇰🇿 كازاخستان", "3": "🇨🇳 الصين",
    "4": "🇵🇭 الفلبين", "6": "🇮🇩 إندونيسيا", "12": "🇺🇸 أمريكا", "16": "🇬🇧 بريطانيا",
    "17": "🇲🇦 المغرب", "21": "🇪🇬 مصر", "22": "🇮🇳 الهند", "29": "🇵🇰 باكستان",
    "31": "🇿🇦 جنوب أفريقيا", "36": "🇨🇦 كندا", "43": "🇩🇪 ألمانيا", "46": "🇸🇪 السويد",
    "47": "🇮🇶 العراق", "48": "🇳🇱 هولندا", "53": "🇪🇸 إسبانيا", "58": "🇩🇿 الجزائر",
    "59": "🇸🇦 السعودية", "73": "🇧🇷 البرازيل", "78": "🇫🇷 فرنسا", "86": "🇮🇹 إيطاليا",
    "87": "🇾🇪 اليمن", "89": "🇹🇳 تونس", "94": "🇱🇧 لبنان", "95": "🇦🇪 الإمارات",
    "97": "🇵🇸 فلسطين", "100": "🇱🇾 ليبيا", "104": "🇸🇾 سوريا", "105": "🇸🇩 السودان",
    "106": "🇰🇼 الكويت", "107": "🇴🇲 عُمان", "111": "🇶🇦 قطر", "114": "🇲🇷 موريتانيا",
    "116": "🇯🇴 الأردن", "117": "🇵🇹 البرتغال", "145": "🇧🇭 البحرين", "161": "🇹🇷 تركيا"
}

def numbers_main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💬 واتساب (WhatsApp)", callback_data="num_service_wa"),
        InlineKeyboardButton("✈️ تليجرام (Telegram)", callback_data="num_service_tg")
    )
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main"))
    return kb

def countries_keyboard(service_id: str, page: int = 0):
    kb = InlineKeyboardMarkup(row_width=2)
    items_per_page = 12
    country_items = list(COUNTRIES_AR.items())
    total_pages = math.ceil(len(country_items) / items_per_page)
    start = page * items_per_page
    end = start + items_per_page
    current_countries = country_items[start:end]
    for c_id, c_name in current_countries:
        kb.insert(InlineKeyboardButton(c_name, callback_data=f"num_cntry_{service_id}_{c_id}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"num_page_{service_id}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"num_page_{service_id}_{page+1}"))
    if nav_buttons:
        kb.row(*nav_buttons)
    kb.add(InlineKeyboardButton("🔙 اختيار التطبيق", callback_data="section_numbers"))
    return kb

async def show_numbers_section(call: types.CallbackQuery):
    await call.answer()
    text = "📱 **قسم الأرقام الوهمية**\n\nاختر التطبيق المراد شراء رقم له:"
    await call.message.edit_text(text, reply_markup=numbers_main_keyboard(), parse_mode="Markdown")

async def select_service_handler(call: types.CallbackQuery):
    await call.answer("⏳ جاري التحميل...")
    service_id = call.data.split('_')[2]
    app_name = "واتساب" if service_id == "wa" else "تليجرام"
    await call.message.edit_text(f"اختر الدولة المطلوبة لخدمة {app_name}:", reply_markup=countries_keyboard(service_id, page=0))

async def change_page_handler(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split('_')
    service_id, page = parts[2], int(parts[3])
    app_name = "واتساب" if service_id == "wa" else "تليجرام"
    await call.message.edit_text(f"اختر الدولة المطلوبة لخدمة {app_name}:", reply_markup=countries_keyboard(service_id, page=page))

async def process_country_handler(call: types.CallbackQuery):
    await call.answer("⏳ جاري فحص السيرفرات والأسعار...")
    parts = call.data.split('_')
    service_id, country_id = parts[2], parts[3]
    app_name = "واتساب" if service_id == "wa" else "تليجرام"
    
    # جلب تفاصيل الأسعار المخصصة للدولة والخدمة من السيرفر الخارجي
    prices_data = sms_service.get_prices(service_id, country_id)
    if not prices_data:
        return await call.answer("❌ لا توجد أرقام متوفرة لهذه الدولة حالياً.", show_alert=True)
    
    # استخراج السعر الحقيقي مع دعم القواميس أو القيم المتعددة
    base_cost = 0.50
    if isinstance(prices_data, dict):
        base_cost = float(prices_data.get(str(country_id), prices_data.get('cost', prices_data.get('price', 0.50))))
    elif isinstance(prices_data, (int, float)):
        base_cost = float(prices_data)
        
    custom_servers = db.get_custom_servers()
    kb = InlineKeyboardMarkup(row_width=1)
    for index, server in enumerate(custom_servers, start=1):
        margin = float(server['margin_value'])
        final_price = round(base_cost + margin, 2)
        button_text = f"{app_name} | {final_price}$ | سيرفر {index}"
        kb.add(InlineKeyboardButton(button_text, callback_data=f"num_buy_{service_id}_{country_id}_{server['id']}_{final_price}"))
        
    kb.add(InlineKeyboardButton("🔙 العودة لقائمة الدول", callback_data=f"num_service_{service_id}"))
    country_name = COUNTRIES_AR.get(country_id, country_id)
    text = f"📱 **تطبيق:** {app_name}\n🌍 **الدولة:** {country_name}\n\n👇 اختر السيرفر المناسب للشراء:"
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

async def monitor_sms_code(bot, chat_id: int, message_id: int, activation_id: str, phone_number: str, country_name: str, app_name: str, final_price: float):
    for _ in range(30):
        await asyncio.sleep(10)
        status = sms_service.get_sms_code(activation_id)
        if status and status != "WAITING":
            success_text = (
                f"😍 ⌯ يبدوا ان الكود قد وصل لهذا الرقم ✅.\n\n"
                f"✅ NUMBER : `+{phone_number}`\n"
                f"💬 CODE : `{status}`\n\n"
                f"✅ - إضغط على الكود او الرقم للنسخ. 😌🌸\n"
                f"🙋‍♂️ - اذا وصلت لك هذه الرسالة مرتين يرجى إرسال الرقم الى الدعم لإرجاع قيمة الرقم الى حسابك. 👮"
            )
            try:
                await bot.send_message(chat_id, success_text, parse_mode="Markdown")
            except Exception:
                pass
            return
            
    timeout_text = (
        f"✅ الرقم : `+{phone_number}`\n"
        f"🇰🇸 الدولة : {country_name}\n"
        f"🛒 التطبيق : {app_name}\n"
        f"⏳ الحالة : Timeout ... ⏰\n\n"
        f"⏰ الوقت المتبقي : 00:00:00 دقيقة\n"
        f"⚠️ انتهى الوقت المتاح للرقم\n"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔄 الشراء مجدداً بنفس السعر!", callback_data=f"num_service_{app_name.lower()}"),
        InlineKeyboardButton("🔙 رجوع", callback_data="section_numbers")
    )
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=timeout_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

async def buy_number_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split('_')
    service_id, country_id, server_id, final_price = parts[2], parts[3], parts[4], float(parts[5])
    
    user = db.get_user(user_id)
    if not user or user['balance'] < final_price:
        return await call.answer(f"❌ رصيدك غير كافي! السعر المطلوب: {final_price}$", show_alert=True)
        
    await call.answer("⏳ جاري طلب الرقم من السيرفر...", show_alert=True)
    order = sms_service.buy_number(service_id, country_id)
    if order:
        db.update_balance(user_id, -final_price)
        db.add_order(user_id, "Virtual Number", f"+{order['number']}", final_price, "Completed")
        country_name = COUNTRIES_AR.get(country_id, country_id)
        app_name = "واتساب" if service_id == "wa" else "تليجرام"
        clean_number = order['number'].replace('+', '')
        text = (
            f"✅ **تم شراء رقم جديد**\n\n"
            f"🇰🇸 الدولة : {country_name}\n"
            f"🛒 التطبيق : {app_name}\n\n"
            f"📞 الرقم : `+{order['number']}`\n"
            f"🔄 الحالة : Pending ... 🔄\n"
            f"💰 السعر : {final_price}$\n\n"
            f"⚠️ اضغط على الرقم لنسخه!\n"
            f"📥 أدخل الرقم في التطبيق لوصول الكود، ثم اضغط على زر تحديث."
        )
        kb = InlineKeyboardMarkup(row_width=1)
        if service_id == "wa":
            kb.add(InlineKeyboardButton("🌐 رؤية حالة الرقم في واتساب", url=f"https://wa.me/{clean_number}"))
        kb.add(
            InlineKeyboardButton("🔄 تحديث.", callback_data=f"num_check_{order['activation_id']}"),
            InlineKeyboardButton("⚠️ إلغاء.", callback_data=f"num_cancel_{order['activation_id']}_{final_price}"),
            InlineKeyboardButton("🔙 رجوع.", callback_data="section_numbers")
        )
        msg = await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        asyncio.create_task(monitor_sms_code(
            call.bot, call.message.chat.id, msg.message_id, 
            order['activation_id'], order['number'], country_name, app_name, final_price
        ))
    else:
        await call.answer("❌ تعذر شراء الرقم حالياً أو نفدت الكمية. يرجى المحاولة لاحقاً.", show_alert=True)

async def check_sms_handler(call: types.CallbackQuery):
    status = sms_service.get_sms_code(call.data.split('_')[2])
    if status == "WAITING":
        await call.answer("⏳ لم يتم استلام الكود بعد...", show_alert=True)
    elif status:
        await call.answer("📬 تم استلام الكود بنجاح!", show_alert=False)
        await call.message.edit_text(f"📬 **تم استلام كود التفعيل!**\n\nالكود هو: `{status}`", parse_mode="Markdown")
    else:
        await call.answer("⚠️ انتهت المهلة أو تم إلغاء الرقم.", show_alert=True)

async def cancel_number_handler(call: types.CallbackQuery):
    await call.answer("⏳ جاري معالجة الإلغاء...")
    user_id = call.from_user.id
    parts = call.data.split('_')
    activation_id, price = parts[2], float(parts[3])
    
    status = sms_service.get_sms_code(activation_id)
    if status and status != "WAITING":
        db.update_balance(user_id, -price)
        db.add_order(user_id, "Penalty / Abuse", f"ID: {activation_id}", price, "Penalized")
        warning_text = (
            f"⚠️ **تحذير أمني ونظامي صارم!** ⚠️\n\n"
            f"لقد حاولت إلغاء الرقم بعد أن **تم إرسال كود التفعيل عليه بالفعل**!\n"
            f"❌ **العقوبة المطبقة:** تم تطبيق غرامة وخصم قيمة الرقم (**{price}$**) مرتين من رصيدك."
        )
        return await call.message.edit_text(warning_text, parse_mode="Markdown")
        
    if sms_service.cancel_activation(activation_id):
        db.update_balance(user_id, price)
        await call.message.edit_text(f"تم إلغاء الرقم بنجاح وإعادة **{price}$** إلى رصيدك. ♻️", parse_mode="Markdown")
    else:
        await call.answer("❌ تعذر إلغاء الرقم الآن.", show_alert=True)

def register_numbers_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(show_numbers_section, lambda c: c.data == "section_numbers")
    dp.register_callback_query_handler(select_service_handler, lambda c: c.data.startswith("num_service_"))
    dp.register_callback_query_handler(change_page_handler, lambda c: c.data.startswith("num_page_"))
    dp.register_callback_query_handler(process_country_handler, lambda c: c.data.startswith("num_cntry_"))
    dp.register_callback_query_handler(buy_number_handler, lambda c: c.data.startswith("num_buy_"))
    dp.register_callback_query_handler(check_sms_handler, lambda c: c.data.startswith("num_check_"))
    dp.register_callback_query_handler(cancel_number_handler, lambda c: c.data.startswith("num_cancel_"))
