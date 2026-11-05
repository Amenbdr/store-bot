from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from database import get_total_users_balances, get_total_consumption, get_profit_margin

async def show_admin_panel(callback: types.CallbackQuery, total_users: int):
    total_balances = get_total_users_balances()
    total_consumption = get_total_consumption()
    current_margin = get_profit_margin()
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🌐 إدارة API المواقع والرصيد", callback_data="admin_apis_menu")
    builder.button(text="📌 إدارة وتثبيت المنتجات", callback_data="admin_manage_pinned")
    builder.button(text="💵 إدارة أرصدة المستخدمين", callback_data="admin_manage_balance")
    builder.button(text="📈 تعديل هامش الربح", callback_data="admin_edit_margin")
    builder.button(text="🔄 تحديث الإحصائيات", callback_data="admin_refresh")
    builder.button(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_menu")
    
    builder.adjust(1, 1, 2, 1, 1)
    
    admin_text = (
        "⚙️ **لوحة تحكم المشرف (الإدارة العامة)**\n\n"
        f"👥 **إجمالي المستخدمين:** `{total_users}` عميل\n"
        f"💰 **إجمالي أرصدة العملاء:** `{total_balances:.2f}$`\n"
        f"💸 **إجمالي استهلاك الطلبات:** `{total_consumption:.2f}$`\n"
        f"📈 **هامش الربح الحالي:** `{current_margin}%`\n\n"
        "اختر الإجراء المطلوب من القائمة أدناه:"
    )
    
    await callback.message.edit_text(admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
