import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

START_TEXT = (
    "🧾 <b>CarFact</b> — ստուգիր քո ավտոմեքենայի իրական պատմությունը ըստ VIN-ի։\n\n"
    "🚗 Իմացիր՝\n"
    "• քանի <b>սեփականատեր</b> է ունեցել մեքենան\n"
    "• եղել են արդյոք <b>վթարներ</b>\n"
    "• քանի <b>կիլոմետր</b> է անցել իրականում\n"
    "• որտեղ և երբ է <b>ներմուծվել</b>\n\n"
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
                "http://localhost:8000/check-vin",
                json={
                    "vin": vin,
                    "user_id": str(update.effective_user.id)
                },
                timeout=5
            )
            data = response.json()

            if data["status"] == "ok":
                report = data["report"]
                message = (
                    f"📄 <b>Ավտոմեքենայի պատմություն</b> ({report['vin']})\n\n"
                    f"🚘 Մոդել: {report['model']}\n"
                    f"👥 Սեփականատերեր: {report['owners']}\n"
                    f"📉 Վերջին գրանցված վազքը: {report['mileage']}\n"
                    f"🛠️ Վթար: {report['accident']}\n"
                    f"🌍 Ներմուծվել է՝ {report['imported']}\n"
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
        response = requests.get(f"http://localhost:8000/history/{user_id}", timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data["history"]:
            await update.message.reply_text("❗Դուք դեռ չեք իրականացրել VIN ստուգում։")
            return

        text = "<b>📜 Ձեր վերջին VIN ստուգումները</b>:\n\n"
        for i, item in enumerate(data["history"], 1):
            r = item["report"]
            text += f"{i}. {r['vin']} — {r['model']}, {r['mileage']}\n"

        await update.message.reply_html(text)

    except Exception as e:
        print("❌ History error:", e)
        await update.message.reply_text("⚠️ Չհաջողվեց բերել պատմությունը։")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Ունեմ VIN$"), handle_vin_prompt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 CarFact բոտը աշխատում է...")
    app.run_polling()
