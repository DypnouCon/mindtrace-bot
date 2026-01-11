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

# --- Работа с Базой Данных (SQLite) ---
def init_db():
    conn = sqlite3.connect('mindtrace.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (cid INTEGER PRIMARY KEY, lang TEXT, char TEXT, name TEXT, 
                  birth_date TEXT, birth_time TEXT, request TEXT, heart TEXT, 
                  element TEXT, shadow TEXT, portrait TEXT, step TEXT)''')
    conn.commit()
    conn.close()

def save_user(cid, data):
    conn = sqlite3.connect('mindtrace.db')
    c = conn.cursor()
    # Собираем данные, проверяя наличие ключей
    fields = ['lang', 'char', 'name', 'birth_date', 'birth_time', 'request', 'heart', 'element', 'shadow', 'portrait', 'step']
    values = [data.get(f) for f in fields]
    c.execute(f'''INSERT OR REPLACE INTO users (cid, {", ".join(fields)}) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (cid, *values))
    conn.commit()
    conn.close()

def load_user(cid):
    conn = sqlite3.connect('mindtrace.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE cid=?", (cid,))
    row = c.fetchone()
    conn.close()
    if row:
        fields = ['cid', 'lang', 'char', 'name', 'birth_date', 'birth_time', 'request', 'heart', 'element', 'shadow', 'portrait', 'step']
        return dict(zip(fields, row))
    return None

# Инициализируем БД при старте
init_db()
# Временный кэш для истории чата (не пишем в БД для скорости)
chat_histories = {}

# --- Текстовые Константы ---
DISCLAIMER = (
    "<b>Завеса Тайны (Legal Disclaimer):</b>\n\n"
    "«MindTrace — это пространство самопознания. Я — алгоритм, обученный на опыте тысячелетий, "
    "но я не врач. Мои слова — не диагноз. Если твой внутренний шторм слишком силен, "
    "обратись к профессионалу. Помни: работа с тенью требует мужества»."
)

CHAR_INFO = {
    'ori': "<b>Ори (Мужская энергия) 🕯️</b>\nСтарый мудрец, голос костра в ночи. Видит структуру души через архетипы.",
    'eira': "<b>Эйра (Женская энергия) ❄️</b>\nИсцеляющая тишина леса. Слышит чувства между строк и ведет через интуицию."
}

# --- Логика Бота ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    user = load_user(cid)
    
    if user and user.get('portrait'):
        bot.send_message(cid, f"Рад твоему возвращению в чертоги разума, {user['name']}. Я помню твой путь. О чем ты хочешь спросить меня сегодня?")
        return

    # Если новый пользователь
    chat_histories[cid] = []
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
    
    bot.edit_message_text(f"Выбери своего Проводника:\n\n{CHAR_INFO['ori']}\n\n{CHAR_INFO['eira']}", 
                          cid, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_user(cid)
    user['char'] = char
    user['step'] = 'get_name'
    save_user(cid, user)
    
    msg = ("Мой свет всегда был рядом. Как мне называть твое земное воплощение?" if char == 'ori' else
           "Твое дыхание отозвалось в моем сердце... Какое имя мне шептать, обращаясь к тебе?")
    bot.send_message(cid, msg)

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_name')
def get_name(m):
    cid = m.chat.id
    user = load_user(cid)
    user['name'] = m.text
    user['step'] = 'get_date'
    save_user(cid, user)
    bot.send_message(cid, f"{m.text}, в какой день ты явился под звезды? (дд.мм.гггг)")

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_date')
def get_date(m):
    cid = m.chat.id
    user = load_user(cid)
    user['birth_date'] = m.text
    user['step'] = 'get_time'
    save_user(cid, user)
    bot.send_message(cid, "А в какой час? Это поможет мне точнее прочесть узоры судьбы. (Например: 15:15 или 'не знаю')")

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_time')
def get_time(m):
    cid = m.chat.id
    user = load_user(cid)
    user['birth_time'] = m.text
    user['step'] = 'get_request'
    save_user(cid, user)
    msg = ("С какой жаждой истины ты пришел ко мне сегодня?" if user['char'] == 'ori' else
           "О чем болит или мечтает твоя душа? Расскажи о своем главном поиске...")
    bot.send_message(cid, msg)

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_request')
def get_req(m):
    cid = m.chat.id
    user = load_user(cid)
    user['request'] = m.text
    user['step'] = 'get_heart'
    save_user(cid, user)
    bot.send_message(cid, "Какое чувство сейчас самое громкое в твоем сердце?")

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_heart')
def get_heart(m):
    cid = m.chat.id
    user = load_user(cid)
    user['heart'] = m.text
    user['step'] = 'get_element'
    save_user(cid, user)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_Огонь"), 
               types.InlineKeyboardButton("Вода 🌊", callback_data="elem_Вода"))
    markup.add(types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_Воздух"), 
               types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_Земля"))
    bot.send_message(cid, "Какая стихия откликается в тебе сильнее?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_user(cid)
    user['element'] = elem
    user['step'] = 'get_shadow'
    save_user(cid, user)
    
    explanation = (
        "<b>Шаг в Тень</b> 🌑\n\nЭто те качества, которые мы отрицаем в себе, но ярко видим в других. "
        "Скажи честно: что тебя сильнее всего раздражает в людях?"
    )
    bot.edit_message_text(f"Твоя стихия — {elem}.\n\n{explanation}", cid, call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'get_shadow')
def get_shadow(m):
    cid = m.chat.id
    user = load_user(cid)
    user['shadow'] = m.text
    user['step'] = 'processing'
    save_user(cid, user)
    
    bot.send_message(cid, "Слышу тебя. Плету нити твоего откровения... 🌌")
    bot.send_chat_action(cid, 'typing')
    
    char_style = ("Ты Ори, мудрец. Юнг, архетипы, глубокая логика. Жирный шрифт для акцентов." if user['char'] == 'ori' else 
                  "Ты Эйра, эмпат. Чувства, природа, мягкость. Курсив для акцентов.")
    
    prompt = (f"ИНСТРУКЦИЯ: {char_style}. Напиши глубокий портрет для {user['name']}. "
              f"Дата: {user['birth_date']} ({user['birth_time']}). Состояние: {user['heart']}. "
              f"Стихия: {user['element']}. Тень: {user['shadow']}. Запрос: {user['request']}. "
              "Свяжи это с астрологией и психологией. В конце добавь '👁️ Личная заметка:'.")
    
    try:
        res = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
        portrait = res.choices[0].message.content
        user['portrait'] = portrait
        user['step'] = 'free_talk'
        save_user(cid, user)
        bot.send_message(cid, portrait, parse_mode='HTML')
    except:
        bot.send_message(cid, "Звезды скрылись... Попробуй еще раз.")

@bot.message_handler(func=lambda m: load_user(m.chat.id) and load_user(m.chat.id).get('step') == 'free_talk')
def free_talk(m):
    cid = m.chat.id
    user = load_user(cid)
    bot.send_chat_action(cid, 'typing')
    
    if cid not in chat_histories: chat_histories[cid] = []
    chat_histories[cid].append({"role": "user", "content": m.text})
    
    sys_prompt = f"Ты {'Ори' if user['char'] == 'ori' else 'Эйра'}. Суть юзера: {user['portrait'][:800]}. Говори метафорами, без списков."
    
    messages = [{"role": "system", "content": sys_prompt}] + chat_histories[cid][-6:]
    
    try:
        res = client.chat_completion(messages=messages, max_tokens=800)
        ans = res.choices[0].message.content
        bot.send_message(cid, ans, parse_mode='HTML')
        chat_histories[cid].append({"role": "assistant", "content": ans})
    except:
        bot.send_message(cid, "Туман сгустился. Повтори?")

# --- Сервис ---
@app.route('/')
def home(): return "MindTrace III Live", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
