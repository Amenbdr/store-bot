import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    init_db, get_user, update_user_language, save_user_credentials, 
    get_total_users_count, get_profit_margin, set_profit_margin,
    find_user_by_identifier, update_user_balance, log_user_activity, get_user_logs
)
from admin import show_admin_panel
from api_services import (
    get_pinned_products, pin_product, unpin_product, search_products_from_provider,
    get_product_details_from_provider, send_order_to_provider, pay_order_in_provider,
    get_order_status_from_provider, get_all_providers, check_provider_balance, 
    update_provider_api_key, get_provider_config
)

TELEGRAM_BOT_TOKEN = "5418318795:AAGioQ8yj8DkVLiOCaiPv3h-tmaZPJcdecQ"
REQUIRED_CHANNEL = "@SIM_NUMBERS"          # قناة الاشتراك الإجباري
ORDERS_LOG_CHANNEL = "@SPEDERCH"           # قناة الطلبات العامة المشفرة
ADMIN_ID = 5396793642                      # الآيدي الخاص بك
OWNER_USERNAME = "DF00D"                   # معرف المالك لتواصل الشحن

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class BotStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_target = State()
    waiting_for_quantity = State()
    waiting_for_new_margin = State()
    waiting_for_custom_price = State()
    admin_get_user = State()
    admin_get_amount = State()
    waiting_for_new_api_key = State()
    admin_searching_product = State()

def mask_target_info(info: str) -> str:
    info = str(info).strip()
    if info.isdigit():
        if len(info) > 6:
            return info[:3] + "****" + info[-3:]
        return "***" + info[-2:] if len(info) > 2 else "****"
    else:
        if len(info) > 4:
            return info[:3] + "****" + info[-2:]
        return "@****"

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        conn = sqlite3.connect("secure_bot_database.db")
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    if not await check_subscription(user_id):
        builder = InlineKeyboardBuilder()
        builder.button(text="SIM_NUMBERS✅", url="https://t.me/SIM_NUMBERS")
        builder.button(text="🔄 تحقق من الاشتراك", callback_data="check_sub")
        builder.adjust(1)
        return await message.answer(
            "⚠️ **يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه!**\n\n"
            "يرجى الضغط على الزر أدناه للاشتراك:", 
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    
    await show_language_selection(message)

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.delete()
        await show_language_selection(callback)
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

async def show_language_selection(message_or_callback):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇸🇦 العربية", callback_data="lang_ar")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    text = "اختر لغتك المفضلة / Choose your language:"
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    update_user_language(user_id, lang)
    
    user_data = get_user(user_id)
    if not user_data or not user_data[0] or not user_data[0].endswith("@gmail.com"):
        await state.set_state(BotStates.waiting_for_email)
        text = (
            "⚠️ **يجب عليك تسجيل حسابك أولاً لتتمكن من الدخول واستخدام البوت.**\n\n"
            "📧 **أدخل بريدك الإلكتروني (يجب أن ينتهي بـ `@gmail.com`):**"
            if lang == "ar" else 
            "⚠️ **You must register your account first to use the bot.**\n\n"
            "📧 **Enter your email (must end with `@gmail.com`):**"
        )
        await callback.message.edit_text(text, parse_mode="Markdown")
    else:
        await show_main_menu(callback, lang)

@dp.message(BotStates.waiting_for_email)
async def process_user_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not email.endswith("@gmail.com"):
        return await message.answer("❌ **عذراً، يجب أن ينتهي البريد بـ `@gmail.com`. حاول مجدداً:**", parse_mode="Markdown")
    await state.update_data(email=email)
    await state.set_state(BotStates.waiting_for_password)
    await message.answer("🔑 **أدخل كلمة المرور الخاصة بحسابك:**", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_password)
async def process_user_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    save_user_credentials(message.from_user.id, message.from_user.username or "No", data.get("email"), password)
    await state.clear()
    
    await message.answer("✅ **تم حفظ بياناتك بنجاح! جاري الدخول...**", parse_mode="Markdown")
    user_data = get_user(message.from_user.id)
    lang = user_data[2] if user_data else "ar"
    await show_main_menu(message, lang)

@dp.callback_query(F.data == "set_email")
async def change_email_request(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_email)
    await callback.message.answer("📧 **أدخل بريدك الإلكتروني الجديد (يجب أن ينتهي بـ `@gmail.com`):**", parse_mode="Markdown")

async def show_main_menu(event: types.Message | types.CallbackQuery, lang: str):
    user = event.from_user
    user_data = get_user(user.id)
    email = user_data[0] if user_data else "غير مسجل"
    is_admin = user_data[3] if user_data else 0
    balance = user_data[4] if user_data else 0.0
    
    builder = InlineKeyboardBuilder()
    if lang == "ar":
        builder.button(text="⭐ خدمات واشتراكات تليجرام", callback_data="telegram_services")
        builder.button(text="💳 شحن الرصيد", url=f"https://t.me/{OWNER_USERNAME}")
        builder.button(text="📋 سجل طلباتي", callback_data="my_orders_log")
        builder.button(text="📧 تعديل بياناتي", callback_data="set_email")
        builder.button(text="🌐 تغيير اللغة", callback_data="change_lang")
        if is_admin:
            builder.button(text="⚙️ لوحة تحكم الأدمن", callback_data="admin_panel")
        builder.adjust(1, 2, 2, 1)
        
        text = (
            f"مرحباً بك، **{user.first_name}** 👋\n\n"
            f"🆔 **الآيدي:** `{user.id}`\n"
            f"📧 **الإيميل:** `{email}`\n"
            f"💰 **رصيدك الحالي:** `{balance}$`\n\n"
            "اختر القسم المطلوب من القائمة أدناه:"
        )
    else:
        builder.button(text="⭐ Telegram Services", callback_data="telegram_services")
        builder.button(text="💳 Recharge Balance", url=f"https://t.me/{OWNER_USERNAME}")
        builder.button(text="📋 My Orders Log", callback_data="my_orders_log")
        builder.button(text="📧 Update Info", callback_data="set_email")
        builder.button(text="🌐 Change Language", callback_data="change_lang")
        if is_admin:
            builder.button(text="⚙️ Admin Panel", callback_data="admin_panel")
        builder.adjust(1, 2, 2, 1)
        
        text = (
            f"Welcome, **{user.first_name}** 👋\n\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"📧 **Email:** `{email}`\n"
            f"💰 **Balance:** `{balance}$`\n\n"
            "Choose a section from below:"
        )
        
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "change_lang")
async def process_change_lang(callback: types.CallbackQuery):
    await show_language_selection(callback)

