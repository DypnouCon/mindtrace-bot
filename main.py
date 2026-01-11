import os
import telebot
from telebot import types
import threading
import time
import requests
import sqlite3
import random
from flask import Flask
from huggingface_hub import InferenceClient

# --- Настройки ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')
bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
app = Flask(__name__)

# --- Работа с Базой Данных ---
def init_db():
    conn = sqlite3.connect('mindtrace.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (cid INTEGER PRIMARY KEY, lang TEXT, char TEXT, name TEXT, 
                  birth_date TEXT, birth_time TEXT, request TEXT, heart TEXT, 
                  element TEXT, shadow TEXT, portrait TEXT, step TEXT)''')
    conn.commit()
    conn.close()

def save_user(cid, data):
    conn = sqlite3.connect('mindtrace.db', check_same_thread=False)
    c = conn.cursor()
    fields = ['lang', 'char', 'name', 'birth_date', 'birth_time', 'request', 'heart', 'element', 'shadow', 'portrait', 'step']
    # Гарантируем, что все ключи есть в словаре
    vals = [data.get(f, None) for f in fields]
    query = f"INSERT OR REPLACE INTO users (cid, {', '.join(fields)}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    c.execute(query, (cid, *vals))
    conn.commit()
    conn.close()

def load_user(cid):
    conn = sqlite3.connect('mindtrace.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE cid=?", (cid,))
    row = c.fetchone()
    conn.close()
    if row:
        fields = ['cid', 'lang', 'char', 'name', 'birth_date', 'birth_time', 'request', 'heart', 'element', 'shadow', 'portrait', 'step']
        return dict(zip(fields, row))
    return None

init_db()
chat_histories = {}

# --- Тексты ---
DISCLAIMER = (
    "<b>Завеса Тайны (Legal Disclaimer):</b>\n\n"
    "«MindTrace — это пространство самопознания. Я — алгоритм, "
    "но я не врач. Мои слова — не диагноз. Если тебе плохо, обратись к специалисту.»"
)

# --- Обработка команд ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    print(f"[LOG] Start command from {cid}")
    user = load_user(cid)
    
    if user and user.get('portrait'):
        bot.send_message(cid, f"Рад твоему возвращению, {user.get('name', 'странник')}. Я помню наш путь. О чем ты хочешь спросить?")
        return

    # Новая сессия
    save_user(cid, {'step': 'language'})
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
               types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    
    bot.send_message(cid, DISCLAIMER, parse_mode='HTML')
    bot.send_message(cid, "На каком языке мы начнем наше погружение?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    cid = call.message.chat.id
    lang = call.data.split('_')[1]
    save_user(cid, {'lang': lang, 'step': 'char_selection'})
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ори 🕯️", callback_data="char_ori"),
               types.InlineKeyboardButton("Эйра ❄️", callback_data="char_eira"))
    
    bot.edit_message_text("Выбери своего Проводника:\n\n<b>Ори</b> — Мудрец\n<b>Эйра</b> — Исцеляющая тишина", 
                          cid, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_user(cid) or {}
    user['char'] = char
    user['step'] = 'get_name'
    save_user(cid, user)
    
    msg = "Как мне называть тебя?"
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    cid = m.chat.id
    user = load_user(cid)
    if not user: return

    step = user.get('step')
    
    if step == 'get_name':
        user['name'] = m.text
        user['step'] = 'get_date'
        save_user(cid, user)
        bot.send_message(cid, f"{m.text}, в какой день ты родился? (дд.мм.гггг)")
        
    elif step == 'get_date':
        user['birth_date'] = m.text
        user['step'] = 'get_time'
        save_user(cid, user)
        bot.send_message(cid, "В какой час? (или 'не знаю')")
        
    elif step == 'get_time':
        user['birth_time'] = m.text
        user['step'] = 'get_request'
        save_user(cid, user)
        bot.send_message(cid, "Твой главный запрос сегодня?")
        
    elif step == 'get_request':
        user['request'] = m.text
        user['step'] = 'get_heart'
        save_user(cid, user)
        bot.send_message(cid, "Какое чувство в сердце сейчас?")
        
    elif step == 'get_heart':
        user['heart'] = m.text
        user['step'] = 'get_element'
        save_user(cid, user)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_Огонь"), 
                   types.InlineKeyboardButton("Вода 🌊", callback_data="elem_Вода"),
                   types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_Воздух"), 
                   types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_Земля"))
        bot.send_message(cid, "Твоя стихия?", reply_markup=markup)
        
    elif step == 'free_talk':
        # Логика свободного общения
        bot.send_chat_action(cid, 'typing')
        if cid not in chat_histories: chat_histories[cid] = []
        chat_histories[cid].append({"role": "user", "content": m.text})
        
        sys_p = f"Ты {'Ори' if user['char']=='ori' else 'Эйра'}. Суть: {user['portrait'][:500]}"
        msgs = [{"role": "system", "content": sys_p}] + chat_histories[cid][-5:]
        
        try:
            res = client.chat_completion(messages=msgs, max_tokens=500)
            bot.send_message(cid, res.choices[0].message.content)
            chat_histories[cid].append({"role": "assistant", "content": res.choices[0].message.content})
        except:
            bot.send_message(cid, "Я в тумане...")

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem_final(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_user(cid)
    user['element'] = elem
    user['step'] = 'get_shadow_input' # Промежуточный шаг
    save_user(cid, user)
    bot.edit_message_text(f"Стихия: {elem}. А теперь скажи: что тебя больше всего бесит в людях? (Это твоя Тень)", cid, call.message.message_id)
    # Переключаем шаг на ожидание текста тени
    user['step'] = 'wait_shadow'
    save_user(cid, user)

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'wait_shadow')
def final_portrait_gen(m):
    cid = m.chat.id
    user = load_user(cid)
    user['shadow'] = m.text
    bot.send_message(cid, "Плету твой портрет... Подожди.")
    
    # Тут логика генерации портрета (как в прошлых версиях)
    prompt = f"Напиши глубокий портрет для {user['name']}. Тень: {user['shadow']}, Стихия: {user['element']}."
    try:
        res = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1000)
        portrait = res.choices[0].message.content
        user['portrait'] = portrait
        user['step'] = 'free_talk'
        save_user(cid, user)
        bot.send_message(cid, portrait)
    except:
        bot.send_message(cid, "Ошибка звезд.")

# --- Flask ---
@app.route('/')
def home(): return "MindTrace Fix Live", 200

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("[LOG] Polling started...")
    bot.infinity_polling(timeout=20)
