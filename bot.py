import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)
# Храним список в памяти (после перезагрузки очистится)
shopping_list = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, f"Нет доступа. ID: {message.from_user.id}")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов! Используйте кнопки меню:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    if not shopping_list:
        bot.send_message(message.chat.id, "В списке пока пусто.")
        return
    
    # Формируем сообщение с кнопками под каждым продуктом
    for item, bought in shopping_list.items():
        status = "✅" if bought else "🛒"
        kb = types.InlineKeyboardMarkup()
        if not bought:
            kb.add(types.InlineKeyboardButton(text=f"Отметить: {item}", callback_data=f"buy_{item}"))
        else:
            kb.add(types.InlineKeyboardButton(text=f"Удалить: {item}", callback_data=f"del_{item}"))
        
        bot.send_message(message.chat.id, f"{status} {item}", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("buy_"):
        item = call.data.replace("buy_", "")
        shopping_list[item] = True
        bot.answer_callback_query(call.id, "Куплено!")
    
    elif call.data.startswith("del_"):
        item = call.data.replace("del_", "")
        if item in shopping_list:
            del shopping_list[item]
        bot.answer_callback_query(call.id, "Удалено!")
    
    # После нажатия обновляем вид (удаляем старое сообщение и шлем новое)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    # Если список не пуст, можно вызвать показ списка снова, но лучше просто подтвердить действие

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def ask_add(message):
    msg = bot.send_message(message.chat.id, "Напиши, что добавить (через запятую или каждое с новой строки):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    # Учитываем и запятые, и переносы строк
    text = message.text.replace('\n', ',')
    items = [i.strip() for i in text.split(',') if i.strip()]
    
    for i in items:
        shopping_list[i] = False
    
    bot.send_message(message.chat.id, "Добавил! Вот ваш актуальный список:")
    show_list(message) # Автоматически показываем список с кнопками

if __name__ == "__main__":
    bot.polling(none_stop=True)
