import aiohttp
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

FOXRELOAD_API_KEY = "dmk_SLDMDj7c85zyzMGiCN56JGFYsu0Dyc_cuFL9DWxcpEA"

# دالة جلب الرصيد الحقيقي من المنصة
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
                return None
        except Exception:
            return None

async def show_admin_panel(callback_or_message, total_users):
    balance_data = await get_foxreload_balance()
    
    admin_text = (
        "⚙️ **لوحة تحكم الأدمن (Admin Panel)**\n\n"
        f"👥 **إجمالي العملاء المسجلين:** `{total_users}` مستخدم\n"
        f"💰 **حالة الأرصدة في المنصة:**\n`{balance_data}`\n\n"
        "اختر العملية الإدارية المطلوبة:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 تحديث لوحة التحكم", callback_data="admin_refresh")
    builder.button(text="🔙 القائمة الرئيسية", callback_data="back_to_menu")
    builder.adjust(1)
    
    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.edit_text(admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await callback_or_message.answer(admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
