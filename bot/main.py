# bot/main.py
import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

START_TEXT = (
    "📟 <b>CarFact</b> — ստուգիր քո ավտոմեքենայի ջողովության պատմությունը ընդ VIN-իքրովորդֆ\n"
    "🚗 Իմացիրթիրկրովորդֆ\n"
    "• քանի <b>սպասարոբածեր</b> է ունեցել մեքենան\n"
    "• եղել են արդյոք <b>վչարներ</b>\n"
    "• քանի <b>կիլոմետր</b> է անցել վրապրականում\n"
    "• որվ ու և երբ է <b>ներմուծվել</b>\n\n"
    "Սեղմիր ' 🔍 Ստուգել VIN'՝ֈ ստուգումը սկսելու համարարինք։"
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
                "https://carfact.onrender.com/check-vin",
                json={
                    "vin": vin,
                    "user_id": str(update.effective_user.id)
                },
                timeout=10
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

async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        response = requests.get(f"https://carfact.onrender.com/history/{user_id}", timeout=10)
        data = response.json()

        if not data["history"]:
            await update.message.reply_text("❗Դուք դեռ չեք իրականացրել VIN ստուգում։")
            return

        text = "<b>📜 Ձեր վերջին VIN ստուգումները</b>:\n\n"
        for i, item in enumerate(data["history"], 1):
            r = item["report"]
            text += f"{i}. {r['vin']} — {r.get('model')}, {r.get('year')}\n"

        await update.message.reply_html(text)

    except Exception as e:
        print("❌ History error:", e)
        await update.message.reply_text("⚠️ Չհաջողվեց բերել պատմությունը։")

async def buy(update, context):
    quantity = int(context.args[0]) if context.args else 1
    if quantity not in [1, 3]:
        await update.message.reply_text("Укажите количество: 1 или 3 (например, /buy 3)")
        return

    payment_url = create_vin_payment(quantity)
    await update.message.reply_text(f"Оплатите проверку здесь: {payment_url}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Ունեմ VIN$"), handle_vin_prompt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin_input))

    print("🤖 CarFact բոտը աշխատում է...")
    app.run_polling()

# from aiogram import Bot, Dispatcher, types
# from aiogram.utils import executor
# import logging
# import requests
# import os
# from dotenv import load_dotenv
#
# load_dotenv()
#
# TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# API_BASE_URL = os.getenv("API_BASE_URL", "https://carfact.onrender.com")  # или http://localhost:8000
#
# bot = Bot(token=TELEGRAM_TOKEN)
# dp = Dispatcher(bot)
#
# logging.basicConfig(level=logging.INFO)
#
# @dp.message_handler(commands=["start"])
# async def start_command(message: types.Message):
#     await message.answer("👋 Добро пожаловать! Отправьте /buy чтобы приобрести VIN-отчёт.")
#
# @dp.message_handler(commands=["buy"])
# async def buy_handler(message: types.Message):
#     keyboard = types.InlineKeyboardMarkup()
#     keyboard.add(
#         types.InlineKeyboardButton(text="1 VIN — $2.99", callback_data="buy:single"),
#         types.InlineKeyboardButton(text="3 VIN — $5.99", callback_data="buy:bundle3"),
#     )
#     await message.answer("Выберите тариф:", reply_markup=keyboard)
#
# @dp.callback_query_handler(lambda c: c.data.startswith("buy:"))
# async def process_buy_callback(callback_query: types.CallbackQuery):
#     plan = callback_query.data.split(":")[1]
#     vin = "ABC1234567890XYZ"  # можешь заменить на временный или запросить у пользователя
#     telegram_id = callback_query.from_user.id
#
#     try:
#         res = requests.post(f"{API_BASE_URL}/create-checkout-session", json={
#             "vin": vin,
#             "telegram_id": telegram_id,
#             "plan": plan
#         })
#         res.raise_for_status()
#         data = res.json()
#         await bot.send_message(telegram_id, f"💳 Перейдите по ссылке для оплаты:\n{data['url']}")
#     except Exception as e:
#         await bot.send_message(telegram_id, f"⚠️ Ошибка при создании сессии оплаты: {e}")
#
# if __name__ == "__main__":
#     executor.start_polling(dp, skip_updates=True)
