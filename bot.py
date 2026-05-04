import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Данные пользователя (в памяти)
shopping_list = {}
# Храним ID последнего сообщения со списком, чтобы его удалить
last_list_msg_id = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, "Нет доступа.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов! Используйте меню:", reply_markup=markup)

def delete_old_menu(chat_id):
    """Удаляет предыдущее сообщение со списком, если оно существует"""
    if chat_id in last_list_msg_id:
        try:
            bot.delete_message(chat_id, last_list_msg_id[chat_id])
        except:
            pass # Если сообщение уже удалено вручную или устарело

def get_keyboard(edit_mode=False):
    markup = types.InlineKeyboardMarkup()
    if not shopping_list:
        if edit_mode:
            markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_from_edit"))
            markup.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="view_mode"))
            return markup
        return None

    for item, bought in shopping_list.items():
        if edit_mode:
            markup.add(types.InlineKeyboardButton(text=f"❌ Удалить: {item}", callback_data=f"del_{item}"))
        else:
            icon = "✅" if bought else "🛒"
            markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    
    if edit_mode:
        markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_from_edit"))
        markup.add(types.InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_all"))
        markup.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="view_mode"))
    else:
        markup.add(types.InlineKeyboardButton(text="✍️ Редактировать список", callback_data="edit_mode"))
    return markup

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    delete_old_menu(message.chat.id)
    kb = get_keyboard()
    if kb:
        sent_msg = bot.send_message(message.chat.id, "Ваш список покупок:", reply_markup=kb)
        last_list_msg_id[message.chat.id] = sent_msg.message_id
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_from_edit"))
        sent_msg = bot.send_message(message.chat.id, "Список пока пуст.", reply_markup=markup)
        last_list_msg_id[message.chat.id] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    global shopping_list
    
    if call.data.startswith("tgl_"):
        item = call.data.replace("tgl_", "")
        if item in shopping_list:
            shopping_list[item] = not shopping_list[item]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard())
    
    elif call.data == "edit_mode":
        bot.edit_message_text("🛠 Режим редактирования:", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))
                             
    elif call.data == "view_mode":
        bot.edit_message_text("Ваш список покупок:", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=False))

    elif call.data == "add_from_edit":
        bot.answer_callback_query(call.id)
        ask_add(call.message)

    elif call.data.startswith("del_"):
        item = call.data.replace("del_", "")
        if item in shopping_list:
            del shopping_list[item]
        kb = get_keyboard(edit_mode=True)
        if kb:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            bot.edit_message_text("Список пуст.", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))

    elif call.data == "clear_all":
        shopping_list = {}
        bot.edit_message_text("Список полностью очищен.", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))
        
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def ask_add(message):
    msg = bot.send_message(message.chat.id, "Что добавить? (можно через запятую или списком):")
    bot.register_next_step_handler(msg, process_adding)

def process_adding(message):
    # Удаляем старое меню перед выводом нового после добавления
    delete_old_menu(message.chat.id)
    
    raw_text = message.text.replace('\n', ',')
    items = [i.strip() for i in raw_text.split(',') if i.strip()]
    for i in items:
        if i not in shopping_list:
            shopping_list[i] = False
    
    sent_msg = bot.send_message(message.chat.id, "Список обновлен:", reply_markup=get_keyboard())
    last_list_msg_id[message.chat.id] = sent_msg.message_id

if __name__ == "__main__":
    bot.polling(none_stop=True)
