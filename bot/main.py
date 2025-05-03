import sys
import os
from pathlib import Path

# Абсолютный путь к родительской директории проекта vin-bot
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from backend.payment import create_vin_payment

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

START_TEXT = (
    "📟 <b>CarFact</b> — ստուգիր քո ավտոմեքենայի պատմությունը VIN-ի միջոցով\n"
    "🚗 Իմացիր՝\n"
    "• քանի <b>սեփականատեր</b> է ունեցել մեքենան\n"
    "• եղել են արդյոք <b>վթարներ</b>\n"
    "• քանի <b>կիլոմետր</b> է անցել\n"
    "• երբ է <b>ներմուծվել</b>\n\n"
    "Սեղմիր '🔍 Ստուգել VIN'՝ ստուգումը սկսելու համար։"
)

keyboard = ReplyKeyboardMarkup([["🔍 Ստուգել VIN"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(START_TEXT, reply_markup=keyboard)

async def handle_vin_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Խնդրում ենք ուղարկել ավտոմեքենայի VIN կոդը (17 նիշ):")

async def handle_vin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()

    if len(vin) == 17 and vin.isalnum():
        await update.message.reply_text(f"🔎 Ստուգում եմ VIN: {vin} ...")

        try:
            response = requests.post(
                "https://carfact.onrender.com/check-vin",
                json={
                    "vin": vin,
                    "user_id": str(update.effective_user.id)
                },
                timeout=20  # увеличь таймаут на случай пробуждения Render.com
            )
            data = response.json()

            if data["status"] == "ok":
                r = data["report"]
                message = (
                    f"📄 <b>Ավտոմեքենայի տվյալներ</b> ({r['vin']})\n\n"
                    f"🏷️ Արտադրող: {r.get('make')}\n"
                    f"🚘 Մոդել: {r.get('model')}\n"
                    f"📆 Տարին: {r.get('year')}\n"
                    f"🚗 Տեսակ: {r.get('vehicle_type')}\n"
                    f"🏭 Գործարան: {r.get('plant_country')}\n"
                    f"🚙 Մարմնի տիպը: {r.get('body_class')}"
                )
                await update.message.reply_html(message)
            else:
                await update.message.reply_text("⚠️ Չհաջողվեց ստանալ տվյալներ։")

        except Exception as e:
            await update.message.reply_text("⚠️ Սերվերի սխալ կամ կապի խնդիր։")
            print(f"[ERROR] {e}")
    else:
        await update.message.reply_text("⚠️ Սխալ VIN։ Այն պետք է լինի 17 նիշ և բաղկացած լինի միայն տառերից և թվերից։")

async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = requests.get(f"https://carfact.onrender.com/history/{user_id}", timeout=20)
        data = response.json()

        if not data["history"]:
            await update.message.reply_text("❗Դուք դեռ չեք իրականացրել VIN ստուգում։")
            return

        text = "<b>📜 Ձեր վերջին VIN ստուգումները</b>:\n\n"
        for i, item in enumerate(data["history"], 1):
            r = item["report"]
            text += f"{i}. {r['vin']} — {r.get('model')}, {r.get('year')}\n"

        await update.message.reply_html(text)

    except Exception as e:
        print("❌ History error:", e)
        await update.message.reply_text("⚠️ Չհաջողվեց բերել պատմությունը։")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    quantity = int(context.args[0]) if context.args else 1
    if quantity not in [1, 3]:
        await update.message.reply_text("Укажите количество: 1 или 3 (например, /buy 3)")
        return

    payment_url = create_vin_payment(quantity, telegram_user_id=user_id)
    await update.message.reply_text(f"Оплатите проверку здесь: {payment_url}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Ստուգել VIN$"), handle_vin_prompt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 CarFact բոտը աշխատում է...")
    app.run_polling()
