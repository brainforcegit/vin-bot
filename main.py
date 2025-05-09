import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
START_TEXT = (
    "📟 <b>CarFact</b> — ստուգիր քո ավտոմեքենայի պատմությունը VIN-ի միջոցով\n"
    "🚗 Իմացիր՝\n"
    "• քանի <b>սեփականատեր</b> է ունեցել մեքենան\n"
    "• եղել են արդյոք <b>վթարներ</b>\n"
    "• քանի <b>կիլոմետր</b> է անցել\n"
    "• երբ է <b>ներմուծվել</b>\n\n"
    "Սեղմիր '🔍 Ստուգել VIN'՝ ստուգումը սկսելու համար։"
)

app = FastAPI()

keyboard = ReplyKeyboardMarkup([["🔍 Ստուգել VIN"]], resize_keyboard=True)

async def start_bot():
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(START_TEXT, reply_markup=keyboard)

    async def handle_vin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        vin = update.message.text.strip().upper()
        if len(vin) == 17 and vin.isalnum():
            await update.message.reply_text(f"🔎 Ստուգում եմ VIN: {vin} ...")
        else:
            await update.message.reply_text("⚠️ Սխալ VIN։ Այն պետք է լինի 17 նիշ և բաղկացած լինի միայն տառերից և թվերից։")

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🚀 Telegram Bot is running...")
    await bot_app.run_polling()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_bot())
    print("🚀 CarFact API server is running...")

@app.get("/")
async def root():
    return {"message": "Welcome to CarFact!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
