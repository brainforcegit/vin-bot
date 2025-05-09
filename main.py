import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import requests
import uvicorn
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DOMAIN = os.getenv("DOMAIN")

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

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_telegram_bot())
    print("🚀 CarFact API and Bot are running...")

@app.get("/")
async def root():
    return {"message": "Welcome to CarFact!"}

@app.post("/check-vin")
async def check_vin(vin: str, user_id: str):
    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(status_code=400, detail="Invalid VIN format.")
    try:
        # Simulate VIN check (replace with real API call)
        response = {
            "status": "ok",
            "report": {
                "vin": vin,
                "make": "Toyota",
                "model": "Camry",
                "year": "2020",
                "vehicle_type": "Sedan",
                "plant_country": "Japan",
                "body_class": "Sedan"
            }
        }
        return response
    except Exception as e:
        print(f"[ERROR] VIN Check failed: {e}")
        raise HTTPException(status_code=500, detail="VIN check failed.")

async def start_telegram_bot():
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(START_TEXT, reply_markup=keyboard)

    async def handle_vin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        vin = update.message.text.strip().upper()

        if len(vin) == 17 and vin.isalnum():
            await update.message.reply_text(f"🔎 Ստուգում եմ VIN: {vin} ...")
            try:
                response = requests.post(
                    f"{DOMAIN}/check-vin",
                    json={"vin": vin, "user_id": str(update.effective_user.id)},
                    timeout=20
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

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.Regex("^🔍 Ստուգել VIN$"), handle_vin_input))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 Telegram Bot is running...")
    await bot_app.run_polling()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
