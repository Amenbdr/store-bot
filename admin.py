import aiohttp
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_profit_margin, get_total_users_balances, get_total_consumption

FOXRELOAD_API_KEY = "dmk_i5mOcfUakf7MLFFOF3VMWhpEo2btd32SoEgiLOcFBlo"

async def get_foxreload_balance():
    url = "https://public-api.foxreload.com/api/access/me/balances/"
    headers = {
        "X-API-Key": FOXRELOAD_API_KEY,
        "X-Language": "en",
        "X-Currency": "usd",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return "غير معروف"
        except Exception:
            return "خطأ في الاتصال"

async def show_admin_panel(callback_or_message, total_users):
    balance_data = await get_foxreload_balance()
    current_margin = get_profit_margin()
    total_balances = get_total_users_balances()
    total_consumption = get_total_consumption()
    
    admin_text = (
        "⚙️ **لوحة تحكم الأدمن المتقدمة (Admin Panel)**\n\n"
        f"👥 **إجمالي العملاء:** `{total_users}` مستخدم\n"
        f"💰 **إجمالي أرصدة المستخدمين:** `{total_balances}$`\n"
        f"🛒 **إجمالي الاستهلاك (الطلبات):** `{total_consumption}$`\n"
        f"📈 **هامش الربح الحالي:** `{current_margin}%`\n\n"
        f"🌐 **رصيد الموقع الحقيقي (FoxReload):**\n`{balance_data}`\n\n"
        "اختر العملية الإدارية المطلوبة:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 إدارة أرصدة العملاء (إضافة/خصم)", callback_data="admin_manage_balance")
    builder.button(text="📈 تعديل هامش الربح", callback_data="admin_edit_margin")
    builder.button(text="🔄 تحديث لوحة التحكم", callback_data="admin_refresh")
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.edit_text(admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await callback_or_message.answer(admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
