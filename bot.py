import logging
import requests
import sqlite3
import math
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==========================================
# ⚙️ إعدادات البوت 
# ==========================================
BOT_TOKEN = "5418318795:AAEO50r0oNYrT3QCLafLDFzww1x2kfCO7Eg"
API_URL = "https://smsbower.app/stubs/handler_api.php"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ==========================================
# 🌍 قائمة الدول الشاملة
# ==========================================
COUNTRIES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "2": "🇰🇿 كازاخستان", "3": "🇨🇳 الصين",
    "4": "🇵🇭 الفلبين", "6": "🇮🇩 إندونيسيا", "12": "🇺🇸 أمريكا", "16": "🇬🇧 بريطانيا",
    "17": "🇲🇦 المغرب", "21": "🇪🇬 مصر", "22": "🇮🇳 الهند", "29": "🇵🇰 باكستان",
    "31": "🇿🇦 جنوب أفريقيا", "36": "🇨🇦 كندا", "43": "🇩🇪 ألمانيا", "46": "🇸🇪 السويد",
    "47": "🇮🇶 العراق", "48": "🇳🇱 هولندا", "53": "🇪🇸 إسبانيا", "58": "🇩🇿 الجزائر",
    "59": "🇸🇦 السعودية", "73": "🇧🇷 البرازيل", "78": "🇫🇷 فرنسا", "86": "🇮🇹 إيطاليا",
    "87": "🇾🇪 اليمن", "89": "🇹🇳 تونس", "94": "🇱🇧 لبنان", "95": "🇦🇪 الإمارات",
    "97": "🇵🇸 فلسطين", "100": "🇱🇾 ليبيا
