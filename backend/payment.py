import stripe

stripe.api_key = STRIPE_SECRET_ST_KEY

def create_vin_payment(quantity: int):
    price_id = "price_123456" if quantity == 1 else "price_789012"

    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={"type": "redirect", "redirect": {"url": "https://t.me/your_bot"}},
        metadata={"quantity": quantity}
    )
    return payment_link.url



# # payments.py
# from fastapi import FastAPI, Request, HTTPException
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import stripe
# import os
# from dotenv import load_dotenv
# import requests
#
# load_dotenv()
#
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
#
# app = FastAPI()
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
#
# DOMAIN = os.getenv("DOMAIN") or "http://localhost:3000"
# TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
#
# @app.post("/create-checkout-session")
# async def create_checkout_session(request: Request):
#     data = await request.json()
#     vin = data.get("vin")
#     telegram_id = data.get("telegram_id")
#     plan = data.get("plan", "single")  # default to "single" plan
#
#     if not vin or not telegram_id:
#         raise HTTPException(status_code=400, detail="VIN and Telegram ID are required")
#
#     if plan == "single":
#         price_cents = 299
#         product_name = f"1 VIN Report for {vin}"
#     elif plan == "bundle3":
#         price_cents = 599
#         product_name = f"3 VIN Reports (starting with {vin})"
#     else:
#         raise HTTPException(status_code=400, detail="Invalid plan selected")
#
#     try:
#         checkout_session = stripe.checkout.Session.create(
#             line_items=[
#                 {
#                     'price_data': {
#                         'currency': 'usd',
#                         'product_data': {
#                             'name': product_name,
#                         },
#                         'unit_amount': price_cents,
#                     },
#                     'quantity': 1,
#                 },
#             ],
#             mode='payment',
#             success_url=f"{DOMAIN}/success?vin={vin}",
#             cancel_url=f"{DOMAIN}/cancel",
#             metadata={"vin": vin, "telegram_id": str(telegram_id), "plan": plan},
#         )
#         return {"url": checkout_session.url}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})
#
# @app.post("/webhook")
# async def stripe_webhook(request: Request):
#     payload = await request.body()
#     sig_header = request.headers.get("stripe-signature")
#     webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
#
#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, webhook_secret
#         )
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid payload")
#     except stripe.error.SignatureVerificationError:
#         raise HTTPException(status_code=400, detail="Invalid signature")
#
#     if event['type'] == 'checkout.session.completed':
#         session = event['data']['object']
#         vin = session.get('metadata', {}).get('vin', 'UNKNOWN')
#         telegram_id = session.get('metadata', {}).get('telegram_id')
#         plan = session.get('metadata', {}).get('plan', 'single')
#
#         if telegram_id:
#             send_mock_vin_report(telegram_id, vin, plan)
#
#     return {"status": "success"}
#
# def send_mock_vin_report(telegram_id: str, vin: str, plan: str):
#     if plan == "single":
#         message = f"✅ Оплата получена!\nВот ваш тестовый VIN-отчёт для: {vin}\n(Это пример, в будущем будет реальный отчёт.)"
#     elif plan == "bundle3":
#         message = f"✅ Оплата за пакет 3 VIN!\nВот первый тестовый VIN-отчёт: {vin}\nВы можете прислать ещё 2 VIN-кода для анализа."
#     else:
#         message = f"✅ Оплата получена! VIN: {vin}"
#
#     url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#     payload = {"chat_id": telegram_id, "text": message}
#     try:
#         requests.post(url, json=payload)
#     except Exception as e:
#         print(f"❌ Ошибка отправки сообщения в Telegram: {e}")
