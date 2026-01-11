import os
import telebot
from telebot import types
import threading
import time
import requests
import sqlite3
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

# --- Текстовые блоки (Та самая Гармония) ---
DISCLAIMER = (
    "<b>Завеса Тайны (Legal Disclaimer):</b>\n\n"
    "«MindTrace — это пространство самопознания. Я — алгоритм, обученный на опыте тысячелетий, "
    "но я не врач. Мои слова — не диагноз. Если твой внутренний шторм слишком силен, "
    "обратись к профессионалу. Помни: работа с тенью требует мужества»."
)

CHAR_INFO = {
    'ori': (
        "<b>Ори (Мужская энергия) 🕯️</b>\n"
        "Старый мудрец, чей голос подобен треску костра в ночи. Он видит структуру твоей души, "
        "говорит прямо, но глубоко. Его путь — это логика архетипов и свет осознания."
    ),
    'eira': (
        "<b>Эйра (Женская энергия) ❄️</b>\n"
        "Исцеляющая тишина зимнего леса. Её голос — мягкий шепот ветра. "
        "Она слышит твои чувства между строк, обнимает твою боль и ведет за руку через туман интуиции."
    )
}

ELEMENT_DESCRIPTIONS = {
    'fire': "🔥 <b>Огонь</b> — твоя воля способна плавить металл. Это энергия чистого действия.",
    'water': "🌊 <b>Вода</b> — ты чувствуешь течения жизни там, где другие видят пустоту.",
    'air': "🌬️ <b>Воздух</b> — твоя мысль летит быстрее птицы. Свобода и интеллект — твои крылья.",
    'earth': "⛰️ <b>Земля</b> — ты опора этого мира. В твоем спокойствии рождается структура."
}

# --- Обработка команд ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    user = load_user(cid)
    
    if user and user.get('portrait'):
        bot.send_message(cid, f"Рад твоему возвращению в чертоги разума, {user['name']}. Я помню твой путь. О чем ты хочешь спросить меня сегодня?")
        return

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
    
    bot.edit_message_text(f"Выбери своего Проводника:\n\n{CHAR_INFO['ori']}\n\n{CHAR_INFO['eira']}", 
                          cid, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_user(cid) or {}
    user['char'] = char
    user['step'] = 'get_name'
    save_user(cid, user)
    
    msg = ("Мой свет всегда был рядом. Как мне называть твое земное воплощение?" if char == 'ori' else
           "Твое дыхание отозвалось в моем сердце... Какое имя мне шептать, обращаясь к тебе?")
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.message_handler(func=lambda m: True)
def handle_steps(m):
    cid = m.chat.id
    user = load_user(cid)
    if not user: return
    step = user.get('step')
    char = user.get('char', 'ori')

    if step == 'get_name':
        user['name'] = m.text
        user['step'] = 'get_date'
        save_user(cid, user)
        msg = (f"{m.text}, в какой день ты явился под звезды? (дд.мм.гггг)" if char == 'ori' else
               f"{m.text}... прекрасное имя. В какой день ты открыл глаза под этим небом? (дд.мм.гггг)")
        bot.send_message(cid, msg)
        
    elif step == 'get_date':
        user['birth_date'] = m.text
        user['step'] = 'get_time'
        save_user(cid, user)
        bot.send_message(cid, "А в какой час? Это поможет мне точнее прочесть узоры судьбы. (15:15 или 'не знаю')")
        
    elif step == 'get_time':
        user['birth_time'] = m.text
        user['step'] = 'get_request'
        save_user(cid, user)
        msg = ("С какой жаждой истины ты пришел ко мне сегодня?" if char == 'ori' else
               "О чем болит или мечтает твоя душа? Расскажи мне о своем главном поиске...")
        bot.send_message(cid, msg)
        
    elif step == 'get_request':
        user['request'] = m.text
        user['step'] = 'get_heart'
        save_user(cid, user)
        bot.send_message(cid, "Какое чувство сейчас самое громкое в твоем сердце? Назови его...")
        
    elif step == 'get_heart':
        user['heart'] = m.text
        user['step'] = 'get_element'
        save_user(cid, user)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_Огонь"), 
                   types.InlineKeyboardButton("Вода 🌊", callback_data="elem_Вода"))
        markup.add(types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_Воздух"), 
                   types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_Земля"))
        bot.send_message(cid, "Прислушайся к своей внутренней стихии. Что откликается в тебе сильнее?", reply_markup=markup)
        
    elif step == 'wait_shadow':
        user['shadow'] = m.text
        user['step'] = 'processing'
        save_user(cid, user)
        bot.send_message(cid, "Твоя искренность — это ключ. Сонастраиваюсь с твоим ритмом... 🌌")
        bot.send_chat_action(cid, 'typing')
        
        # ГЕНЕРАЦИЯ ПОРТРЕТА
        char_style = ("Ты Ори, мудрец. Юнг, архетипы. Жирный шрифт для акцентов." if char == 'ori' else 
                      "Ты Эйра, эмпат. Чувства, природа. Курсив для акцентов.")
        
        prompt = (f"ИНСТРУКЦИЯ: {char_style}. Напиши глубокое откровение-портрет для {user['name']}. "
                  f"Дата: {user['birth_date']} в {user['birth_time']}. Состояние: {user['heart']}. "
                  f"Стихия: {user['element']}. Тень: {user['shadow']}. Запрос: {user['request']}. "
                  "Свяжи дату с астрологией. Разбери Тень через Юнга. В конце: '👁️ Личная заметка:'.")
        
        try:
            res = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
            portrait = res.choices[0].message.content
            user['portrait'] = portrait
            user['step'] = 'free_talk'
            save_user(cid, user)
            bot.send_message(cid, portrait, parse_mode='HTML')
        except:
            bot.send_message(cid, "Звезды скрылись в тумане... Повтори.")
            user['step'] = 'wait_shadow'
            save_user(cid, user)

    elif step == 'free_talk':
        bot.send_chat_action(cid, 'typing')
        if cid not in chat_histories: chat_histories[cid] = []
        chat_histories[cid].append({"role": "user", "content": m.text})
        sys_p = f"Ты {'Ори' if char=='ori' else 'Эйра'}. Суть юзера: {user['portrait'][:800]}. Пиши метафорами."
        messages = [{"role": "system", "content": sys_p}] + chat_histories[cid][-6:]
        try:
            res = client.chat_completion(messages=messages, max_tokens=800)
            ans = res.choices[0].message.content
            bot.send_message(cid, ans, parse_mode='HTML')
            chat_histories[cid].append({"role": "assistant", "content": ans})
        except:
            bot.send_message(cid, "Туман сгустился...")

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem_final(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_user(cid)
    user['element'] = elem
    user['step'] = 'wait_shadow'
    save_user(cid, user)
    
    elem_key = 'fire' if elem == 'Огонь' else 'water' if elem == 'Вода' else 'air' if elem == 'Воздух' else 'earth'
    explanation = (
        "<b>Шаг в Тень</b> 🌑\n\nЭто те части личности, которые мы прячем даже от самих себя. "
        "Обычно это то, что сильнее всего бесит нас в других людях. "
        "Скажи честно: какое качество в других вызывает у тебя самый острый протест?"
    )
    bot.edit_message_text(f"{ELEMENT_DESCRIPTIONS[elem_key]}\n\nТеперь шаг в глубину...\n\n{explanation}", 
                          cid, call.message.message_id, parse_mode='HTML')

# --- Сервис ---
@app.route('/')
def home(): return "MindTrace 3.1 Harmony Live", 200

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
