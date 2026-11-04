import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# استيراد ملفات الإعدادات وقاعدة البيانات
from config import BOT_TOKEN
from database import db

# استيراد جميع الهاندلرز (الملفات المسؤولة عن الأزرار والأوامر)
from handlers.start import register_start_handlers
from handlers.numbers_panel import register_numbers_handlers
from handlers.admin import register_admin_handlers

# إعداد مراقب الأخطاء (Logs)
logging.basicConfig(level=logging.INFO)

# تهيئة البوت وتفعيل الذاكرة (MemoryStorage) الضرورية لعمليات الخصم والإضافة
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# تسجيل جميع الهاندلرز لكي يستجيب البوت لها
register_start_handlers(dp)
register_numbers_handlers(dp)
register_admin_handlers(dp)

# --- إعداد خادم الويب (Web Server) ليعمل البوت على منصة Render بدون توقف ---
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
    logging.info(f"Web server started on port {port}")

# --- دوال بدء التشغيل ---
async def on_startup(dispatcher):
    # إغلاق أي جلسات أو ضغطات معلقة لتجنب خطأ TerminatedByOtherGetUpdates
    await bot.delete_webhook(drop_pending_updates=True)
    
    # تهيئة قاعدة البيانات
    db.init_db()
    
    # تشغيل خادم الويب كعملية في الخلفية
    asyncio.create_task(web_server())
    
    logging.info("Bot and Web Server started successfully.")

# --- نقطة تشغيل البوت ---
if __name__ == '__main__':
    # تشغيل البوت بنظام Polling وتجاهل التحديثات القديمة أثناء فترة التوقف
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
