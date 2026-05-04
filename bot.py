import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
# Берем ID из переменных Railway
ALLOWED_USERS = [int(x.strip()) for x in os.getenv('ALLOWED_USERS', '').split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)
shopping_list = {} # Тут храним продукты

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, f"Доступ запрещен. ID: {message.from_user.id}")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот обновлен! Используй кнопки:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show(message):
    if not shopping_list:
        bot.send_message(message.chat.id, "Список пуст")
        return
    
    text = "🛍 **Ваш список:**\n"
    keyboard = types.InlineKeyboardMarkup()
    for item, bought in shopping_list.items():
        status = "✅" if bought else "❌"
        text += f"{status} {item}\n"
        keyboard.add(types.InlineKeyboardButton(text=f"Купил: {item}", callback_query_data=f"buy_{item}"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def callback_buy(call):
    item = call.data.replace("buy_", "")
    if item in shopping_list:
        shopping_list[item] = True # Помечаем как куплено
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Обновляю...")
        show(call.message)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def add(message):
    msg = bot.send_message(message.chat.id, "Напиши, что добавить (можно через запятую):")
    bot.register_next_step_handler(msg, save_item)

def save_item(message):
    items = message.text.split(',')
    for i in items:
        shopping_list[i.strip()] = False
    bot.send_message(message.chat.id, "Добавил!")
    show(message)

bot.polling(none_stop=True)
