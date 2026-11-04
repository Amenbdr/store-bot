from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from config import CHANNEL_ID, CHANNEL_LINK, ADMIN_IDS
from database import db
from utils.keyboards import main_customer_keyboard, admin_main_keyboard, force_sub_keyboard

async def check_channel_sub(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True

# 1. معالج رسالة /start
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish() # تنظيف أي حالة سابقة
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.username, message.from_user.full_name)
    
    is_subscribed = await check_channel_sub(message.bot, user_id)
    if not is_subscribed:
        return await message.answer(
            "⚠️ **عذراً عزيزي العميل!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية للاستفادة من الخدمات.",
            reply_markup=force_sub_keyboard(CHANNEL_LINK),
            parse_mode="Markdown"
        )

    is_admin = user_id in ADMIN_IDS

    # أولاً: نرسل لوحة العملاء (ستصل للجميع وللأدمن أيضاً)
    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0
    customer_text = (
        f"أهلاً بك عزيزي العميل: **{message.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    await message.answer(customer_text, reply_markup=main_customer_keyboard(is_admin=is_admin), parse_mode="Markdown")

    # ثانياً: إذا كان مشرفاً، نرسل له لوحة التحكم مباشرة في رسالة أخرى تحتها
    if is_admin:
        total_users = db.get_all_users_count()
        servers = db.get_custom_servers()
        admin_text = (
            f"👑 **مرحباً بك يا أستاذنا (مشرف البوت)**\n\n"
            f"👥 إجمالي العملاء: `{total_users}`\n"
            f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
            f"👇 **لوحة تحكم الإدارة السريعة:**"
        )
        await message.answer(admin_text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")

# 2. معالج زر "تحقق من الاشتراك"
async def check_sub_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = call.from_user.id
    is_subscribed = await check_channel_sub(call.bot, user_id)
    
    if is_subscribed:
        await call.message.delete()
        is_admin = user_id in ADMIN_IDS
        
        # نرسل رسالة العميل أولاً
        user_data = db.get_user(user_id)
        balance = user_data['balance'] if user_data else 0.0
        customer_text = (
            f"أهلاً بك عزيزي العميل: **{call.from_user.first_name}**\n"
            f"🆔 معرف حسابك: `{user_id}`\n"
            f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
            f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
        )
        await call.message.answer(customer_text, reply_markup=main_customer_keyboard(is_admin=is_admin), parse_mode="Markdown")

        # ونرسل رسالة المشرف معها
        if is_admin:
            total_users = db.get_all_users_count()
            servers = db.get_custom_servers()
            admin_text = (
                f"👑 **مرحباً بك يا أستاذنا (مشرف البوت)**\n\n"
                f"👥 إجمالي العملاء: `{total_users}`\n"
                f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
                f"👇 **لوحة تحكم الإدارة السريعة:**"
            )
            await call.message.answer(admin_text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")
    else:
        await call.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

# 3. معالج زر "القائمة الرئيسية" عند العودة من الأقسام
async def back_main_handler(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0
    text = (
        f"أهلاً بك عزيزي العميل: **{call.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    # تعديل الرسالة الحالية لتصبح القائمة الرئيسية للعملاء (وبها زر الدخول للوحة التحكم)
    await call.message.edit_text(text, reply_markup=main_customer_keyboard(is_admin=is_admin), parse_mode="Markdown")

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_callback_query_handler(check_sub_callback, lambda c: c.data == 'check_subscription', state='*')
    dp.register_callback_query_handler(back_main_handler, lambda c: c.data == 'back_main', state='*')
