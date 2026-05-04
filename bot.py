import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)
# База данных: {Название: Куплено(True/False)}
shopping_list = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, "Доступ закрыт.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов. Используйте кнопки ниже:", reply_markup=markup)

def get_keyboard():
    """Создает только один блок кнопок, где статус товара (🛒/✅) внутри самой кнопки"""
    markup = types.InlineKeyboardMarkup()
    for item, bought in shopping_list.items():
        icon = "✅" if bought else "🛒"
        # Одна кнопка на один товар, текст кнопки меняется динамически
        markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    return markup

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    if not shopping_list:
        bot.send_message(message.chat.id, "Список пуст.")
        return
    bot.send_message(message.chat.id, "Ваш список покупок:", reply_markup=get_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("tgl_"))
def handle_toggle(call):
    item = call.data.replace("tgl_", "")
    if item in shopping_list:
        # Переключаем статус товара
        shopping_list[item] = not shopping_list[item]
            
    # Редактируем только кнопки в том же сообщении, чтобы не спамить
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard())
    except:
        pass
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def ask_add(message):
    msg = bot.send_message(message.chat.id, "Напиши продукты (можно через запятую или списком):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    # Корректно разбиваем ввод пользователя на отдельные товары
    raw_text = message.text.replace('\n', ',')
    items = [i.strip() for i in raw_text.split(',') if i.strip()]
    
    for i in items:
        if i not in shopping_list:
            shopping_list[i] = False
    
    # Сразу выводим компактный список с кнопками
    bot.send_message(message.chat.id, "Добавлено! Вот ваш список:", reply_markup=get_keyboard())

if __name__ == "__main__":
    bot.polling(none_stop=True)
