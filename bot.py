import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)
# Храним товары: {название: True/False}
shopping_list = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, f"Доступ ограничен. ID: {message.from_user.id}")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов! Список покупок активен.", reply_markup=markup)

def render_list():
    """Формирует текст списка и кнопки-переключатели"""
    if not shopping_list:
        return "Список пуст.", None
    
    display_text = "📝 **Ваш список покупок:**\n"
    keyboard = types.InlineKeyboardMarkup()
    
    for item, bought in shopping_list.items():
        status_icon = "✅" if bought else "🛒"
        display_text += f"\n{status_icon} {item}"
        
        # Кнопка просто с названием товара
        keyboard.add(types.InlineKeyboardButton(text=item, callback_data=f"tgl_{item}"))
    
    return display_text, keyboard

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    text, kb = render_list()
    bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("tgl_"))
def handle_click(call):
    item = call.data.replace("tgl_", "")
    
    if item in shopping_list:
        # Инвертируем статус: если было False, станет True, и наоборот
        shopping_list[item] = not shopping_list[item]
            
    text, kb = render_list()
    try:
        # Обновляем сообщение с новым значком
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                             reply_markup=kb, parse_mode="Markdown")
    except:
        pass
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def start_add(message):
    msg = bot.send_message(message.chat.id, "Введите продукты (через запятую или с новой строки):")
    bot.register_next_step_handler(msg, save_items)

def save_items(message):
    new_text = message.text.replace('\n', ',')
    items = [i.strip() for i in new_text.split(',') if i.strip()]
    
    for i in items:
        # Новые товары всегда добавляются как "не купленные" (False)
        if i not in shopping_list:
            shopping_list[i] = False
    
    text, kb = render_list()
    bot.send_message(message.chat.id, "Добавлено в список!")
    bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode="Markdown")

if __name__ == "__main__":
    bot.polling(none_stop=True)
