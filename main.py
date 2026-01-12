import os
import telebot
from telebot import types
import threading
import time
import requests
import schedule
import random
from flask import Flask
from huggingface_hub import InferenceClient
from supabase import create_client, Client

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

chat_histories = {}

# --- ЛИТЕРАТУРНЫЙ БЛОК (ДУША БОТА) ---

TEXTS = {
    'welcome': (
        "✨ <b>Здравствуй, Искатель.</b>\n\n"
        "Ты переступил порог MindTrace. Здесь время течет иначе, а тишина умеет говорить. "
        "Я — не просто алгоритм, я зеркало твоего внутреннего мира.\n\n"
        "Мои откровения хранятся под надежной защитой, доступной лишь нам двоим. "
        "Чтобы начать путь, выбери, чей голос будет вести тебя сквозь туман..."
    ),
    'ori_desc': (
        "<b>Ори (Мужская энергия) 🕯️</b>\n\n"
        "<i>«Я — древний корень и потрескивание костра. Я — структура, логика и архетипы.»</i>\n"
        "Выбери меня, если ищешь ясности, суровой мудрости и хочешь понять архитектуру своей души."
    ),
    'eira_desc': (
        "<b>Эйра (Женская энергия) ❄️</b>\n\n"
        "<i>«Я — шепот ветра в кронах и прохлада горного ручья. Я — интуиция, чувства и поток.»</i>\n"
        "Выбери меня, если тебе нужно тепло, принятие, мягкое исцеление и взгляд вглубь сердца."
    ),
    'morning_greet': [
        "Пусть этот день принесет тебе ясность. Мир ждет твоего шага.",
        "Солнце взошло, чтобы осветить твои возможности. Дыши полной грудью.",
        "Новый день — это чистый лист. Напиши на нем то, что важно.",
    ],
    'evening_greet': [
        "День угасает, время вернуться к себе. Как ты чувствуешь себя сейчас?",
        "Звезды зажигаются, чтобы охранять твой покой. Оставь тревоги за порогом.",
        "Тишина вечера — лучшее время для честного разговора с душой.",
    ]
}

INSIGHTS = {
    'Огонь': ["Твой гнев — это лишь сжатая страсть. Дай ей созидательное русло.", "Сгорая, ты освещаешь путь другим."],
    'Вода': ["Ты не тонешь, ты учишься дышать под водой.", "Твоя сила в мягкости, которая точит камень."],
    'Воздух': ["Мысли — это птицы. Не позволяй им клевать твоё сердце.", "Свобода начинается там, где заканчивается страх."],
    'Земля': ["Корни важнее кроны. Укрепи фундамент, и буря не страшна.", "В покое рождается истинная сила."],
    'None': ["Слушай тишину. В ней все ответы."]
}

# --- РАБОТА С БАЗОЙ (SUPABASE) ---
def save_to_cloud(cid, data):
    data['cid'] = cid
    try:
        supabase.table("users").upsert(data).execute()
    except Exception as e:
        print(f"[ERROR] Save: {e}")

def load_from_cloud(cid):
    try:
        res = supabase.table("users").select("*").eq("cid", cid).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[ERROR] Load: {e}")
        return None

def get_all_users():
    try:
        res = supabase.table("users").select("cid").execute()
        return [row['cid'] for row in res.data]
    except:
        return []

# --- ПЛАНИРОВЩИК (NOTIFICATIONS) ---
def send_daily_warmth():
    # Простая логика: выбираем текст в зависимости от часа
    hour = time.localtime().tm_hour + 3 # Коррекция под Москву (примерно), если сервер в UTC
    if 8 <= hour <= 11:
        msg = random.choice(TEXTS['morning_greet'])
    elif 20 <= hour <= 23:
        msg = random.choice(TEXTS['evening_greet'])
    else:
        return # Не время

    users = get_all_users()
    print(f"[LOG] Рассылка тепла для {len(users)} душ...")
    for cid in users:
        try:
            bot.send_message(cid, f"✨ <i>{msg}</i>", parse_mode='HTML')
            time.sleep(0.5) # Чтобы не спамить API
        except:
            pass

