import json
import logging
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

# 1. НАСТРОЙКИ
ALLOWED_USERS = [7367777258, 805623664] # Замени на свой ID
TOKEN = "8611751285:AAFUZ_cRVXWyCV--1mgdL-runtajZ0lItQk"


logging.basicConfig(level=logging.INFO)

FILE = "shopping.json"
PROXY_URL = "http://proxy.server:3128"

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
        return "🛒 **Список пуст**", None

    text = "📝 **ВАШ СПИСОК:**"
    keyboard = []

    for item in items:
        status = "✅" if item["done"] else "🛒"
        keyboard.append([InlineKeyboardButton(f"{status} {item['name']}", callback_data=f"tgl_{item['name']}")])

    admin_row = []
    if any(i["done"] for i in items):
        admin_row.append(InlineKeyboardButton("✨ Убрать готовое", callback_data="clear_done"))

    admin_row.append(InlineKeyboardButton("✍️ Правка текстом", callback_data="edit_text"))

    keyboard.append(admin_row)
    return text, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    await update.message.reply_text("Бот готов! 👇", reply_markup=main_keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    chat_id = str(update.effective_chat.id)
    text = update.message.text

    # Безопасное удаление твоего сообщения
    try:
        await update.message.delete()
    except:
        pass

    if text == "➕ Добавить продукты":
        msg = await context.bot.send_message(chat_id=chat_id, text="✏️ Пришли список (каждый продукт с новой строки):")
        context.user_data["last_msg"] = msg.message_id
        context.user_data["state"] = "adding"
        return

    elif text == "📋 Список":
        # Удаляем старый список, если он был, чтобы не плодить сообщения
        if "list_msg_id" in context.user_data:
            try: await context.bot.delete_message(chat_id, context.user_data["list_msg_id"])
            except: pass

        text_ui, kb_ui = build_list_ui(chat_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=text_ui, reply_markup=kb_ui, parse_mode="Markdown")
        context.user_data["list_msg_id"] = msg.message_id
        return

    elif text == "🧹 Очистить всё":
        data[chat_id] = []
        save_data(data)
        if "list_msg_id" in context.user_data:
            try: await context.bot.edit_message_text("🛒 Список пуст", chat_id=chat_id, message_id=context.user_data["list_msg_id"])
            except: pass
        return

    # ЛОГИКА СОХРАНЕНИЯ / ПРАВКИ ТЕКСТА
    if context.user_data.get("state") == "adding":
        # 1. Удаляем инструкцию ("Пришли список" или "Скопируй...")
        if "last_msg" in context.user_data:
            try: await context.bot.delete_message(chat_id, context.user_data["last_msg"])
            except: pass

        # 2. Удаляем предыдущий ВЕСЬ список (старый столбец)
        if "list_msg_id" in context.user_data:
            try: await context.bot.delete_message(chat_id, context.user_data["list_msg_id"])
            except: pass

        # Перезаписываем данные
        data[chat_id] = []
        lines = text.replace(',', '\n').split('\n')
        for line in lines:
            name = line.strip()
            if name:
                data[chat_id].append({"name": name, "done": False})

        save_data(data)
        context.user_data["state"] = None

        # 3. Выводим новый чистый список и запоминаем его ID
        text_ui, kb_ui = build_list_ui(chat_id)
        new_msg = await context.bot.send_message(chat_id=chat_id, text=text_ui, reply_markup=kb_ui, parse_mode="Markdown")
        context.user_data["list_msg_id"] = new_msg.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    query = update.callback_query
    chat_id = str(query.message.chat_id)
    await query.answer()

    if query.data == "edit_text":
        items = data.get(chat_id, [])
        if not items: return

        raw_text = "\n".join([i["name"] for i in items])
        context.user_data["state"] = "adding"

        # Удаляем старое сообщение со списком при переходе в режим правки
        try: await query.message.delete()
        except: pass

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"📋 Скопируй, исправь и пришли обратно:\n\n`{raw_text}`",
            parse_mode="Markdown"
        )
        context.user_data["last_msg"] = msg.message_id
        return

    elif query.data.startswith("tgl_"):
        target_name = query.data.replace("tgl_", "")
        for item in data[chat_id]:
            if item["name"] == target_name:
                item["done"] = not item["done"]
                break

    elif query.data == "clear_done":
        data[chat_id] = [i for i in data[chat_id] if not i["done"]]

    save_data(data)
    text_ui, kb_ui = build_list_ui(chat_id)

    if kb_ui:
        await query.edit_message_text(text_ui, reply_markup=kb_ui, parse_mode="Markdown")
        context.user_data["list_msg_id"] = query.message.message_id
    else:
        await query.edit_message_text("🛒 Список пуст")

# ЗАПУСК С ПЕРЕЗАПУСКОМ ПРИ ОШИБКАХ СЕТИ
t_request = HTTPXRequest(proxy=PROXY_URL)
app = ApplicationBuilder().token(TOKEN).request(t_request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_callback))

if __name__ == '__main__':
    while True:
        try:
            print("Бот запущен...")
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Сбой сети: {e}. Повтор через 8 сек...")
            time.sleep(8)
