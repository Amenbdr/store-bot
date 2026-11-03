from aiogram import types
from apis import SMSBowerAPI

# قائمة الدول الشاملة والمعتمدة لدى سيرفرات التفعيل
FULL_COUNTRIES_LIST = [
    (0, "🇷🇺 روسيا"), (1, "🇺🇦 أوكرانيا"), (2, "🇰🇿 كازاخستان"), (3, "🇨🇳 الصين"),
    (4, "🇵🇭 الفلبين"), (5, "🇲🇲 ميانمار"), (6, "🇮🇩 إندونيسيا"), (7, "🇲🇾 ماليزيا"),
    (8, "🇰🇪 كينيا"), (9, "🇹🇿 تنزانيا"), (10, "🇻🇳 فيتنام"), (11, "🇰🇬 قرغيزستان"),
    (12, "🇺🇸 الولايات المتحدة"), (13, "🇮🇱 إسرائيل"), (14, "🇭🇰 هونغ كونغ"), (15, "🇵🇱 بولندا"),
    (16, "🇬🇧 بريطانيا"), (17, "🇲🇬 مدغشقر"), (18, "🇨🇬 الكونغو"), (19, "🇳🇬 نيجيريا"),
    (20, "🇲🇴 ماكاو"), (21, "🇪🇬 مصر"), (22, "🇮🇳 الهند"), (23, "🇮🇪 أيرلندا"),
    (24, "🇰🇭 كامبوديا"), (25, "🇱🇦 لاوس"), (26, "🇭🇹 هايتي"), (27, "🇨🇮 ساحل العاج"),
    (28, "🇬🇲 غامبيا"), (29, "🇸🇪 السويد"), (30, "🇺🇿 أوزبكستان"), (31, "🇨🇦 كندا"),
    (32, "🇲🇦 المغرب"), (33, "🇬🇭 غانا"), (34, "🇦🇷 الارجنتين"), (35, "🇺🇿 أوزبكستان 2"),
    (36, "🇳🇱 هولندا"), (37, "🇧🇪 بلجيكا"), (38, "🇩🇪 ألمانيا"), (39, "🇱🇹 ليتوانيا"),
    (40, "🇪🇪 إستونيا"), (41, "🇦🇿 أذربيجان"), (42, "🇹🇯 طاجيكستان"), (43, "🇦🇳 أنغولا"),
    (44, "🇵🇰 باكستان"), (45, "🇧🇾 بيلاروسيا"), (46, "🇮🇶 العراق"), (47, "🇹🇷 تركيا"),
    (48, "🇷🇴 رومانيا"), (49, "🇨🇴 كولومبيا"), (50, "🇸🇦 السعودية"), (51, "🇿🇦 جنوب أفريقيا"),
    (52, "🇪🇸 إسبانيا"), (53, "🇧🇷 البرازيل"), (54, "🇲🇽 المكسيك"), (55, "🇨🇱 تشيلي"),
    (56, "🇬🇪 جورجيا"), (57, "🇦🇱 ألبانيا"), (58, "🇮🇹 إيطاليا"), (59, "🇩🇿 الجزائر"),
    (60, "🇹🇳 تونس"), (61, "🇫🇷 فرنسا"), (62, "🇦🇺 أستراليا"), (63, "🇦🇪 الإمارات"),
    (64, "🇸🇾 سوريا"), (65, "🇸🇩 السودان"), (66, "🇯🇴 الأردن"), (67, "🇱🇧 لبنان"),
    (68, "🇰🇼 الكويت"), (69, "🇴🇲 عمان"), (70, "🇶🇦 قطر"), (71, "🇧🇭 البحرين"),
    (72, "🇾🇪 اليمن"), (73, "🇵🇸 فلسطين"), (74, "🇱🇾 ليبيا"), (75, "🇸🇴 الصومال")
]

async def get_countries_pagination_keyboard(service_type: str, page: int = 1):
    """
    عرض 12 دولة في كل صفحة مع أزرار التنقل (التالي / السابق)
    """
    items_per_page = 12
    total_countries = len(FULL_COUNTRIES_LIST)
    max_pages = (total_countries + items_per_page - 1) // items_per_page

    page = max(1, min(page, max_pages))

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_countries = FULL_COUNTRIES_LIST[start_idx:end_idx]

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    # إضافة الدول (زرين في كل سطر)
    for country_id, country_name in current_countries:
        keyboard.insert(
            types.InlineKeyboardButton(
                country_name,
                callback_data=f"cnt_{service_type}_{country_id}"
            )
        )

    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"p_{service_type}_{page-1}"))
    
    # عرض الصفحة الحالية
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page} / {max_pages}", callback_data="ignore"))
    
    if page < max_pages:
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"p_{service_type}_{page+1}"))

    keyboard.row(*nav_buttons)
    keyboard.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_home"))
    
    return keyboard, f"🌍 **اختر الدولة المطلوبة (صفحة {page} من {max_pages}):**"

async def get_fake_servers_keyboard(service_code: str, country_id: int, service_name: str):
    """
    عرض السيرفرات الوهمية للمستخدم بالتنسيق المطلوب:
    (التطبيق | السعر | السيرفر) مع جلب المخزون الفعلي من الموقع
    """
    prices_data = SMSBowerAPI.get_prices_and_stock(service_code)
    
    country_str = str(country_id)
    stock_count = 0
    price = 0.50
    
    if prices_data and country_str in prices_data:
        srv_info = prices_data[country_str].get(service_code, {})
        stock_count = srv_info.get("count", 0)
        price = srv_info.get("cost", 0.50)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    if stock_count > 0:
        # التنسيق المطلوب: [التطبيق] [السعر] [رقم السيرفر والمخزون]
        keyboard.add(
            types.InlineKeyboardButton(
                f"{service_name} | 💵 {price:.2f}$ | سيرفر 1 (متوفر: {stock_count})", 
                callback_data=f"buy_srv1_{service_code}_{country_id}"
            ),
            types.InlineKeyboardButton(
                f"{service_name} | 💵 {price:.2f}$ | سيرفر 2 (متوفر: {max(1, stock_count // 2)})", 
                callback_data=f"buy_srv2_{service_code}_{country_id}"
            ),
            types.InlineKeyboardButton(
                f"{service_name} | 💵 {price:.2f}$ | سيرفر 3 (متوفر: {max(1, stock_count // 3)})", 
                callback_data=f"buy_srv3_{service_code}_{country_id}"
            )
        )
    else:
        keyboard.add(
            types.InlineKeyboardButton("❌ عذراً، المخزون غير متوفر لهذه الدولة حالياً", callback_data="ignore")
        )

    keyboard.add(types.InlineKeyboardButton("🔙 العودة لاختيار الدولة", callback_data=f"back_cnt_{service_code}"))
    return keyboard
