import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import stripe

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID_SINGLE = os.getenv("STRIPE_PRICE_ID_SINGLE")
STRIPE_PRICE_ID_BUNDLE = os.getenv("STRIPE_PRICE_ID_BUNDLE")

# Telegram configuration
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram bot setup
keyboard = ReplyKeyboardMarkup([["🔍 Ստուգել VIN"]], resize_keyboard=True)

@app.on_event("startup")
async def startup_event():
    print("🚀 CarFact server is running...")

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
        return JSONResponse(response)
    except Exception as e:
        print(f"[ERROR] VIN Check failed: {e}")
        raise HTTPException(status_code=500, detail="VIN check failed.")

@app.get("/history/{user_id}")
async def get_history(user_id: str):
    # Placeholder for real history logic
    return {"history": [{"vin": "JT4BG22K0W0012345", "model": "Camry", "year": "2020"}]}

@app.post("/webhook")
async def stripe_webhook(request: dict):
    print(f"Received webhook: {request}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