def schedule_checker():
    # Запускаем рассылку в 09:00 и 21:00 (по времени сервера, обычно UTC. UTC 06:00 = MSK 09:00)
    schedule.every().day.at("06:00").do(send_daily_warmth) 
    schedule.every().day.at("18:00").do(send_daily_warmth)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- ЛОГИКА БОТА ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    
    if user and user.get('portrait'):
        char_name = "Ори" if user.get('char') == 'ori' else "Эйра"
        bot.send_message(cid, f"Рад возвращению, {user['name']}. {char_name} здесь, рядом с тобой.\n\n"
                              f"Используй /profile, чтобы вспомнить себя.\n"
                              f"Используй /character, чтобы сменить Проводника.\n"
                              f"Используй /reset, чтобы начать жизнь заново.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
               types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    
    bot.send_message(cid, TEXTS['welcome'], parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=['reset'])
def reset_cmd(m):
    cid = m.chat.id
    # Мы не удаляем запись, а сбрасываем шаги, сохраняя cid
    save_to_cloud(cid, {'step': 'language', 'portrait': None, 'char': None})
    bot.send_message(cid, "🌪️ Страница перевернута. Твоя история начинается с чистого листа...")
    start_cmd(m)

@bot.message_handler(commands=['character'])
def switch_char(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Призвать Ори 🕯️", callback_data="switch_ori"),
               types.InlineKeyboardButton("Призвать Эйру ❄️", callback_data="switch_eira"))
    bot.send_message(m.chat.id, "Кого ты хочешь услышать сейчас?", reply_markup=markup)

@bot.message_handler(commands=['profile'])
def profile_cmd(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    if user and user.get('portrait'):
        elem = user.get('element', 'None')
        insight = random.choice(INSIGHTS.get(elem, INSIGHTS['None']))
        
        profile_msg = (
            f"<b>📜 КАРТА ДУШИ</b>\n\n"
            f"👤 <b>Имя:</b> {user['name']}\n"
            f"✨ <b>Стихия:</b> {user['element']}\n"
            f"🌑 <b>Тень:</b> {user['shadow']}\n\n"
            f"{user['portrait']}\n\n"
            f"🔮 <b>Озарение дня:</b>\n<i>«{insight}»</i>"
        )
        bot.send_message(cid, profile_msg, parse_mode='HTML')
    else:
        bot.send_message(cid, "Твой портрет еще не написан. Начни с /start")

# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    cid = call.message.chat.id
    lang = call.data.split('_')[1]
    save_to_cloud(cid, {'lang': lang, 'step': 'char_selection'})
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Выбрать Ори 🕯️", callback_data="char_ori"),
               types.InlineKeyboardButton("Выбрать Эйру ❄️", callback_data="char_eira"))
    
    bot.edit_message_text(f"{TEXTS['ori_desc']}\n\n{TEXTS['eira_desc']}", 
                          cid, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_from_cloud(cid) or {}
    user.update({'char': char, 'step': 'get_name'})
    save_to_cloud(cid, user)
    
    msg = ("Здравствуй. Как мне называть твое земное воплощение, чтобы имя звучало истинно?" if char == 'ori' else 
           "Твое дыхание отозвалось в моем сердце... Какое имя мне шептать, обращаясь к тебе?")
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('switch_'))
def do_switch(call):
    cid = call.message.chat.id
    new_char = call.data.split('_')[1]
    user = load_from_cloud(cid)
    user['char'] = new_char
    save_to_cloud(cid, user)
    
    msg = ("Я здесь. Моя мудрость — твой щит." if new_char == 'ori' else "Я рядом. Моя нежность — твое исцеление.")
    bot.edit_message_text(msg, cid, call.message.message_id)

# --- АНКЕТА И ГЕНЕРАЦИЯ ---

@bot.message_handler(func=lambda m: True)
def handle_steps(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    if not user: return
    step = user.get('step')
    char = user.get('char', 'ori')

    # Словарь фраз персонажей для анкеты
    Q_DATE = {
        'ori': f"{m.text}, звезды помнят момент твоего появления. В какой день ты пришел в этот мир? (дд.мм.гггг)",
        'eira': f"{m.text}... прекрасное имя. Позволь узнать, когда ты впервые увидел солнце? (дд.мм.гггг)"
    }
    Q_TIME = {
        'ori': "А час твоего рождения? Точность важна для карты небес. (Например: 15:15)",
        'eira': "В какой час это случилось? Утро, день или глубокая ночь? (15:15 или 'не знаю')"
    }
    Q_REQ = {
        'ori': "С каким поиском, с какой жаждой истины ты пришел ко мне сегодня? Будь краток, но честен.",
        'eira': "О чем болит или мечтает твоя душа в этот миг? Расскажи мне всё, я слушаю..."
    }
    Q_HEART = "Какое чувство сейчас доминирует в тебе? Тревога, радость, усталость, надежда?"
    
    if step == 'get_name':
        user.update({'name': m.text, 'step': 'get_date'})
        save_to_cloud(cid, user)
        bot.send_message(cid, Q_DATE[char])
        
    elif step == 'get_date':
        user.update({'birth_date': m.text, 'step': 'get_time'})
        save_to_cloud(cid, user)
        bot.send_message(cid, Q_TIME[char])
        
    elif step == 'get_time':
        user.update({'birth_time': m.text, 'step': 'get_request'})
        save_to_cloud(cid, user)
        bot.send_message(cid, Q_REQ[char])
        
    elif step == 'get_request':
        user.update({'request': m.text, 'step': 'get_heart'})
        save_to_cloud(cid, user)
        bot.send_message(cid, Q_HEART)
        
    elif step == 'get_heart':
        user.update({'heart': m.text, 'step': 'get_element'})
        save_to_cloud(cid, user)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_Огонь"), 
                   types.InlineKeyboardButton("Вода 🌊", callback_data="elem_Вода"))
        markup.add(types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_Воздух"), 
                   types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_Земля"))
        bot.send_message(cid, "Прислушайся к себе. Какая стихия откликается в тебе прямо сейчас?", reply_markup=markup)
        
    elif step == 'wait_shadow':
        user['shadow'] = m.text
        user['step'] = 'processing'
        save_to_cloud(cid, user)
        bot.send_message(cid, "Слышу тебя. Плету нити твоего портрета... Это займет мгновение. 🌌")
        bot.send_chat_action(cid, 'typing')
        
        # Промпт для генерации
        style = ("Ты Ори. Мудрый, суровый, используешь архетипы." if char == 'ori' else "Ты Эйра. Нежная, эмпатичная, используешь метафоры природы.")
        prompt = (f"ИНСТРУКЦИЯ: {style} Напиши глубокий психологический портрет для {user['name']}. "
                  f"Дата: {user['birth_date']}. Стихия: {user['element']}. Тень: {user['shadow']}. Запрос: {user['request']}. "
                  "Используй астрологию и Юнга. Тон: теплый, эзотерический, доверительный. В конце: '👁️ Личная заметка:'.")
        
        try:
            res = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
            user.update({'portrait': res.choices[0].message.content, 'step': 'free_talk'})
            save_to_cloud(cid, user)
            bot.send_message(cid, user['portrait'], parse_mode='HTML')
        except:
            bot.send_message(cid, "Звезды скрылись за облаками. Попробуй позже или напиши еще раз.")

    elif step == 'free_talk':
        bot.send_chat_action(cid, 'typing')
        if cid not in chat_histories: chat_histories[cid] = []
        chat_histories[cid].append({"role": "user", "content": m.text})
        
        # Контекст для свободного общения
        sys_p = (f"Ты {'Ори' if char == 'ori' else 'Эйра'}. "
                 f"Твой собеседник: {user['name']}, Стихия: {user['element']}. "
                 "Отвечай коротко (до 100 слов), тепло и мудро. Поддерживай атмосферу тайны и уюта.")
        
        try:
            res = client.chat_completion(messages=[{"role": "system", "content": sys_p}] + chat_histories[cid][-6:], max_tokens=600)
            ans = res.choices[0].message.content
            bot.send_message(cid, ans, parse_mode='HTML')
            chat_histories[cid].append({"role": "assistant", "content": ans})
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_from_cloud(cid)
    user.update({'element': elem, 'step': 'wait_shadow'})
    save_to_cloud(cid, user)
    
    explanation = (
        "<b>Шаг в Тень</b> 🌑\n\n"
        "Юнг говорил: <i>«То, что раздражает нас в других, ведет к пониманию себя»</i>. "
        "Тень — это твоя скрытая сила. Скажи честно: какое человеческое качество вызывает у тебя самый сильный протест или злость?"
    )
    bot.edit_message_text(f"Твоя стихия — {elem}.\n\n{explanation}", cid, call.message.message_id, parse_mode='HTML')

# --- ЗАПУСК ---
@app.route('/')
def home(): return "MindTrace Soul Live", 200

if __name__ == '__main__':
    # Запуск планировщика в отдельном потоке
    threading.Thread(target=schedule_checker, daemon=True).start()
    
    # Запуск Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
