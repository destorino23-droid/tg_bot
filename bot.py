import os
import telebot
from telebot import types

# Считываем настройки из Railway
TOKEN = os.getenv('TOKEN')
ALLOWED_USERS = [int(x.strip()) for x in os.getenv('ALLOWED_USERS', '').split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Временное хранилище (в идеале тут должна быть БД, но для начала хватит и этого)
# Формат: {'название': {'bought': False}}
shopping_list = {}

def check_access(message):
    return message.from_user.id in ALLOWED_USERS

@bot.message_handler(commands=['start'])
def start(message):
    if not check_access(message):
        bot.send_message(message.chat.id, f"Доступ запрещен. Ваш ID: {message.from_user.id}")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🍎 Показать список", "➕ Добавить продукт")
    markup.add("🗑 Очистить купленное")
    bot.send_message(message.chat.id, "Бот готов к работе! Пользуйся меню ниже:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🍎 Показать список")
def show_list(message):
    if not check_access(message): return
    if not shopping_list:
        bot.send_message(message.chat.id, "Список пока пуст.")
        return

    text = "📝 **Ваш список продуктов:**\n\n"
    keyboard = types.InlineKeyboardMarkup()
    
    for item, data in shopping_list.items():
        status = "✅" if data['bought'] else "🛒"
        text += f"{status} {item}\n"
        # Кнопка для переключения статуса
        btn_text = f"{'Вернуть' if data['bought'] else 'Куплено'}: {item}"
        keyboard.add(types.InlineKeyboardButton(text=btn_text, callback_query_id=f"toggle_{item}"))

    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_item(call):
    item = call.data.replace("toggle_", "")
    if item in shopping_list:
        shopping_list[item]['bought'] = not shopping_list[item]['bought']
        # Обновляем сообщение со списком
        show_list(call.message)
        bot.answer_callback_query(call.id, f"Статус {item} изменен")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить продукт")
def add_prompt(message):
    if not check_access(message): return
    msg = bot.send_message(message.chat.id, "Напишите название продукта (или список через запятую):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    items = [i.strip() for i in message.text.split(',')]
    for item in items:
        if item:
            shopping_list[item] = {'bought': False}
    bot.send_message(message.chat.id, f"Добавлено: {', '.join(items)}")
    show_list(message)

@bot.message_handler(func=lambda m: m.text == "🗑 Очистить купленное")
def clear_bought(message):
    global shopping_list
    shopping_list = {k: v for k, v in shopping_list.items() if not v['bought']}
    bot.send_message(message.chat.id, "Купленные товары удалены из списка.")
    show_list(message)

bot.polling(none_stop=True)
