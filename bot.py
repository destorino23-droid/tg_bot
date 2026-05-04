import os
import telebot
from telebot import types

TOKEN = os.getenv('TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(x.strip()) for x in raw_users.split(',') if x.strip()]

bot = telebot.TeleBot(TOKEN)

# Данные: { "Название списка": { "товар": False } }
all_lists = {}
user_context = {} # Храним, в каком списке сейчас юзер
last_msg_id = {}

def delete_old_menu(chat_id):
    if chat_id in last_msg_id:
        try: bot.delete_message(chat_id, last_msg_id[chat_id])
        except: pass

def get_list_kb(list_name, edit_mode=False):
    markup = types.InlineKeyboardMarkup()
    items = all_lists.get(list_name, {})
    
    for item, bought in items.items():
        if edit_mode:
            markup.add(types.InlineKeyboardButton(text=f"❌ Удалить: {item}", callback_data=f"del_{item}"))
        else:
            icon = "✅" if bought else "🛒"
            markup.add(types.InlineKeyboardButton(text=f"{icon} {item}", callback_data=f"tgl_{item}"))
    
    markup.add(types.InlineKeyboardButton(text="➕ Добавить продукт в этот список", callback_data="add_to_this"))
    if edit_mode:
        markup.add(types.InlineKeyboardButton(text="✅ Сохранить", callback_data="view_mode"))
    else:
        markup.add(types.InlineKeyboardButton(text="✍️ Редактировать (удаление)", callback_data="edit_mode"))
    
    markup.add(types.InlineKeyboardButton(text="🗑 Удалить ВЕСЬ список", callback_data="delete_full_list"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS: return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Списки", "➕ Добавить")
    bot.send_message(message.chat.id, "Бот готов! Создайте новый список или посмотрите текущие.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 Списки")
def show_all_lists(message):
    if message.from_user.id not in ALLOWED_USERS: return
    delete_old_menu(message.chat.id)
    bot.delete_message(message.chat.id, message.message_id)
    
    if not all_lists:
        bot.send_message(message.chat.id, "У вас пока нет списков. Нажмите «➕ Добавить», чтобы создать первый.")
        return

    markup = types.InlineKeyboardMarkup()
    for name in all_lists.keys():
        markup.add(types.InlineKeyboardButton(text=f"📂 {name}", callback_data=f"open_{name}"))
    
    res = bot.send_message(message.chat.id, "Ваши списки:", reply_markup=markup)
    last_msg_id[message.chat.id] = res.message_id

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def create_new_list_start(message):
    if message.from_user.id not in ALLOWED_USERS: return
    bot.delete_message(message.chat.id, message.message_id)
    msg = bot.send_message(message.chat.id, "Введите название для НОВОГО списка:")
    bot.register_next_step_handler(msg, process_list_creation)

def process_list_creation(message):
    name = message.text.strip()
    if name:
        all_lists[name] = {}
        user_context[message.chat.id] = name
        bot.delete_message(message.chat.id, message.message_id)
        bot.delete_message(message.chat.id, message.message_id - 1)
        
        res = bot.send_message(message.chat.id, f"Список '{name}' создан! Теперь добавьте в него продукты (через запятую):")
        bot.register_next_step_handler(res, process_items_addition)

def process_items_addition(message):
    list_name = user_context.get(message.chat.id)
    if message.text and list_name:
        items = [i.strip() for i in message.text.replace('\n', ',').split(',') if i.strip()]
        for i in items:
            all_lists[list_name][i] = False
            
    bot.delete_message(message.chat.id, message.message_id)
    bot.delete_message(message.chat.id, message.message_id - 1)
    
    res = bot.send_message(message.chat.id, f"📋 Список: {list_name}", reply_markup=get_list_kb(list_name))
    last_msg_id[message.chat.id] = res.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    if call.data.startswith("open_"):
        name = call.data.replace("open_", "")
        user_context[chat_id] = name
        bot.edit_message_text(f"📋 Список: {name}", chat_id, call.message.message_id, reply_markup=get_list_kb(name))

    elif call.data == "add_to_this":
        msg = bot.send_message(chat_id, "Что добавить в этот список?")
        bot.register_next_step_handler(msg, process_items_addition)

    elif call.data == "edit_mode":
        name = user_context[chat_id]
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(name, edit_mode=True))

    elif call.data == "view_mode":
        name = user_context[chat_id]
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(name, edit_mode=False))

    elif call.data.startswith("tgl_"):
        item = call.data.replace("tgl_", "")
        name = user_context[chat_id]
        all_lists[name][item] = not all_lists[name][item]
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(name))

    elif call.data.startswith("del_"):
        item = call.data.replace("del_", "")
        name = user_context[chat_id]
        all_lists[name].pop(item, None)
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_list_kb(name, edit_mode=True))

    elif call.data == "delete_full_list":
        name = user_context[chat_id]
        all_lists.pop(name, None)
        bot.edit_message_text("Список полностью удален.", chat_id, call.message.message_id)

if __name__ == "__main__":
    bot.polling(none_stop=True)
