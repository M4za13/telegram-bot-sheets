import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json

# Состояния для conversation
SENDER, BANK, RUB, CRYPTO, AMOUNT, RATE, ORDER_ID, COMMENT = range(8)

# Настройки
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Замените на ваш токен Telegram-бота
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # Замените на ваш ID таблицы Google Sheets
SHEET_NAME = "Sheet1"  # Замените на имя листа, если отличается

# Подключение к Google Sheets
def get_sheets_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")  # JSON-ключ из переменной окружения
    creds = Credentials.from_service_account_info(json.loads(creds_json))
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

# Запись данных в Google Sheets
def append_to_sheet(data):
    service = get_sheets_service()
    values = [data]
    body = {"values": values}
    service.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:J",
        valueInputOption="RAW",
        body=body
    ).execute()

# Начало диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text("Введите отправителя (например, Иван Иванов):")
    return SENDER

# Обработка отправителя
async def sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sender"] = update.message.text
    await update.message.reply_text("Введите банк (например, Сбер):")
    return BANK

# Обработка банка
async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text
    await update.message.reply_text("Введите сумму в ₽ (например, 10000):")
    return RUB

# Обработка суммы в ₽
async def rub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.replace(".", "").isdigit():
        await update.message.reply_text("Пожалуйста, введите число для суммы в ₽ (например, 10000):")
        return RUB
    context.user_data["rub"] = text
    await update.message.reply_text("Введите криптовалюту (например, BTC):")
    return CRYPTO

# Обработка криптовалюты
async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["crypto"] = update.message.text
    await update.message.reply_text("Введите количество (например, 0.1):")
    return AMOUNT

# Обработка количества
async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.replace(".", "").isdigit():
        await update.message.reply_text("Пожалуйста, введите число для количества (например, 0.1):")
        return AMOUNT
    context.user_data["amount"] = text
    await update.message.reply_text("Введите курс (например, 50000):")
    return RATE

# Обработка курса
async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.replace(".", "").isdigit():
        await update.message.reply_text("Пожалуйста, введите число для курса (например, 50000):")
        return RATE
    context.user_data["rate"] = text
    await update.message.reply_text("Введите ордер ID (например, 12345):")
    return ORDER_ID

# Обработка ордер ID
async def order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_id"] = update.message.text
    await update.message.reply_text("Введите комментарий (например, Покупка):")
    return COMMENT

# Обработка комментария и запись в таблицу
async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comment"] = update.message.text
    date_time = context.user_data["date_time"]
    date, time = date_time.split(" ")
    data = [
        date,
        time,
        context.user_data["sender"],
        context.user_data["bank"],
        context.user_data["rub"],
        context.user_data["crypto"],
        context.user_data["amount"],
        context.user_data["rate"],
        context.user_data["order_id"],
        context.user_data["comment"]
    ]
    
    try:
        append_to_sheet(data)
        await update.message.reply_text("Данные успешно записаны в таблицу! Начать заново? Отправьте /start")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при записи: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END

# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Диалог отменен. Начать заново? Отправьте /start")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Настройка conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, sender)],
            BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bank)],
            RUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, rub)],
            CRYPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, crypto)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount)],
            RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate)],
            ORDER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_id)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
