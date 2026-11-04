from aiogram import Dispatcher, types
from config import CHANNEL_ID, CHANNEL_LINK, ADMIN_IDS
from database import db
from utils.keyboards import main_customer_keyboard, admin_main_keyboard, force_sub_keyboard

async def check_channel_sub(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True

async def start_handler(message: types.Message):
    user_id = message.from_user.id
    db.add_user(user_id, message.from_user.username, message.from_user.full_name)
    
    is_subscribed = await check_channel_sub(message.bot, user_id)
    if not is_subscribed:
        return await message.answer(
            "⚠️ **عذراً عزيزي العميل!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية للاستفادة من الخدمات.",
            reply_markup=force_sub_keyboard(CHANNEL_LINK),
            parse_mode="Markdown"
        )

    # 1. إذا كان المستخدم مشرفاً (Admin)، نرسل له رسالة خاصة بلوحة التحكم الإدارية
    if user_id in ADMIN_IDS:
        total_users = db.get_all_users_count()
        servers = db.get_custom_servers()
        admin_text = (
            f"👑 **مرحباً بك يا أستاذنا (مشرف البوت)**\n\n"
            f"👥 إجمالي العملاء: `{total_users}`\n"
            f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
            f"👇 **لوحة تحكم الإدارة السريعة:**"
        )
        await message.answer(admin_text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")
        return  # نوقف التنفيذ هنا لكي لا تصله رسالة العميل العادية فوقها

    # 2. إذا كان مستخدماً عادياً، نرسل له لوحة العملاء كالمعتاد
    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0

    text = (
        f"أهلاً بك عزيزي العميل: **{message.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    
    await message.answer(text, reply_markup=main_customer_keyboard(is_admin=False), parse_mode="Markdown")

async def check_sub_callback(call: types.CallbackQuery):
    is_subscribed = await check_channel_sub(call.bot, call.from_user.id)
    if is_subscribed:
        await call.message.delete()
        await start_handler(call.message)
    else:
        await call.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

async def back_main_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    # إذا ضغط الأدمن زر العودة وكانت صلاحيته مفعلة
    if user_id in ADMIN_IDS:
        total_users = db.get_all_users_count()
        servers = db.get_custom_servers()
        admin_text = (
            f"👑 **لوحة تحكم الإدارة**\n\n"
            f"👥 إجمالي العملاء: `{total_users}`\n"
            f"⚙️ السيرفرات النشطة: `{len(servers)}`"
        )
        await call.message.edit_text(admin_text, reply_markup=admin_main_keyboard(), parse_mode="Markdown")
        return

    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0
    text = (
        f"أهلاً بك عزيزي العميل: **{call.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    await call.message.edit_text(text, reply_markup=main_customer_keyboard(is_admin=False), parse_mode="Markdown")

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_callback_query_handler(check_sub_callback, lambda c: c.data == 'check_subscription')
    dp.register_callback_query_handler(back_main_handler, lambda c: c.data == 'back_main')
