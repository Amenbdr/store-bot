from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def force_sub_keyboard(channel_link: str):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📢 اشترك في القناة الرسمية أولاً", url=channel_link),
        InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
    )
    return kb

def main_customer_keyboard(is_admin: bool = False):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📱 قسم الأرقام الوهمية", callback_data="section_numbers"),
        InlineKeyboardButton("🎮 قسم شحن الألعاب", callback_data="section_games")
    )
    kb.add(
        InlineKeyboardButton("💳 شحن الحساب (Binance)", callback_data="section_deposit"),
        InlineKeyboardButton("👤 حسابي الشخصي", callback_data="section_profile")
    )
    kb.add(InlineKeyboardButton("💬 الدعم الفني المباشر", url="https://t.me/دعمك_هنا"))
    if is_admin:
        kb.add(InlineKeyboardButton("⚙️ لوحة تحكم الإدارة", callback_data="section_admin"))
    return kb

def admin_main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة رصيد لعميل", callback_data="admin_add_balance"),
        InlineKeyboardButton("➖ خصم رصيد من عميل", callback_data="admin_deduct_balance")
    )
    kb.add(
        InlineKeyboardButton("🖥 إدارة السيرفرات وهامش الربح", callback_data="admin_servers"),
        InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_stats")
    )
    kb.add(
        InlineKeyboardButton("📢 إذاعة لجميع العملاء", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")
    )
    return kb
