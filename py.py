import stripe

stripe.api_key  = "sk_test_51MGaBODI5pzORPnjyszfRxd501BGv6vL8fiKQR9kx2GPf4oaz6R5F9sMb8rN1Snd6xOfnGYZ3LCBV4iP4xbEFgNt00W4ErhfZL"

try:
    # Попытка получить список продуктов (это просто пример проверки)
    products = stripe.Product.list(limit=1)
    print("✅ Ключ Stripe действителен. API вернул ответ:", products)
except stripe.error.AuthenticationError:
    print("❌ Ошибка аутентификации! Проверь ключ.")
except Exception as e:
    print("❌ Другая ошибка:", e)
