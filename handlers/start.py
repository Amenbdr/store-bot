from aiogram import Dispatcher, types
from config import CHANNEL_ID, CHANNEL_LINK, ADMIN_IDS
from database import db
from utils.keyboards import main_customer_keyboard, force_sub_keyboard

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

    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0

    text = (
        f"أهلاً بك عزيزي العميل: **{message.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    
    is_admin = user_id in ADMIN_IDS
    await message.answer(text, reply_markup=main_customer_keyboard(is_admin), parse_mode="Markdown")

async def check_sub_callback(call: types.CallbackQuery):
    is_subscribed = await check_channel_sub(call.bot, call.from_user.id)
    if is_subscribed:
        await call.message.delete()
        await start_handler(call.message)
    else:
        await call.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

async def back_main_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_data = db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0
    text = (
        f"أهلاً بك عزيزي العميل: **{call.from_user.first_name}**\n"
        f"🆔 معرف حسابك: `{user_id}`\n"
        f"💰 رصيدك الحالي: **{balance:.2f} $**\n\n"
        f"👇 اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    is_admin = user_id in ADMIN_IDS
    await call.message.edit_text(text, reply_markup=main_customer_keyboard(is_admin), parse_mode="Markdown")

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_callback_query_handler(check_sub_callback, lambda c: c.data == 'check_subscription')
    dp.register_callback_query_handler(back_main_handler, lambda c: c.data == 'back_main')