@dp.callback_query(F.data == "back_to_menu")
async def process_back_menu(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    lang = user_data[2] if user_data else "ar"
    await show_main_menu(callback, lang)

@dp.callback_query(F.data == "my_orders_log")
async def show_user_activity_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logs = get_user_logs(user_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    if not logs:
        return await callback.message.edit_text(
            "📋 **سجل عملياتك وطلباتك:**\n\nعذراً، ليس لديك أي عمليات شحن سابقة حتى الآن.",
            reply_markup=builder.as_markup(), parse_mode="Markdown"
        )
    
    log_text = "📋 **آخر عمليات الشحن والطلبات الخاصة بك:**\n\n"
    for idx, (service, target, cost, created_at) in enumerate(logs, 1):
        log_text += (
            f"*{idx}. الخدمة:* {service}\n"
            f"👤 *المستهدف:* `{target}`\n"
            f"💵 *التكلفة:* `{cost}$`\n"
            f"🕒 *الوقت:* `{created_at}`\n"
            "-----------------------------------\n"
        )
        
    await callback.message.edit_text(log_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "telegram_services")
async def process_telegram_services(callback: types.CallbackQuery):
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    
    if pinned:
        for p_id, p_name, p_price, _ in pinned:
            builder.button(text=f"🔹 {p_name} — 💰 {p_price}$", callback_data=f"viewprod_{p_id}")
    else:
        builder.button(text="⚠️ لا توجد خدمات مثبتة حالياً من الإدارة", callback_data="none")
        
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    text = (
        "⭐ **قسـم خدمات واشتراكات تليجرام**\n\n"
        "اختر الخدمة أو القسم المطلوبة للاطلاع على التفاصيل وإتمام الطلب:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("viewprod_"))
async def process_view_product_details(callback: types.CallbackQuery, state: FSMContext):
    p_id = callback.data.split("_")[1]
    
    await callback.answer("⏳ جاري جلب التفاصيل...", show_alert=False)
    product_data = await get_product_details_from_provider(p_id)
    
    pinned = get_pinned_products()
    selected_product = next((p for p in pinned if p[0] == p_id), None)
    
    if selected_product and selected_product[2] > 0:
        p_price = selected_product[2]
    elif product_data:
        p_price = float(product_data.get("bestOfferPrice") or product_data.get("price") or product_data.get("retail_price") or 0.0)
    else:
        p_price = selected_product[2] if selected_product else 0.0

    p_name = product_data.get("name", selected_product[1] if selected_product else "خدمة رقمية")
    p_desc = product_data.get("description") if product_data else "لا توجد تفاصيل إضافية متاحة."
    stock_count = product_data.get("inStockCount", "متاح") if product_data else "متاح"

    is_stars = "star" in p_name.lower() or "نجم" in p_name.lower()

    await state.update_data(product_id=p_id, service_name=p_name, service_price=p_price, is_stars=is_stars)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 شراء وتأكيد الطلب", callback_data="confirm_buy_step")
    builder.button(text="🔙 العودة للأقسام", callback_data="telegram_services")
    builder.adjust(1)
    
    text = (
        f"📦 **الخدمة / القسم:** `{p_name}`\n\n"
        f"💰 **السعر الحالي:** `{p_price}$`\n"
        f"📦 **المخزون:** `{stock_count}`\n\n"
        f"📝 **التفاصيل:**\n{p_desc}\n\n"
        "اضغط على زر الشراء أدناه للمتابعة:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "confirm_buy_step")
async def process_confirm_buy(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_stars = data.get("is_stars", False)
    
    if is_stars:
        await state.set_state(BotStates.waiting_for_quantity)
        await callback.message.edit_text(
            "⭐ **هذا القسم خاص بنجوم تليجرام.**\n\n"
            "🔢 **أدخل عدد النجوم المطلوبة (مثلاً: 50 أو 500):**\n"
            "(الحد الأدنى 50 نجمة)",
            parse_mode="Markdown"
        )
    else:
        await state.set_state(BotStates.waiting_for_target)
        await callback.message.edit_text(
            "📥 **أدخل معرف المستخدم (User ID) أو اليوزر المراد الشحن له:**",
            parse_mode="Markdown"
        )

@dp.message(BotStates.waiting_for_quantity)
async def process_star_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 50:
            return await message.answer("❌ الحد الأدنى للنجوم هو 50 نجمة. أدخل رقماً صحيحاً مجدداً:")
        await state.update_data(quantity=qty)
        await state.set_state(BotStates.waiting_for_target)
        await message.answer(f"✅ تم تحديد الكمية: `{qty} نجمة`\n\n📥 **أدخل معرف المستخدم (User ID) أو اليوزر المطلوب الشحن له:**", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً لعدد النجوم:")

@dp.message(BotStates.waiting_for_target)
async def process_target_id(message: types.Message, state: FSMContext):
    target_info = message.text.strip()
    data = await state.get_data()
    
    product_id = data.get("product_id")
    service_name = data.get("service_name", "خدمة رقمية")
    base_price = data.get("service_price", 1.0)
    quantity = data.get("quantity", 1)
    
    total_price = round(base_price * quantity, 2) if quantity > 1 else base_price
    
    msg = await message.answer("⏳ **جاري إرسال طلبك ومعالجته عبر السيرفر، يرجى الانتظار...**", parse_mode="Markdown")
    
    success, result = await send_order_to_provider(product_id, target_info, quantity=quantity, provider_key="foxreload")
    
    if not success:
        logging.error(f"Order creation failed: {result}")
        return await msg.edit_text("❌ **عذراً، فشل إنشاء الطلب في السيرفر.**\nيرجى التأكد من صحة البيانات والمحاولة لاحقاً.", parse_mode="Markdown")
        
    order_id = result.get("id") or (result.get("data", {}) if isinstance(result, dict) else {}).get("id")
    if not order_id and isinstance(result, dict):
        order_id = result.get("orderId")
        
    if order_id and isinstance(order_id, str):
        await msg.edit_text("💳 **جاري إتمام الدفع وخصم القيمة من الرصيد...**", parse_mode="Markdown")
        pay_success, pay_result = await pay_order_in_provider(order_id, "foxreload")
        
        if pay_success:
            log_user_activity(message.from_user.id, f"{service_name} (كمية: {quantity})", target_info, total_price)
            masked_target = mask_target_info(target_info)
            
            try:
                log_text = (f"🚀 **عملية شحن ناجحة ومكتملة!**\n\n📦 القسم/الخدمة: `{service_name}`\n"
                            f"🔢 الكمية: `{quantity}`\n👤 المستهدف: `{masked_target}`\n💵 التكلفة: `{total_price}$`\n🟢 الحالة: `مكتمل ودفع بنجاح ✅`")
                await bot.send_message(chat_id=ORDERS_LOG_CHANNEL, text=log_text, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Failed to send log: {e}")
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🔑 جلب الأكواد / التحقق من الحالة فوراً", callback_data=f"checkorder_{order_id}")
            builder.button(text="🔄 شراء خدمة أخرى", callback_data="telegram_services")
            builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
            builder.adjust(1)
            
            await msg.edit_text(
                f"🎉 **مبروك! تم تنفيذ طلبك بنجاح تام ⚡**\n\n"
                f"📦 **الخدمة:** `{service_name}`\n"
                f"🔢 **الكمية:** `{quantity}`\n"
                f"👤 **المستهدف:** `{target_info}`\n"
                f"💵 **التكلفة الإجمالية:** `{total_price}$`\n\n"
                f"✨ **حالة الطلب:** تم معالجته بنجاح عبر السيرفر.",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text(f"⚠️ **تم إنشاء الطلب بنجاح، ولكن تعذر إتمام الدفع التلقائي:**\n`{pay_result}`", parse_mode="Markdown")
    else:
        await msg.edit_text("✅ **تم استلام طلبك، ولكن تعذر جلب معرف الطلب للتحقق الفوري.**", parse_mode="Markdown")
        
    await state.clear()

@dp.callback_query(F.data.startswith("checkorder_"))
async def process_check_order_status(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    
    await callback.answer("🔄 جاري فحص حالة الطلب من السيرفر...", show_alert=False)
    order_data = await get_order_status_from_provider(order_id)
    
    if not order_data:
        return await callback.answer("❌ تعذر جلب بيانات الطلب حالياً، حاول مجدداً بعد قليل.", show_alert=True)
        
    status = order_data.get("status", "unknown")
    items = order_data.get("items", [])
    
    details_text = f"🔍 **تقرير حالة الطلب المباشر:**\n\n📌 **الحالة العامة:** `{status}`\n\n"
    for idx, item in enumerate(items, 1):
        item_name = item.get("name", "خدمة رقمية")
        item_status = item.get("status", "processing")
        external_data = item.get("externalData") or item.get("external_data") or "جاري إصدار الأكواد من السيرفر..."
        
        details_text += (
            f"*{idx}. {item_name}*\n"
            f"🔹 *الحالة الفرعية:* `{item_status}`\n"
            f"🔑 *الأكواد / البيانات المستلمة:* `{external_data}`\n\n"
        )
        
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 تحديث الحالة والأكواد", callback_data=f"checkorder_{order_id}")
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(details_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("عذراً، للمشرفين فقط.", show_alert=True)
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_refresh")
async def process_admin_refresh(callback: types.CallbackQuery):
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_apis_menu")
async def admin_apis_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("عذراً، للمشرفين فقط.", show_alert=True)
    
    providers = get_all_providers()
    builder = InlineKeyboardBuilder()
    for p_key, p_name in providers:
        builder.button(text=f"💰 رصيد: {p_name}", callback_data=f"api_bal_{p_key}")
        builder.button(text=f"🔑 تغيير مفتاح: {p_name}", callback_data=f"api_edit_{p_key}")
    
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🌐 **قسم إدارة API المواقع المرتبطة:**\n\nاختر الموقع المطلوب للفحص أو التحديث:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("api_bal_"))
async def process_check_api_balance(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    provider_key = callback.data.split("_")[2]
    await callback.answer("⏳ جاري استعلام الرصيد...", show_alert=False)
    balance_info = await check_provider_balance(provider_key)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 تحديث الفحص", callback_data=f"api_bal_{provider_key}")
    builder.button(text="🔙 عودة للمواقع", callback_data="admin_apis_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(f"💰 **رصيد الموقع الحالي:**\n\n`{balance_info}`", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("api_edit_"))
async def process_edit_api_key(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    provider_key = callback.data.split("_")[2]
    config = get_provider_config(provider_key)
    await state.update_data(editing_provider=provider_key)
    await state.set_state(BotStates.waiting_for_new_api_key)
    
    await callback.message.answer(
        f"🔑 **تحديث مفتاح الحساب لـ ({config['name']}):**\n\nأرسل مفتاح الـ API الجديد في رسالة الآن:",
        parse_mode="Markdown"
    )

@dp.message(BotStates.waiting_for_new_api_key)
async def save_new_api_key(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    new_key = message.text.strip()
    data = await state.get_data()
    provider_key = data.get("editing_provider")
    
    update_provider_api_key(provider_key, new_key)
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 إدارة API المواقع", callback_data="admin_apis_menu")
    builder.adjust(1)
    
    await message.answer("✅ **تم تحديث مفتاح الـ API بنجاح!**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_manage_pinned")
async def admin_manage_pinned_menu(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("عذراً، للمشرفين فقط.", show_alert=True)
    
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    for p_id, p_name, p_price, _ in pinned:
        builder.button(text=f"✏️ تعديل سعر: {p_name} ({p_price}$)", callback_data=f"editprice_{p_id}")
        builder.button(text=f"❌ إزالة القسم", callback_data=f"unpin_{p_id}")
        
    builder.button(text="🔍 بحث عن قسم/منتج وتثبيته", callback_data="admin_search_start")
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    
    text = "📌 **إدارة الأقسام والأسعار المخصصة للمستخدمين:**"
    if not pinned:
        text += "\n\n(لا توجد أقسام مثبتة حالياً)"
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("editprice_"))
async def process_edit_product_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    p_id = callback.data.split("_")[1]
    await state.update_data(editing_product_id=p_id)
    await state.set_state(BotStates.waiting_for_custom_price)
    await callback.message.answer("💵 **أدخل السعر الجديد لهذا القسم أو المنتج:**", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_custom_price)
async def save_custom_product_price(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        new_price = float(message.text.strip())
        data = await state.get_data()
        p_id = data.get("editing_product_id")
        
        pinned = get_pinned_products()
        target_prod = next((p for p in pinned if p[0] == p_id), None)
        
        if target_prod:
            pin_product(target_prod[0], target_prod[1], new_price, target_prod[3])
            await state.clear()
            await message.answer(f"✅ **تم تحديث سعر القسم/المنتج ({target_prod[1]}) ليصبح `{new_price}$` بنجاح!**", parse_mode="Markdown")
        else:
            await message.answer("❌ حدث خطأ، لم يتم العثور على المنتج المحدد.")
            await state.clear()
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً أو عشرياً للسعر:")

@dp.callback_query(F.data == "admin_search_start")
async def admin_search_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(BotStates.admin_searching_product)
    await callback.message.answer("🔍 **أدخل كلمة البحث عن المنتج في السيرفر** (مثلاً: `telegram-stars`, `telegram-premium`):", parse_mode="Markdown")

@dp.message(BotStates.admin_searching_product)
async def admin_process_search(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    query = message.text.strip()
    await message.answer(f"⏳ جاري البحث عن `{query}`...")
    
    results = await search_products_from_provider(query)
    if not results:
        return await message.answer("❌ لم يتم العثور على أي منتج يطابق بحثك. حاول بكلمة أخرى:")
        
    builder = InlineKeyboardBuilder()
    for item in results[:10]:
        item_id = str(item.get("id"))
        item_name = str(item.get("name", "منتج"))
        price = float(item.get("bestOfferPrice") or item.get("price") or item.get("retail_price") or 0.0)
        
        # 🟢 استخدام معرف المنتج المباشر لتلافي مشكلة صلاحية الذاكرة المؤقتة نهائياً
        callback_data = f"pinid_{item_id}"
        builder.button(text=f"📌 تثبيت كقسم: {item_name} ({price}$)", callback_data=callback_data)
        
    builder.button(text="🔙 عودة", callback_data="admin_manage_pinned")
    builder.adjust(1)
    
    await message.answer("🔎 **نتائج البحث المطابقة (اضغط للتثبيت الفوري):**", reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("pinid_"))
async def process_pin_direct(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    p_id = callback.data.split("_")[1]
    
    await callback.answer("⏳ جاري جلب بيانات المنتج وتثبيته...", show_alert=False)
    product_data = await get_product_details_from_provider(p_id)
    
    if not product_data:
        return await callback.answer("❌ تعذر جلب تفاصيل المنتج من السيرفر.", show_alert=True)
        
    p_name = str(product_data.get("name", "خدمة"))
    price = float(product_data.get("bestOfferPrice") or product_data.get("price") or product_data.get("retail_price") or 0.0)
    description = str(product_data.get("description") or "لا توجد تفاصيل.")
    
    pin_product(p_id, p_name, price, description)
    await callback.answer("✅ تم تثبيت القسم والمنتج بنجاح تام!", show_alert=True)
    
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    for pid, pname, pval, _ in pinned:
        builder.button(text=f"✏️ تعديل سعر: {pname} ({pval}$)", callback_data=f"editprice_{pid}")
        builder.button(text=f"❌ إزالة القسم", callback_data=f"unpin_{pid}")
    builder.button(text="🔍 بحث عن قسم وتثبيته", callback_data="admin_search_start")
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    
    await callback.message.edit_text("📌 **قائمة الأقسام والمنتجات المثبتة وأسعارها:**", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("unpin_"))
async def process_unpin_product(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    p_id = callback.data.split("_")[1]
    unpin_product(p_id)
    await callback.answer("🗑️ تمت إزالة القسم.", show_alert=True)
    
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    for pid, pname, pval, _ in pinned:
        builder.button(text=f"✏️ تعديل سعر: {pname} ({pval}$)", callback_data=f"editprice_{pid}")
        builder.button(text=f"❌ إزالة القسم", callback_data=f"unpin_{pid}")
    builder.button(text="🔍 بحث عن قسم وتثبيته", callback_data="admin_search_start")
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    
    await callback.message.edit_text("📌 **قائمة الأقسام والمنتجات المثبتة وأسعارها:**", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_edit_margin")
async def process_edit_margin(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(BotStates.waiting_for_new_margin)
    current = get_profit_margin()
    await callback.message.answer(f"📈 هامش الربح الحالي: `{current}%`\nأدخل النسبة الجديدة:", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_new_margin)
async def save_new_margin(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        new_margin = float(message.text.strip())
        set_profit_margin(new_margin)
        await state.clear()
        await message.answer(f"✅ تم تحديث هامش الربح ليصبح: `{new_margin}%`", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً أو عشرياً:")

@dp.callback_query(F.data == "admin_manage_balance")
async def admin_manage_balance_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ إضافة رصيد لمستخدم", callback_data="bal_op_add")
    builder.button(text="➖ خصم رصيد من مستخدم", callback_data="bal_op_sub")
    builder.button(text="🔙 عودة لوحة الأدمن", callback_data="admin_panel")
    builder.adjust(1)
    await callback.message.edit_text("💵 **إدارة أرصدة العملاء:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bal_op_"))
async def admin_ask_user(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    op = callback.data.split("_")[2]
    await state.update_data(balance_op=op)
    await state.set_state(BotStates.admin_get_user)
    op_text = "إضافة رصيد إلى" if op == "add" else "خصم رصيد من"
    await callback.message.answer(f"👤 **{op_text} عميل:**\nأدخل معرف المستخدم (User ID) أو الإيميل:", parse_mode="Markdown")

@dp.message(BotStates.admin_get_user)
async def admin_receive_user(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    user = find_user_by_identifier(message.text.strip())
    if not user:
        return await message.answer("❌ لم يتم العثور على المستخدم. حاول مجدداً:")
    await state.update_data(target_user_id=user[0])
    await state.set_state(BotStates.admin_get_amount)
    await message.answer(f"✅ المستخدم: `{user[1]}` (الرصيد: `{user[2]}$`)\nأدخل المبلغ المراد:", parse_mode="Markdown")

@dp.message(BotStates.admin_get_amount)
async def admin_receive_amount(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        update_user_balance(data.get("target_user_id"), amount, data.get("balance_op"))
        await state.clear()
        await message.answer("✅ تم تحديث رصيد المستخدم بنجاح!", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ قيمة غير صالحة. أدخل رقماً صحيحاً للمبلغ:")

async def main():
    init_db()
    logging.info("Bot fully operational with fixed direct ID pinning, sections, and FoxReload API.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
