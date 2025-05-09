import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
import stripe
import requests
from pydantic import BaseModel
from backend.database import init_db, SessionLocal, VINLog
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
DOMAIN = os.getenv("DOMAIN")

stripe.api_key = STRIPE_SECRET_KEY
init_db()

app = FastAPI()

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

                if data["status"] == "ok":
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

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.Regex("^🔍 Ստուգել VIN$"), handle_vin_prompt))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 Telegram Bot is running...")
    await bot_app.run_polling()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_telegram_bot())
    print("🚀 CarFact API and Bot are running...")

# ========== MODELS ========== #

class VINRequest(BaseModel):
    vin: str
    user_id: str

# ========== ROUTES ========== #

@app.get("/health")
def health():
    return {"status": "ok"}

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

    result = []
    for log in logs:
        result.append({
            "vin": log.vin,
            "timestamp": log.timestamp.isoformat(),
            "report": json.loads(log.report)
        })

    return {"user_id": user_id, "history": result}

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as ve:
        print("❌ ValueError in webhook:", ve)
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as se:
        print("❌ Signature error in webhook:", se)
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print("❌ General error in webhook:", e)
        raise HTTPException(status_code=500, detail="Unhandled error")

    print(f"✅ Stripe Event Received: {event['type']}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        telegram_user_id = metadata.get("telegram_user_id")
        vin = metadata.get("vin")

        if telegram_user_id and vin:
            try:
                response = requests.post(
                    f"{DOMAIN}/check-vin",
                    json={"vin": vin, "user_id": "paid:" + telegram_user_id},
                    timeout=20
                )
                report = response.json().get("report", {})
                message = format_report_message(vin, report)
                send_telegram_message(telegram_user_id, message)
            except Exception as e:
                print("❌ Error during VIN check or Telegram send:", e)

    return {"status": "success"}

# ========== HELPERS ========== #

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print("[Telegram Error]", e)

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