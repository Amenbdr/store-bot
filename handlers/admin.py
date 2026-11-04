from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
from database import db

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    users_count = db.get_all_users_count()
    servers = db.get_custom_servers()
    
    text = (
        f"👑 **لوحة تحكم المشرف**\n\n"
        f"👥 إجمالي المستخدمين: `{users_count}`\n"
        f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
        f"اختر القسم المطلوب من الأزرار أدناه:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("⚙️ إدارة السيرفرات وهوامش الربح", callback_data="admin_servers"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")
    )
    await message.reply(text, reply_markup=kb, parse_mode="Markdown")

async def admin_panel_handler(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌ عذراً، هذا الأمر للمشرفين فقط.", show_alert=True)
    
    await call.answer()
    users_count = db.get_all_users_count()
    servers = db.get_custom_servers()
    
    text = (
        f"👑 **لوحة تحكم المشرف**\n\n"
        f"👥 إجمالي المستخدمين: `{users_count}`\n"
        f"⚙️ السيرفرات النشطة: `{len(servers)}`\n\n"
        f"اختر القسم المطلوب من الأزرار أدناه:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("⚙️ إدارة السيرفرات وهوامش الربح", callback_data="admin_servers"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

async def admin_servers_handler(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("❌ غير مسموح.", show_alert=True)
    
    await call.answer()
    servers = db.get_custom_servers()
    kb = InlineKeyboardMarkup(row_width=1)
    
    text = "⚙️ **إدارة السيرفرات وجلبها:**\n\nالسيرفرات المتوفرة حالياً في قاعدة البيانات:"
    if servers:
        for server in servers:
            text += f"\n- {server['server_name']} (الهامش: {server['margin_value']}$)"
    else:
        text += "\n❌ لا توجد سيرفرات مضافة حالياً!"
        
    kb.add(InlineKeyboardButton("🔙 عودة لوحة التحكم", callback_data="admin_panel"))
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_command, commands=['admin'])
    dp.register_callback_query_handler(admin_panel_handler, lambda c: c.data == "admin_panel")
    dp.register_callback_query_handler(admin_servers_handler, lambda c: c.data == "admin_servers")
