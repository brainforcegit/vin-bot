import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
import stripe
import requests
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
DOMAIN = os.getenv("DOMAIN")
DATABASE_URL = os.getenv("DATABASE_URL")

stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI()

# Database setup
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class VINLog(Base):
    __tablename__ = "vin_logs"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String(17), index=True)
    user_id = Column(String(50), index=True)
    report = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

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

async def start_telegram_bot():
    bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

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
                    f"{DOMAIN}/check-vin",
                    json={"vin": vin, "user_id": str(update.effective_user.id)},
                    timeout=20
                )
                data = response.json()

                if data.get("status") == "ok":
                    r = data["report"]
                    message = format_report_message(vin, r)
                    await update.message.reply_html(message)
                else:
                    await update.message.reply_text("⚠️ Չհաջողվեց ստանալ տվյալներ։")

            except Exception as e:
                await update.message.reply_text("⚠️ Սերվերի սխալ կամ կապի խնդիր։")
                print(f"[ERROR] {e}")
        else:
            await update.message.reply_text("⚠️ Սխալ VIN։ Այն պետք է լինի 17 նիշ և բաղկացած լինի միայն տառերից և թվերից։")

    async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        try:
            response = requests.get(f"{DOMAIN}/history/{user_id}", timeout=20)
            data = response.json()

            if "history" not in data or not data["history"]:
                await update.message.reply_text("❗Դուք դեռ չեք իրականացրել VIN ստուգում։")
                return

            history_text = "<b>📜 Ձեր վերջին VIN ստուգումները</b>:\n\n"
            for i, item in enumerate(data["history"], 1):
                r = item["report"]
                history_text += f"{i}. {r['vin']} — {r.get('make', 'Unknown')} {r.get('model', 'Unknown')} ({r.get('year', 'Unknown')})\n"

            await update.message.reply_html(history_text)

        except Exception as e:
            print("❌ History error:", e)
            await update.message.reply_text("⚠️ Չհաջողվեց բերել պատմությունը։")

    # Add handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("history", handle_history))
    bot_app.add_handler(MessageHandler(filters.Regex("^🔍 Ստուգել VIN$"), handle_vin_prompt))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 Telegram Bot is running...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_telegram_bot())
    print("🚀 CarFact API and Bot are running...")

# ========== MODELS ========== #

class VINRequest(BaseModel):
    vin: str
    user_id: str

# ========== ROUTES ========== #

@app.get("/")
def root():
    return {"message": "Welcome to CarFact!"}

@app.post("/check-vin")
def check_vin(data: VINRequest):
    vin = data.vin.upper()

    if len(vin) != 17 or not vin.isalnum():
        raise HTTPException(status_code=400, detail="Invalid VIN")

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        decoded = res.json()

        fields = {item["Variable"]: item["Value"] for item in decoded["Results"] if item["Value"]}
        report = {
            "vin": vin,
            "make": fields.get("Make"),
            "model": fields.get("Model"),
            "year": fields.get("Model Year"),
            "vehicle_type": fields.get("Vehicle Type"),
            "plant_country": fields.get("Plant Country"),
            "body_class": fields.get("Body Class"),
        }

        # Save to DB
        db = SessionLocal()
        log = VINLog(
            vin=vin,
            user_id=data.user_id,
            report=json.dumps(report)
        )
        db.add(log)
        db.commit()
        db.close()

        return {"status": "ok", "report": report}

    except Exception as e:
        print("[API ERROR]", e)
        raise HTTPException(status_code=500, detail="Failed to fetch VIN data")

@app.get("/history/{user_id}")
def get_user_history(user_id: str):
    db = SessionLocal()
    logs = db.query(VINLog).filter(VINLog.user_id == user_id).order_by(VINLog.timestamp.desc()).limit(10).all()
    db.close()

    history = []
    for log in logs:
        history.append({
            "vin": log.vin,
            "timestamp": log.timestamp.isoformat(),
            "report": json.loads(log.report)
        })

    return {"user_id": user_id, "history": history}

@app.post(f"/{TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    await bot_app.updater.process_update(Update.de_json(json_data, bot_app.bot))
    return {"status": "ok"}

# ========== HELPERS ========== #

def format_report_message(vin, r):
    if not r:
        return f"⚠️ Չհաջողվեց ստանալ VIN {vin}-ի տվյալները։"

    return (
        f"📄 <b>Վճարված VIN ստուգման արդյունքներ ({vin})</b>\n\n"
        f"🏷️ Արտադրող: {r.get('make')}\n"
        f"🚘 Մոդել: {r.get('model')}\n"
        f"📆 Տարին: {r.get('year')}\n"
        f"🚗 Տեսակ: {r.get('vehicle_type')}\n"
        f"🏭 Գործարան: {r.get('plant_country')}\n"
        f"🚙 Մարմնի տիպը: {r.get('body_class')}"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
