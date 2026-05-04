import os
import telebot
from telebot import types

# Инициализация бота
TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Данные пользователя (хранятся в оперативной памяти)
shopping_list = {}
last_list_msg_id = {}

def delete_message_safe(chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

def get_keyboard(edit_mode=False):
    markup = types.InlineKeyboardMarkup()
    
    if not shopping_list and not edit_mode:
        return None

    for item, bought in shopping_list.items():
        if edit_mode:
            # Режим удаления: кнопки с крестиками
            markup.add(types.InlineKeyboardButton(text=f"❌ Удалить: {item}", callback_data=f"del_{item}"))
        else:
            # Обычный режим: кнопки со статусом (корзинка/галочка)
            icon = "✅" if bought else "🛒"
            markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    
    if edit_mode:
        # В режиме редактирования добавляем кнопку добавления и сохранения
        markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_item_action"))
        markup.add(types.InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_all"))
        markup.add(types.InlineKeyboardButton(text="✅ Сохранить", callback_data="view_mode"))
    else:
        # В обычном режиме только кнопка перехода к редактированию
        markup.add(types.InlineKeyboardButton(text="✍️ Редактировать", callback_data="edit_mode"))
    
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS: return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Список", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов! Используйте меню для управления списком.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Список")
def show_list(message):
    if message.from_user.id not in ALLOWED_USERS: return
    delete_message_safe(message.chat.id, message.message_id)
    
    # Удаляем старое сообщение со списком, если оно было
    if message.chat.id in last_list_msg_id:
        delete_message_safe(message.chat.id, last_list_msg_id[message.chat.id])
    
    kb = get_keyboard()
    msg_text = "Ваш список покупок:" if kb else "Список пуст."
    
    # Если список пуст, даем кнопку "Добавить" сразу
    if not kb:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_item_action"))

    sent_msg = bot.send_message(message.chat.id, msg_text, reply_markup=kb)
    last_list_msg_id[message.chat.id] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    global shopping_list
    if call.from_user.id not in ALLOWED_USERS: return
    
    # Сразу подтверждаем получение запроса, чтобы кнопка не "висела"
    bot.answer_callback_query(call.id)

    if call.data == "add_item_action":
        # Запрашиваем ввод продукта
        msg = bot.send_message(call.message.chat.id, "Введите название продукта (или несколько через запятую):")
        bot.register_next_step_handler(msg, process_adding_step, return_to_edit=True)
    
    elif call.data == "edit_mode":
        bot.edit_message_text("🛠 Режим редактирования:", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))
                             
    elif call.data == "view_mode":
        bot.edit_message_text("Ваш список покупок:", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=False))

    elif call.data.startswith("tgl_"):
        item = call.data.replace("tgl_", "")
        if item in shopping_list:
            shopping_list[item] = not shopping_list[item]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard())

    elif call.data.startswith("del_"):
        item = call.data.replace("del_", "")
        shopping_list.pop(item, None)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))

    elif call.data == "clear_all":
        shopping_list = {}
        bot.edit_message_text("Список пуст.", call.message.chat.id, call.message.message_id, reply_markup=get_keyboard(edit_mode=True))

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def manual_add(message):
    if message.from_user.id not in ALLOWED_USERS: return
    delete_message_safe(message.chat.id, message.message_id)
    msg = bot.send_message(message.chat.id, "Что добавить?")
    bot.register_next_step_handler(msg, process_adding_step, return_to_edit=False)

def process_adding_step(message, return_to_edit=False):
    if not message.text: return
    
    # Добавляем продукты в список
    raw_text = message.text.replace('\n', ',')
    items = [i.strip() for i in raw_text.split(',') if i.strip()]
    for i in items:
        if i not in shopping_list:
            shopping_list[i] = False

    # Удаляем сообщение пользователя и вопрос бота для чистоты чата
    delete_message_safe(message.chat.id, message.message_id)
    delete_message_safe(message.chat.id, message.message_id - 1)

    # Обновляем основное сообщение со списком
    if message.chat.id in last_list_msg_id:
        delete_message_safe(message.chat.id, last_list_msg_id[message.chat.id])
    
    text = "🛠 Режим редактирования:" if return_to_edit else "Список покупок:"
    sent_msg = bot.send_message(message.chat.id, text, reply_markup=get_keyboard(edit_mode=return_to_edit))
    last_list_msg_id[message.chat.id] = sent_msg.message_id

if __name__ == "__main__":
    bot.polling(none_stop=True)
