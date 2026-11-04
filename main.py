import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers.start import register_start_handlers
from handlers.admin_panel import register_admin_handlers
from handlers.numbers_panel import register_numbers_handlers

# إعداد السجلات (Logging)
logging.basicConfig(level=logging.INFO)

# تهيئة البوت والتخزين المؤقت
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def on_startup(dispatcher):
    logging.info("🚀 جاري تشغيل البوت بنجاح...")
    # تسجيل جميع أقسام الـ Handlers
    register_start_handlers(dispatcher)
    register_admin_handlers(dispatcher)
    register_numbers_handlers(dispatcher)
    logging.info("✅ تم تحميل جميع الأقسام واللوحات بنجاح!")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
