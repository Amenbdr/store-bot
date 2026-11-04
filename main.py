import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, executor
from config import BOT_TOKEN
from database import db
from handlers.start import register_start_handlers
from handlers.numbers_panel import register_numbers_handlers

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# تسجيل الهاندلرز المتاحة والمتوفرة فقط
register_start_handlers(dp)
register_numbers_handlers(dp)

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
    db.init_db()
    # تشغيل خادم الويب بجانب البوت
    await web_server()
    logging.info("Bot and Web Server started successfully.")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
