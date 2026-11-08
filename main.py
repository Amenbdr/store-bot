# -*- coding: utf-8 -*-
"""
SUPER-BOT - لوحة إدارة ومراقبة SMSBower
هذا الإصدار يعرض الرصيد والدول ومزودي الأرقام والأسعار والمخزون،
ويرسل تنبيهات المخزون إلى قناة خاصة. لا ينفذ شراء أرقام ولا يجمع رموز تحقق.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)

# ========= الإعدادات التي تعدلها =========
BOT_TOKEN = "6109143608:AAGtuR45uCQmAapFbY7GU59h-RMrKlzqy7I"
ADMIN_ID = 5396793642
# يضاف مفتاح SMSBower من داخل البوت عبر الأمر /setapi
CHANNEL_ID = "-1001571573121"
SERVICE_CODE = "wa"             # تحقق من رمز الخدمة في حساب/توثيق SMSBower
MAX_PRICE = 0.50
DAILY_BUDGET = 5.00             # حد مرجعي للتنبيهات، لا توجد مشتريات في هذا الإصدار
DAILY_LIMIT = 100               # حد مرجعي
CHECK_SECONDS = 60
STATE_FILE = Path("superbot_state.json")
API_URL = "https://smsbower.page/stubs/handler_api.php"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("SUPER-BOT")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.exception("تعذر قراءة ملف الحالة")
    return {
        "selected_country": None,
        "selected_country_name": None,
        "selected_provider": None,
        "watching": False,
        "last_stock": None,
        "api_key": "",
    }


state = load_state()
monitor_task: asyncio.Task | None = None


def save_state() -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)


async def api_request(**params: Any) -> Any:
    api_key = state.get("api_key", "")
    if not api_key:
        raise RuntimeError("أضف مفتاح SMSBower من داخل البوت بالأمر /setapi")
    payload = {"api_key": api_key, **params}
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(API_URL, params=payload)
        response.raise_for_status()
        text = response.text.strip()
        try:
            return response.json()
        except ValueError:
            return text


async def deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("هذا البوت خاص بالمدير فقط.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    await update.message.reply_text(
        "مرحباً بك في لوحة إدارة SUPER-BOT.\n\n"
        "/setapi - إضافة أو تغيير مفتاح SMSBower\n"
        "/balance - عرض الرصيد\n"
        "/country اسم_الدولة - البحث عن دولة\n"
        "/prices - عرض مزودي الدولة المختارة\n"
        "/channel - اختبار القناة\n"
        "/watch - بدء مراقبة المخزون\n"
        "/stop - إيقاف المراقبة\n"
        "/settings - عرض الإعدادات"
    )



async def setapi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    context.user_data["waiting_for_api_key"] = True
    await update.message.reply_text(
        "أرسل مفتاح SMSBower الآن في هذه المحادثة الخاصة.\n"
        "لن يظهر المفتاح في رد البوت، وسيتم حذف رسالتك بعد استلامها إن أمكن."
    )


async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update) or not context.user_data.get("waiting_for_api_key"):
        return
    key = (update.message.text or "").strip()
    if not key:
        return
    state["api_key"] = key
    save_state()
    context.user_data["waiting_for_api_key"] = False
    try:
        await update.message.delete()
    except Exception:
        pass
    await update.effective_chat.send_message(
        "تم حفظ مفتاح SMSBower. استخدم /balance لاختبار الاتصال."
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    try:
        result = await api_request(action="getBalance")
        await update.message.reply_text(f"رد الرصيد من SMSBower:\n{result}")
    except Exception as e:
        await update.message.reply_text(f"تعذر جلب الرصيد: {e}")


def normalize_countries(data: Any) -> list[dict]:
    rows = []
    if isinstance(data, list):
        source = data
    elif isinstance(data, dict):
        source = data.values()
    else:
        source = []
    for item in source:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        name = item.get("eng") or item.get("name") or item.get("rus") or str(cid)
        if cid is not None:
            rows.append({"id": str(cid), "name": str(name)})
    return rows


async def country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text(
            "اكتب اسم الدولة أو رقمها هكذا:\n/country Saudi"
        )
    try:
        raw = await api_request(action="getCountries")
        countries = normalize_countries(raw)
        matches = [
            c for c in countries
            if query.casefold() in c["name"].casefold()
            or query == c["id"]
        ][:20]
        if not matches:
            return await update.message.reply_text(
                "لم أجد الدولة. جرّب الاسم الإنجليزي أو رقم الدولة."
            )
        keyboard = [[InlineKeyboardButton(
            f'{c["name"]} | ID: {c["id"]}',
            callback_data=f'country:{c["id"]}:{c["name"][:35]}'
        )] for c in matches]
        await update.message.reply_text(
            "اختر الدولة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        await update.message.reply_text(f"تعذر البحث عن الدول: {e}")


async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    if not state.get("selected_country"):
        return await update.message.reply_text(
            "اختر دولة أولاً باستخدام /country اسم الدولة"
        )
    await send_prices(update.effective_chat.id, context)


async def send_prices(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = state["selected_country"]
    try:
        data = await api_request(
            action="getPricesV3",
            service=SERVICE_CODE,
            country=cid,
        )
        rows = extract_providers(data, cid)
        if not rows:
            await context.bot.send_message(
                chat_id,
                "لم أستطع استخراج مزودي الأرقام من رد الموقع. "
                "قد تختلف بنية الرد أو رمز الخدمة."
            )
            return
        lines = [
            f'الدولة: {state.get("selected_country_name")} (ID {cid})',
            f'الخدمة: {SERVICE_CODE}',
            "المزودون / السعر / المخزون:",
        ]
        buttons = []
        for row in rows[:30]:
            lines.append(
                f'المزود {row["id"]}: ${row["price"]:.3f} | مخزون: {row["count"]}'
            )
            buttons.append([InlineKeyboardButton(
                f'اختيار المزود {row["id"]} (${row["price"]:.3f})',
                callback_data=f'provider:{row["id"]}'
            )])
        lines.append("\nاختيار المزود هنا للحفظ والمراقبة فقط؛ لا يتم الشراء.")
        await context.bot.send_message(
            chat_id, "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        await context.bot.send_message(chat_id, f"تعذر جلب الأسعار: {e}")


def extract_providers(data: Any, country_id: str) -> list[dict]:
    if not isinstance(data, dict):
        return []
    country_data = data.get(country_id)
    if country_data is None and len(data) == 1:
        country_data = next(iter(data.values()))
    if not isinstance(country_data, dict):
        return []
    service_data = country_data.get(SERVICE_CODE)
    if not isinstance(service_data, dict):
        return []
    rows = []
    for key, value in service_data.items():
        if not isinstance(value, dict):
            continue
        try:
            price = float(value.get("price", value.get("cost", 0)))
            count = int(float(value.get("count", 0)))
            provider_id = str(value.get("provider_id", key))
            rows.append({"id": provider_id, "price": price, "count": count})
        except (TypeError, ValueError):
            continue
    return sorted(rows, key=lambda x: x["price"])


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        if update.callback_query:
            await update.callback_query.answer("غير مصرح", show_alert=True)
        return
    q = update.callback_query
    await q.answer()
    parts = q.data.split(":", 2)
    if parts[0] == "country":
        state["selected_country"] = parts[1]
        state["selected_country_name"] = parts[2] if len(parts) > 2 else parts[1]
        state["selected_provider"] = None
        save_state()
        await q.edit_message_text(
            f'تم اختيار الدولة: {state["selected_country_name"]} '
            f'(ID {state["selected_country"]}).\n'
            "استخدم /prices لعرض المزودين والأسعار والمخزون."
        )
    elif parts[0] == "provider":
        state["selected_provider"] = parts[1]
        save_state()
        await q.edit_message_text(
            f"تم حفظ اختيار المزود يدوياً: {parts[1]}.\n"
            "هذا الاختيار للمراقبة فقط، ولا ينفذ شراء."
        )


async def channel_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    if not CHANNEL_ID:
        return await update.message.reply_text(
            "ضع معرف القناة في CHANNEL_ID أعلى الكود، "
            "وأضف البوت مشرفاً فيها."
        )
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="تم ربط SUPER-BOT بالقناة بنجاح."
        )
        await update.message.reply_text("نجح اختبار إرسال رسالة إلى القناة.")
    except Exception as e:
        await update.message.reply_text(f"فشل الإرسال إلى القناة: {e}")


async def monitor_loop(app: Application) -> None:
    while state.get("watching"):
        try:
            cid = state.get("selected_country")
            provider = state.get("selected_provider")
            if cid and provider and CHANNEL_ID:
                data = await api_request(
                    action="getPricesV3",
                    service=SERVICE_CODE,
                    country=cid,
                )
                rows = extract_providers(data, cid)
                row = next((r for r in rows if r["id"] == provider), None)
                if row:
                    snapshot = {
                        "count": row["count"],
                        "price": row["price"],
                    }
                    if snapshot != state.get("last_stock"):
                        state["last_stock"] = snapshot
                        save_state()
                        if row["count"] > 0 and row["price"] <= MAX_PRICE:
                            await app.bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=(
                                    "تنبيه مخزون SUPER-BOT\n"
                                    f'الدولة: {state.get("selected_country_name")}\n'
                                    f'المزود: {provider}\n'
                                    f'السعر: ${row["price"]:.3f}\n'
                                    f'المخزون: {row["count"]}\n'
                                    "هذا إشعار فقط؛ لا يوجد شراء تلقائي."
                                ),
                            )
        except Exception:
            log.exception("خطأ أثناء مراقبة المخزون")
        await asyncio.sleep(max(30, CHECK_SECONDS))


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global monitor_task
    if not is_admin(update):
        return await deny(update)
    if not CHANNEL_ID:
        return await update.message.reply_text("أضف CHANNEL_ID أعلى الكود أولاً.")
    if not state.get("selected_country") or not state.get("selected_provider"):
        return await update.message.reply_text(
            "اختر الدولة ثم المزود يدوياً قبل بدء المراقبة."
        )
    state["watching"] = True
    save_state()
    if monitor_task is None or monitor_task.done():
        monitor_task = asyncio.create_task(monitor_loop(context.application))
    await update.message.reply_text("بدأت مراقبة المخزون.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    state["watching"] = False
    save_state()
    await update.message.reply_text("تم إيقاف مراقبة المخزون.")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return await deny(update)
    await update.message.reply_text(
        "إعدادات SUPER-BOT:\n"
        f'الدولة: {state.get("selected_country_name") or "غير محددة"}\n'
        f'معرف الدولة: {state.get("selected_country") or "-"}\n'
        f'المزود: {state.get("selected_provider") or "غير محدد"}\n'
        f'القناة: {CHANNEL_ID or "غير محددة"}\n'
        f'الحد السعري للتنبيه: ${MAX_PRICE:.2f}\n'
        f'الميزانية المرجعية: ${DAILY_BUDGET:.2f}\n'
        f'الحد اليومي المرجعي: {DAILY_LIMIT}\n'
        f'المراقبة: {"تعمل" if state.get("watching") else "متوقفة"}\n\n'
        "الميزانية والحد اليومي لا يخصمان أو ينفذان عمليات شراء في هذا الإصدار."
    )


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN.startswith("PUT_"):
        raise SystemExit("ضع BOT_TOKEN في أعلى الملف قبل التشغيل.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setapi", setapi))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("country", country))
    app.add_handler(CommandHandler("prices", show_prices))
    app.add_handler(CommandHandler("channel", channel_test))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(callback))
    log.info("SUPER-BOT started")
    app.run_polling()


if __name__ == "__main__":
    main()
