import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)
# База данных в памяти: {Название: Статус(True/False)}
shopping_list = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, f"Доступ закрыт.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов. Нажмите '➕ Добавить', чтобы внести продукты.", reply_markup=markup)

def get_keyboard():
    """Создает только блок кнопок, где иконка внутри текста кнопки"""
    markup = types.InlineKeyboardMarkup()
    for item, bought in shopping_list.items():
        icon = "✅" if bought else "🛒"
        # Текст кнопки меняется в зависимости от статуса
        markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    if not shopping_list:
        bot.send_message(message.chat.id, "Список пуст.")
        return
    
    bot.send_message(message.chat.id, "Ваш список (нажмите, чтобы отметить):", reply_markup=get_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("tgl_"))
def handle_toggle(call):
    item = call.data.replace("tgl_", "")
    
    if item in shopping_list:
        # Меняем статус на противоположный
        shopping_list[item] = not shopping_list[item]
            
    # Обновляем только кнопки в том же сообщении
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard())
    except:
        pass
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def ask_add(message):
    msg = bot.send_message(message.chat.id, "Что добавить? (можно сразу несколько через запятую):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    raw_text = message.text.replace('\n', ',')
    items = [i.strip() for i in raw_text.split(',') if i.strip()]
    
    for i in items:
        if i not in shopping_list:
            shopping_list[i] = False
    
    bot.send_message(message.chat.id, "Добавлено! Вот ваш список:", reply_markup=get_keyboard())

if __name__ == "__main__":
    bot.polling(none_stop=True)
