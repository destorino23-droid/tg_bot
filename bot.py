import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# 1. НАСТРОЙКИ (Берем из переменных Railway)
# Если переменные не заданы в Railway, бот выдаст ошибку в логах
TOKEN = os.getenv("TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

logging.basicConfig(level=logging.INFO)

FILE = "shopping.json"

def load_data():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data_to_save):
    with open(FILE, "w") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

data = load_data()

main_keyboard = ReplyKeyboardMarkup([
    ["➕ Добавить продукты"],
    ["📋 Список"],
    ["🧹 Очистить всё"]
], resize_keyboard=True)

def build_list_ui(chat_id):
    items = data.get(str(chat_id), [])
    if not items:
        return "🛒 Список пуст", None
    
    text = "📋 **ВАШ СПИСОК:**"
    keyboard = []
    
    for i, item in enumerate(items):
        status = "✅ " if item["done"] else "❌ "
        keyboard.append([InlineKeyboardButton(f"{status} {item['name']}", callback_id=f"tgl_{i}")])
    
    admin_row = []
    if any(not i["done"] for i in items):
        admin_row.append(InlineKeyboardButton("✔️ Отметить всё", callback_data="mark_done"))
    
    admin_row.append(InlineKeyboardButton("🗑️ Правка списка", callback_data="edit_list"))
    
    keyboard.append(admin_row)
    return text, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"Доступ запрещен. Ваш ID: {user_id}")
        return
    await update.message.reply_text("Бот готов к работе!", reply_markup=main_keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        return

    chat_id = str(update.effective_chat.id)
    text = update.message.text

    if text == "➕ Добавить продукты":
        await update.message.reply_text("Введите список продуктов (каждый с новой строки):")
        context.user_data["state"] = "adding"
        return

    if text == "📋 Список":
        msg_text, kb = build_list_ui(chat_id)
        await update.message.reply_text(msg_text, reply_markup=kb, parse_mode="Markdown")
        return

    if text == "🧹 Очистить всё":
        data[chat_id] = []
        save_data(data)
        await update.message.reply_text("Список очищен!", reply_markup=main_keyboard)
        return

    if context.user_data.get("state") == "adding":
        new_items = [{"name": x.strip(), "done": False} for x in text.split("\n") if x.strip()]
        if chat_id not in data: data[chat_id] = []
        data[chat_id].extend(new_items)
        save_data(data)
        context.user_data["state"] = None
        await update.message.reply_text(f"Добавлено {len(new_items)} поз.", reply_markup=main_keyboard)

if __name__ == '__main__':
    if not TOKEN:
        print("ОШИБКА: TOKEN не найден в переменных окружения!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        print("Бот успешно запущен...")
        app.run_polling()
