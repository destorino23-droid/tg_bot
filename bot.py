import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Данные в памяти
shopping_list = {}
last_list_msg_id = {}

def delete_message_safe(chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

def delete_old_menu(chat_id):
    if chat_id in last_list_msg_id:
        delete_message_safe(chat_id, last_list_msg_id[chat_id])

def get_keyboard():
    """Создает кнопки только для переключения статуса и входа в режим правки"""
    if not shopping_list:
        return None
    
    markup = types.InlineKeyboardMarkup()
    for item, bought in shopping_list.items():
        icon = "✅" if bought else "🛒"
        markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    
    markup.add(types.InlineKeyboardButton(text="✍️ Редактировать текст списка", callback_data="edit_text_mode"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS: return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    if message.from_user.id not in ALLOWED_USERS: return
    delete_message_safe(message.chat.id, message.message_id)
    delete_old_menu(message.chat.id)
    
    kb = get_keyboard()
    if kb:
        sent_msg = bot.send_message(message.chat.id, "Ваш список покупок:", reply_markup=kb)
        last_list_msg_id[message.chat.id] = sent_msg.message_id
    else:
        bot.send_message(message.chat.id, "Список пуст. Нажми '➕ Добавить', чтобы внести продукты.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    global shopping_list
    if call.from_user.id not in ALLOWED_USERS: return
    
    if call.data.startswith("tgl_"):
        item = call.data.replace("tgl_", "")
        if item in shopping_list:
            shopping_list[item] = not shopping_list[item]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard())
    
    elif call.data == "edit_text_mode":
        # Формируем текст текущего списка для редактирования
        text_list = "\n".join(shopping_list.keys())
        bot.send_message(call.message.chat.id, "Скопируй, отредактируй и отправь мне обратно:")
        bot.send_message(call.message.chat.id, f"```{text_list}```", parse_mode="Markdown")
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def ask_add(message):
    if message.from_user.id not in ALLOWED_USERS: return
    delete_message_safe(message.chat.id, message.message_id)
    msg = bot.send_message(message.chat.id, "Что добавить? (через запятую или списком):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    delete_message_safe(message.chat.id, message.message_id)
    delete_old_menu(message.chat.id)
    
    if message.text:
        raw_text = message.text.replace('\n', ',')
        items = [i.strip() for i in raw_text.split(',') if i.strip()]
        for i in items:
            if i not in shopping_list:
                shopping_list[i] = False
    
    sent_msg = bot.send_message(message.chat.id, "Список обновлен:", reply_markup=get_keyboard())
    last_list_msg_id[message.chat.id] = sent_msg.message_id

# Дополнительный обработчик: если пользователь просто присылает текст, 
# когда в списке уже что-то есть — считаем это полной заменой списка (редактированием)
@bot.message_handler(func=lambda m: True)
def handle_manual_edit(message):
    global shopping_list
    if message.from_user.id not in ALLOWED_USERS: return
    
    # Если в сообщении несколько строк или это явный ответ на редактирование
    delete_message_safe(message.chat.id, message.message_id)
    delete_old_menu(message.chat.id)

    raw_text = message.text.replace('\n', ',')
    new_items = [i.strip() for i in raw_text.split(',') if i.strip()]
    
    # Создаем новый список, сохраняя статусы "куплено" для тех, кто остался
    new_list = {}
    for item in new_items:
        new_list[item] = shopping_list.get(item, False)
    
    shopping_list = new_list
    
    sent_msg = bot.send_message(message.chat.id, "Список обновлен (режим правки):", reply_markup=get_keyboard())
    last_list_msg_id[message.chat.id] = sent_msg.message_id

if __name__ == "__main__":
    bot.polling(none_stop=True)
