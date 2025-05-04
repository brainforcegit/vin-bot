import json
import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import stripe
from .database import init_db, SessionLocal, VINLog
import os

load_dotenv()
init_db()

app = FastAPI()

# ENV variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

stripe.api_key = STRIPE_SECRET_KEY

# ========== MODELS ==========

class VINRequest(BaseModel):
    vin: str
    user_id: str

# ========== ROUTES ==========

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
        print("🎯 Metadata:", metadata)

        telegram_user_id = metadata.get("telegram_user_id")
        vin = metadata.get("vin")

        if telegram_user_id and vin:
            try:
                print(f"🚀 Processing paid VIN {vin} for Telegram user {telegram_user_id}")
                response = requests.post(
                    "https://carfact.onrender.com/check-vin",
                    json={"vin": vin, "user_id": "paid:" + telegram_user_id},
                    timeout=20
                )
                report = response.json().get("report", {})
                message = format_report_message(vin, report)
                send_telegram_message(telegram_user_id, message)
            except Exception as e:
                print("❌ Error during VIN check or Telegram send:", e)

    return {"status": "success"}

# ========== HELPERS ==========

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
