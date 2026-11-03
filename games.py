from aiogram import types
from database import add_log, modify_user_balance
import sqlite3

async def get_games_catalog_keyboard():
    """لوحة مفاتيح تفاعلية لعرض قسم شحن الألعاب والخدمات الترفيهية"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎮 شحن شدات ببجي (PUBG)", callback_data="game_pubg"),
        types.InlineKeyboardButton("🔥 شحن جواهر فري فاير (Free Fire)", callback_data="game_freefire"),
        types.InlineKeyboardButton("🎵 عملات تيك توك (TikTok Coins)", callback_data="game_tiktok"),
        types.InlineKeyboardButton("💎 شحن شدات يوفي (UC / Diamonds)", callback_data="game_other"),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_home")
    )
    return keyboard

async def games_menu_handler(query: types.CallbackQuery):
    """معالجة ضغطات أزرار الألعاب وعرض الأسعار أو خطوات الشحن"""
    data = query.data
    user_id = str(query.from_user.id)
    
    if data == "game_pubg":
        text = (
            "🎮 **شحن شدات ببجي موبايل (PUBG Mobile)**\n\n"
            "الرجاء إرسال الآيدي (Player ID) الخاص بك مع اختيار الباقة المناسبة.\n"
            "*(ملاحظة: سيتم الخصم تلقائياً من رصيدك في البوت)*\n\n"
            "🔹 60 شدة = `0.99 $`\n"
            "🔹 325 شدة = `4.99 $`\n"
            "🔹 660 شدة = `9.99 $`"
        )
        # زر لشراء الباقة أو تأكيد العملية
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("🛒 شراء باقة 60 شدة (تلقائي)", callback_data="buy_pubg_60"),
            types.InlineKeyboardButton("🔙 العودة للألعاب", callback_data="back_to_games")
        )
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await query.answer()

    elif data == "game_freefire":
        text = (
            "🔥 **شحن جواهر فري فاير (Free Fire)**\n\n"
            "اختر الباقة المراد شحنها:\n\n"
            "🔹 100 جوهرة = `1.00 $`\n"
            "🔹 310 جوهرة = `2.99 $`"
        )
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("🛒 شراء 100 جوهرة", callback_data="buy_ff_100"),
            types.InlineKeyboardButton("🔙 العودة للألعاب", callback_data="back_to_games")
        )
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await query.answer()

    elif data == "game_tiktok" or data == "game_other":
        await query.message.answer("⏳ هذا القسم قيد التحديث وسيتم ربطه بالـ API قريباً.", parse_mode="Markdown")
        await query.answer()

    elif data == "back_to_games":
        keyboard = await get_games_catalog_keyboard()
        await query.message.edit_text("🎮 **اختر اللعبة أو الخدمة الرقمية المراد شحنها:**", reply_markup=keyboard, parse_mode="Markdown")
        await query.answer()
