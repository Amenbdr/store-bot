import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, executor

from config import BOT_TOKEN
from database import db

# استيراد ملفات الهاندلرز
from handlers.start import register_start_handlers
from handlers.numbers_panel import register_numbers_handlers
from handlers.admin import register_admin_handlers  # استيراد لوحة الإدارة

# إعداد السجلات لمراقبة الأخطاء
logging.basicConfig(level=logging.INFO)

# تهيئة البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# تسجيل جميع المعالجات (الأزرار والأوامر)
register_start_handlers(dp)
register_numbers_handlers(dp)
register_admin_handlers(dp)  # تفعيل أزرار لوحة التحكم

# --- خادم ويب وهمي لترضية منصة Render والبقاء مجانياً ---
async def handle(request):
    return web.Response(text="Virtual Number Bot is running successfully! 🚀")

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def on_startup(dispatcher):
    # 🔴 السطر الأهم: إغلاق أي جلسات عالقة وحذف الضغطات القديمة لحل مشكلة تعليق الأزرار
    await bot.delete_webhook(drop_pending_updates=True)
    
    # تهيئة قاعدة البيانات
    db.init_db()
    
    # تشغيل خادم الويب
    await web_server()
    logging.info("Bot and Web Server started successfully.")

if __name__ == '__main__':
    # تشغيل البوت متجاهلاً أي تحديثات قديمة قد تسبب تعارض
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
