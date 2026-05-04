import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Структура данных: { "Название списка": { "товар": False, "товар2": True } }
all_lists = {"Основной": {}}
# Храним, в каком списке сейчас находится каждый пользователь
user_current_list = {}
last_msg_id = {}

def delete_msg(chat_id):
    if chat_id in last_msg_id:
        try: bot.delete_message(chat_id, last_msg_id[chat_id])
        except: pass

def get_main_menu_kb():
    """Клавиатура со списком всех созданных списков"""
    markup = types.InlineKeyboardMarkup()
    for list_name in all_lists.keys():
        markup.add(types.InlineKeyboardButton(text=f"📂 {list_name}", callback_data=f"open_list_{list_name}"))
    markup.add(types.InlineKeyboardButton(text="✨ Создать новый список", callback_data="create_new_list"))
    return markup

def get_list_kb(list_name, edit_mode=False):
    """Клавиатура конкретного списка"""
    markup = types.InlineKeyboardMarkup()
    items = all_lists.get(list_name, {})
    
    for item, bought in items.items():
        if edit_mode:
            markup.add(types.InlineKeyboardButton(text=f"❌ Удалить: {item}", callback_data=f"del_{item}"))
        else:
            icon = "✅" if bought else "🛒"
            markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    
    markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт", callback_data="add_item"))
    if edit_mode:
        markup.add(types.InlineKeyboardButton(text="✅ Готово (выход из правки)", callback_data="view_mode"))
    else:
        markup.add(types.InlineKeyboardButton(text="✍️ Редактировать список", callback_data="edit_mode"))
    
    markup.add(types.InlineKeyboardButton(text="⬅️ Назад ко всем спискам", callback_data="back_to_main"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS: return
    res = bot.send_message(message.chat.id, "Выберите список или создайте новый:", reply_markup=get_main_menu_kb())
    last_msg_id[message.chat.id] = res.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_queries(call):
    chat_id = call.message.chat.id
    global all_lists
    
    bot.answer_callback_query(call.id)

    # Открыть конкретный список
    if call.data.startswith("open_list_"):
        list_name = call.data.replace("open_list_", "")
        user_current_list[chat_id] = list_name
        bot.edit_message_text(f"📋 Список: {list_name}", chat_id, call.message.message_id, reply_markup=get_list_kb(list_name))

    # Создать новый список
    elif call.data == "create_new_list":
        msg = bot.send_message(chat_id, "Введите название для нового списка:")
        bot.register_next_step_handler(msg, process_create_list)

    # Назад в главное меню
    elif call.data == "back_to_main":
        bot.edit_message_text("Ваши списки:", chat_id, call.message.message_id, reply_markup=get_main_menu_kb())

    # Режимы внутри списка
    elif call.data == "edit_mode":
        list_name = user_current_list.get(chat_id)
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(list_name, edit_mode=True))

    elif call.data == "view_mode":
        list_name = user_current_list.get(chat_id)
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(list_name, edit_mode=False))

    # Добавление товара
    elif call.data == "add_item":
        msg = bot.send_message(chat_id, f"Что добавить в список '{user_current_list[chat_id]}'?")
        bot.register_next_step_handler(msg, process_add_item)

    # Переключение статуса (куплено/нет)
    elif call.data.startswith("tgl_"):
        item = call.data.replace("tgl_", "")
        list_name = user_current_list.get(chat_id)
        all_lists[list_name][item] = not all_lists[list_name][item]
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(list_name))

    # Удаление товара
    elif call.data.startswith("del_"):
        item = call.data.replace("del_", "")
        list_name = user_current_list.get(chat_id)
        all_lists[list_name].pop(item, None)
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(list_name, edit_mode=True))

def process_create_list(message):
    list_name = message.text.strip()
    if list_name and list_name not in all_lists:
        all_lists[list_name] = {}
    
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    
    delete_msg(message.chat.id)
    res = bot.send_message(message.chat.id, "Список создан! Выберите его:", reply_markup=get_main_menu_kb())
    last_msg_id[message.chat.id] = res.message_id

def process_add_item(message):
    list_name = user_current_list.get(message.chat.id)
    if message.text and list_name:
        items = [i.strip() for i in message.text.replace('\n', ',').split(',') if i.strip()]
        for i in items:
            all_lists[list_name][i] = False
    
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    
    delete_msg(message.chat.id)
    res = bot.send_message(message.chat.id, f"Обновлено в '{list_name}':", reply_markup=get_list_kb(list_name))
    last_msg_id[message.chat.id] = res.message_id

if __name__ == "__main__":
    bot.polling(none_stop=True)
