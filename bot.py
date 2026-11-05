import os
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

from database import (
    init_db, get_user, save_user_credentials, 
    get_total_users_count, find_user_by_identifier, 
    update_user_balance, log_user_activity, get_user_logs
)
from admin_panel import show_admin_panel
from keyboards import (
    get_main_menu_keyboard, get_back_to_menu_keyboard, 
    get_order_check_keyboard, get_confirmation_keyboard
)
from api_services import (
    get_pinned_products, pin_product, unpin_product, search_products_from_provider,
    get_product_details_from_provider, send_order_to_provider, pay_order_in_provider,
    get_order_status_from_provider, get_all_providers, check_provider_balance, 
    update_provider_api_key, get_provider_config
)

TELEGRAM_BOT_TOKEN = "5418318795:AAF5TJs6tg-Z2TzBMbrMK2fogKOAaICv3pA"
REQUIRED_CHANNEL = "@SIM_NUMBERS"          
ORDERS_LOG_CHANNEL = "@SPEDERCH"           
ADMIN_ID = 5396793642                      
OWNER_USERNAME = "DF00D"                   

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class BotStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_target = State()
    waiting_for_quantity = State()
    waiting_for_custom_price = State()
    waiting_for_order_id = State()
    admin_get_user = State()
    admin_get_amount = State()
    waiting_for_new_api_key = State()
    admin_searching_product = State()

def mask_target_info(info: str) -> str:
    info = str(info).strip()
    if info.isdigit():
        if len(info) > 6: return info[:3] + "****" + info[-3:]
        return "***" + info[-2:] if len(info) > 2 else "****"
    else:
        if len(info) > 4: return info[:3] + "****" + info[-2:]
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
        return await message.answer("⚠️ **يجب عليك الاشتراك في القناة أولاً!**", reply_markup=builder.as_markup(), parse_mode="Markdown")
    
    user_data = get_user(user_id)
    if user_data and user_data[0] and str(user_data[0]).endswith("@gmail.com"):
        await show_main_menu(message)
    else:
        await state.set_state(BotStates.waiting_for_email)
        await message.answer("⚠️ **مرحباً بك! يرجى تسجيل حسابك لمرة واحدة.**\n\n📧 **أدخل بريدك الإلكتروني (ينتهي بـ `@gmail.com`):**", parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.delete()
        user_data = get_user(user_id)
        if user_data and user_data[0] and str(user_data[0]).endswith("@gmail.com"):
            await show_main_menu(callback)
        else:
            await state.set_state(BotStates.waiting_for_email)
            await callback.message.answer("⚠️ **أدخل بريدك الإلكتروني (ينتهي بـ `@gmail.com`):**", parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.message(BotStates.waiting_for_email)
async def process_user_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not email.endswith("@gmail.com"):
        return await message.answer("❌ **يجب أن ينتهي البريد بـ `@gmail.com`. حاول مجدداً:**", parse_mode="Markdown")
    await state.update_data(email=email)
    await state.set_state(BotStates.waiting_for_password)
    await message.answer("🔑 **أدخل كلمة المرور الخاصة بحسابك:**", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_password)
async def process_user_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 4:
        return await message.answer("❌ كلمة المرور قصيرة جداً. أدخل كلمة مرور صالحة:")
    data = await state.get_data()
    save_user_credentials(message.from_user.id, message.from_user.username or "No", data.get("email"), password)
    await state.clear()
    await message.answer("✅ **تم التسجيل بنجاح!**", parse_mode="Markdown")
    await show_main_menu(message)

async def show_main_menu(event: types.Message | types.CallbackQuery):
    user = event.from_user
    user_data = get_user(user.id)
    email = user_data[0] if user_data else "غير مسجل"
    is_admin = bool(user_data[3]) if user_data else False
    balance = user_data[4] if user_data else 0.0
    
    text = (f"مرحباً بك، **{user.first_name}** 👋\n\n🆔 **الآيدي:** `{user.id}`\n📧 **الإيميل:** `{email}`\n💰 **رصيدك الحالي:** `{balance}$`\n\nاختر القسم المطلوب:")
    markup = get_main_menu_keyboard(is_admin)
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_menu")
async def process_back_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)

@dp.callback_query(F.data == "check_order_menu")
async def process_check_order_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_order_id)
    await callback.message.edit_text("🔄 **متابعة حالة الطلب**\nالرجاء إرسال معرف الطلب (Order ID):", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_order_id)
