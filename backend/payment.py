import stripe
from dotenv import load_dotenv
import os

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # ✅ исправлено

# Замени на свои реальные price_id из Stripe Dashboard
PRICE_ID_SINGLE = "price_1VIN..."
PRICE_ID_BUNDLE3 = "price_3VIN..."

def create_vin_payment(quantity: int, telegram_user_id: str):
    if quantity == 1:
        price_id = PRICE_ID_SINGLE
    elif quantity == 3:
        price_id = PRICE_ID_BUNDLE3
    else:
        raise ValueError("Only quantities 1 or 3 are supported.")

    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={"quantity": quantity, "telegram_user_id": telegram_user_id},
        after_completion={"type": "redirect", "redirect": {"url": "https://t.me/carfactarm_bot"}},
    )
    return payment_link.url
