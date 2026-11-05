from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 إدارة API المواقع", callback_data="admin_apis_menu")
    builder.button(text="📌 إدارة الأقسام والأسعار", callback_data="admin_manage_pinned")
    builder.button(text="💵 إدارة أرصدة العملاء", callback_data="admin_manage_balance")
    builder.button(text="🔄 تحديث اللوحة", callback_data="admin_refresh")
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()

async def show_admin_panel(callback: types.CallbackQuery, total_users: int):
    text = (
        f"⚙️ **لوحة تحكم المشرف (الأدمن)**\n\n"
        f"👥 **إجمالي المستخدمين المسجلين:** `{total_users}`\n\n"
        "اختر القسم المطلوب للإدارة:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