async def process_user_order_id_input(message: types.Message, state: FSMContext):
    order_id = message.text.strip()
    await state.clear()
    msg = await message.answer("⏳ **جاري فحص حالة الطلب...**", parse_mode="Markdown")
    order_data = await get_order_status_from_provider(order_id)
    if not order_data:
        return await msg.edit_text("❌ **لم يتم العثور على طلب بهذا المعرف.**", reply_markup=get_back_to_menu_keyboard())
    
    status = order_data.get("status", "unknown")
    items = order_data.get("items", [])
    details_text = f"🔍 **نتيجة فحص الطلب (`{order_id}`):**\n\n📌 **الحالة:** `{status}`\n\n"
    for idx, item in enumerate(items, 1):
        details_text += f"*{idx}. {item.get('name', 'خدمة')}*\n🔹 *الحالة:* `{item.get('status', 'processing')}`\n🔑 *البيانات:* `{item.get('externalData') or 'قيد المعالجة'}`\n\n"
    await msg.edit_text(details_text, reply_markup=get_order_check_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("checkorder_"))
async def process_check_order_status(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    await callback.answer("🔄 جاري الفحص...", show_alert=False)
    order_data = await get_order_status_from_provider(order_id)
    if not order_data:
        return await callback.answer("❌ تعذر جلب بيانات الطلب.", show_alert=True)
    
    status = order_data.get("status", "unknown")
    items = order_data.get("items", [])
    details_text = f"🔍 **تقرير الطلب (`{order_id}`):**\n\n📌 **الحالة العامة:** `{status}`\n\n"
    for idx, item in enumerate(items, 1):
        details_text += f"*{idx}. {item.get('name', 'خدمة')}*\n🔹 *الحالة:* `{item.get('status', 'processing')}`\n🔑 *البيانات:* `{item.get('externalData') or 'قيد المعالجة'}`\n\n"
    await callback.message.edit_text(details_text, reply_markup=get_order_check_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "my_orders_log")
async def show_user_activity_history(callback: types.CallbackQuery):
    logs = get_user_logs(callback.from_user.id)
    if not logs:
        return await callback.message.edit_text("ليس لديك أي عمليات سابقة.", reply_markup=get_back_to_menu_keyboard())
    log_text = "📋 **آخر عمليات الشحن:**\n\n"
    for idx, (service, target, cost, created_at) in enumerate(logs, 1):
        log_text += f"*{idx}.* {service} | `{target}` | `{cost}$`\n"
    await callback.message.edit_text(log_text, reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "telegram_services")
async def process_telegram_services(callback: types.CallbackQuery):
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    if pinned:
        for p_id, p_name, p_price, _ in pinned:
            builder.button(text=f"🔹 {p_name} — 💰 {p_price}$", callback_data=f"viewprod_{p_id}")
    else:
        builder.button(text="⚠️ لا توجد خدمات مثبتة", callback_data="none")
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    await callback.message.edit_text("⭐ **اختر الخدمة المطلوبة:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("viewprod_"))
async def process_view_product_details(callback: types.CallbackQuery, state: FSMContext):
    p_id = callback.data.split("_")[1]
    await callback.answer("⏳ جاري جلب التفاصيل...", show_alert=False)
    pinned = get_pinned_products()
    selected_product = next((p for p in pinned if str(p[0]) == str(p_id)), None)
    if not selected_product:
        return await callback.answer("❌ المنتج غير متوفر.", show_alert=True)
        
    p_name, p_price = selected_product[1], selected_product[2]
    is_stars = "star" in p_name.lower() or "نجم" in p_name.lower()
    await state.update_data(product_id=p_id, service_name=p_name, service_price=p_price, is_stars=is_stars)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 شراء الآن", callback_data="confirm_buy_step")
    builder.button(text="🔙 العودة للأقسام", callback_data="telegram_services")
    builder.adjust(1)
    await callback.message.edit_text(f"📦 **القسم:** `{p_name}`\n💰 **سعر الوحدة:** `{p_price}$`\n\nاضغط الشراء للمتابعة:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "confirm_buy_step")
async def process_confirm_buy(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("is_stars", False):
        await state.set_state(BotStates.waiting_for_quantity)
        await callback.message.edit_text(
            "⭐ **تحديد كمية النجوم:**\n\n"
            "أرسل الآن عدد النجوم المطلوب (اكتب الرقم بنفسك):\n"
            "📌 *(الحد الأدنى: 50 نجمة | الحد الأقصى: 1,000,000 نجمة)*",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await state.update_data(quantity=1)
        await state.set_state(BotStates.waiting_for_target)
        await callback.message.edit_text("📥 **أدخل معرف المستخدم (User ID) أو اليوزر المراد الشحن له:**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_quantity)
async def process_star_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 50 or qty > 1000000:
            return await message.answer(
                "❌ **عذراً، العدد المدخل غير مسموح به!**\n\n"
                "يرجى إدخال عدد صحيح بين **50** و **1,000,000** نجمة:",
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode="Markdown"
            )
            
        await state.update_data(quantity=qty)
        await state.set_state(BotStates.waiting_for_target)
        await message.answer(
            f"✅ **تم تحديد الكمية:** `{qty} نجمة`\n\n"
            "📥 **أدخل الآن معرف المستخدم (User ID) أو اليوزر المطلوب الشحن له:**",
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ **قيمة غير صالحة!** يرجى إدخال رقماً صحيحاً فقط (مثلاً: `150` أو `500`):")

@dp.message(BotStates.waiting_for_target)
async def process_target_id(message: types.Message, state: FSMContext):
    target_info = message.text.strip()
    await state.update_data(target_info=target_info)
    data = await state.get_data()
    
    service_name, base_price, quantity = data.get("service_name"), data.get("service_price"), data.get("quantity", 1)
    total_price = round(base_price * quantity, 4) if quantity > 1 else base_price
    await state.update_data(total_price=total_price)
    
    user_data = get_user(message.from_user.id)
    user_balance = float(user_data[4]) if user_data else 0.0
    
    if user_balance < total_price:
        await state.clear()
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 شحن الرصيد", url=f"https://t.me/{OWNER_USERNAME}")
        builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
        builder.adjust(1)
        return await message.answer(f"❌ **رصيدك غير كافٍ!**\n💰 رصيدك: `{user_balance}$`\n💵 المطلوب: `{total_price}$`", reply_markup=builder.as_markup(), parse_mode="Markdown")
    
    await message.answer(
        f"🧾 **تأكيد الفاتورة:**\n\n📦 **الخدمة:** `{service_name}`\n🔢 **الكمية:** `{quantity}`\n👤 **المستهدف:** `{target_info}`\n💰 **الإجمالي:** `{total_price}$`\n\n⚠️ **متأكد من الشراء؟**",
        reply_markup=get_confirmation_keyboard(), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "confirm_final_pay")
async def execute_purchase_final(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data or not data.get("product_id"):
        return await callback.message.edit_text("❌ انتهت الجلسة.")
        
    product_id, target_info, quantity = data.get("product_id"), data.get("target_info"), data.get("quantity", 1)
    service_name, total_price = data.get("service_name"), data.get("total_price")
    
    update_user_balance(callback.from_user.id, total_price, "sub")
    await callback.message.edit_text("⏳ **جاري إرسال الطلب للسيرفر والدفع...**", parse_mode="Markdown")
    
    success, result = await send_order_to_provider(product_id, target_info, quantity=quantity, provider_key="foxreload")
    if not success:
        update_user_balance(callback.from_user.id, total_price, "add")
        return await callback.message.edit_text("❌ **فشل الطلب وتم استرداد رصيدك.**")
        
    order_id = result.get("id") or (result.get("data", {}) if isinstance(result, dict) else {}).get("id") or result.get("orderId")
    if order_id:
        pay_success, _ = await pay_order_in_provider(str(order_id), "foxreload")
        if pay_success:
            log_user_activity(callback.from_user.id, f"{service_name} (كمية: {quantity})", target_info, total_price)
            builder = InlineKeyboardBuilder()
            builder.button(text="🔑 تحقق من الحالة", callback_data=f"checkorder_{order_id}")
            builder.button(text="🔙 الرئيسية", callback_data="back_to_menu")
            await callback.message.edit_text(f"🎉 **تم تنفيذ طلبك بنجاح وخصم `{total_price}$`!**\n📦 **معرف الطلب:** `{order_id}`", reply_markup=builder.as_markup(), parse_mode="Markdown")
        else:
            await callback.message.edit_text("⚠️ **الطلب معلق، تواصل مع الدعم.**")
    else:
        await callback.message.edit_text("✅ **تم استلام الطلب بنجاح.**")
    await state.clear()

@dp.callback_query(F.data == "cancel_final_pay")
async def cancel_purchase_final(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ **تم إلغاء الطلب.**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

# --- لوحة التحكم الخاصة بالأدمن ---
@dp.callback_query(F.data == "admin_panel")
async def process_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_refresh")
async def process_admin_refresh(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    await show_admin_panel(callback, get_total_users_count())

@dp.callback_query(F.data == "admin_apis_menu")
async def admin_apis_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    providers = get_all_providers()
    builder = InlineKeyboardBuilder()
    for p_key, p_name in providers:
        builder.button(text=f"💰 رصيد: {p_name}", callback_data=f"api_bal_{p_key}")
        builder.button(text=f"🔑 مفتاح: {p_name}", callback_data=f"api_edit_{p_key}")
    builder.button(text="🔙 عودة", callback_data="admin_panel")
    builder.adjust(1)
    await callback.message.edit_text("🌐 **إدارة الـ API:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("api_bal_"))
async def process_check_api_balance(callback: types.CallbackQuery):
    provider_key = callback.data.split("_")[2]
    balance_info = await check_provider_balance(provider_key)
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 عودة", callback_data="admin_apis_menu")
    await callback.message.edit_text(f"💰 **الرصيد:**\n`{balance_info}`", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("api_edit_"))
async def process_edit_api_key(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(editing_provider=callback.data.split("_")[2])
    await state.set_state(BotStates.waiting_for_new_api_key)
    await callback.message.answer("🔑 **أرسل مفتاح الـ API الجديد:**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_new_api_key)
async def save_new_api_key(message: types.Message, state: FSMContext):
    data = await state.get_data()
    update_provider_api_key(data.get("editing_provider"), message.text.strip())
    await state.clear()
    await message.answer("✅ **تم التحديث بنجاح!**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_manage_pinned")
async def admin_manage_pinned_menu(callback: types.CallbackQuery):
    pinned = get_pinned_products()
    builder = InlineKeyboardBuilder()
    for p_id, p_name, p_price, _ in pinned:
        builder.button(text=f"✏️ تعديل: {str(p_name)[:12]}", callback_data=f"editprice_{p_id}")
        builder.button(text="❌ إزالة", callback_data=f"unpin_{p_id}")
    builder.button(text="🔍 بحث وتثبيت قسم", callback_data="admin_search_start")
    builder.button(text="🔙 عودة", callback_data="admin_panel")
    builder.adjust(2, 2, 1, 1)
    await callback.message.edit_text("📌 **الأقسام المثبتة:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("editprice_"))
async def process_edit_product_price(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(editing_product_id=callback.data.split("_")[1])
    await state.set_state(BotStates.waiting_for_custom_price)
    await callback.message.answer("💵 **أدخل السعر الجديد (رقم فقط):**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_custom_price)
async def save_custom_product_price(message: types.Message, state: FSMContext):
    try:
        new_price = float(message.text.strip())
        data = await state.get_data()
        p_id = data.get("editing_product_id")
        pinned = get_pinned_products()
        target_prod = next((p for p in pinned if str(p[0]) == str(p_id)), None)
        if target_prod:
            pin_product(target_prod[0], target_prod[1], new_price, target_prod[3])
            await message.answer(f"✅ تم تحديث السعر إلى `{new_price}$`!", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")
        else:
            await message.answer("❌ لم يُعثر على القسم.", reply_markup=get_back_to_menu_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً فقط:")

@dp.callback_query(F.data == "admin_search_start")
async def admin_search_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.admin_searching_product)
    await callback.message.answer("🔍 **أدخل كلمة البحث (مثلاً telegram-stars):**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.admin_searching_product)
async def admin_process_search(message: types.Message, state: FSMContext):
    results = await search_products_from_provider(message.text.strip())
    if not results:
        return await message.answer("❌ لم يتم العثور على نتائج.", reply_markup=get_back_to_menu_keyboard())
    builder = InlineKeyboardBuilder()
    for item in results[:10]:
        builder.button(text=f"📌 تثبيت: {str(item.get('name'))[:20]}", callback_data=f"pin|{item.get('id')}")
    builder.button(text="🔙 عودة", callback_data="admin_manage_pinned")
    builder.adjust(1)
    await message.answer("🔎 **اختر للتثبيت:**", reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("pin|"))
async def process_pin_direct(callback: types.CallbackQuery):
    p_id = callback.data.split("|")[1]
    product_data = await get_product_details_from_provider(p_id)
    if not product_data:
        return await callback.answer("❌ فشل الجلب.", show_alert=True)
    pin_product(p_id, str(product_data.get("name")), float(product_data.get("bestOfferPrice") or 0.0), str(product_data.get("description") or ""))
    await callback.answer("✅ تم التثبيت بنجاح!", show_alert=True)
    await admin_manage_pinned_menu(callback)

@dp.callback_query(F.data.startswith("unpin_"))
async def process_unpin_product(callback: types.CallbackQuery):
    unpin_product(callback.data.split("_")[1])
    await callback.answer("🗑️ تمت الإزالة.", show_alert=True)
    await admin_manage_pinned_menu(callback)

@dp.callback_query(F.data == "admin_manage_balance")
async def admin_manage_balance_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ إضافة رصيد", callback_data="bal_op_add")
    builder.button(text="➖ خصم رصيد", callback_data="bal_op_sub")
    builder.button(text="🔙 عودة", callback_data="admin_panel")
    builder.adjust(1)
    await callback.message.edit_text("💵 **إدارة الأرصدة:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bal_op_"))
async def admin_ask_user(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(balance_op=callback.data.split("_")[2])
    await state.set_state(BotStates.admin_get_user)
    await callback.message.answer("👤 **أدخل معرف المستخدم (User ID):**", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.admin_get_user)
async def admin_receive_user(message: types.Message, state: FSMContext):
    user = find_user_by_identifier(message.text.strip())
    if not user:
        return await message.answer("❌ لم يُعثر على المستخدم.", reply_markup=get_back_to_menu_keyboard())
    await state.update_data(target_user_id=user[0])
    await state.set_state(BotStates.admin_get_amount)
    await message.answer(f"✅ المستخدم: `{user[1]}` (رصيده: `{user[2]}$`)\nأدخل المبلغ:", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.admin_get_amount)
async def admin_receive_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        update_user_balance(data.get("target_user_id"), amount, data.get("balance_op"))
        await state.clear()
        await message.answer("✅ تم تحديث الرصيد بنجاح!", reply_markup=get_back_to_menu_keyboard(), parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً للمبلغ:")

# تشغيل خادم الويب الوهمي لتوافق Render
async def handle_ping(request):
    return web.Response(text="Bot is running perfectly on Render!")

async def main():
    init_db()
    logging.info("Bot fully operational.")
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
