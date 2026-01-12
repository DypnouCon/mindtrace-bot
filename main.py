import os
import telebot
from telebot import types
import threading
import time
import requests
from flask import Flask
from huggingface_hub import InferenceClient
from supabase import create_client, Client

# --- Инициализация ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

chat_histories = {}

# --- Текстовые блоки ---
DISCLAIMER = (
    "<b>Завеса Тайны (Legal Disclaimer):</b>\n\n"
    "«MindTrace — это пространство самопознания. Я — алгоритм, обученный на опыте тысячелетий. "
    "Твои откровения хранятся в зашифрованном облаке, доступном только нам. "
    "Помни: работа с тенью требует мужества»."
)

# --- Работа с Supabase (Облако) ---
def save_to_cloud(cid, data):
    # Подготавливаем данные для вставки/обновления
    data['cid'] = cid
    try:
        supabase.table("users").upsert(data).execute()
    except Exception as e:
        print(f"[ERROR] Supabase Save: {e}")

def load_from_cloud(cid):
    try:
        res = supabase.table("users").select("*").eq("cid", cid).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[ERROR] Supabase Load: {e}")
        return None

# --- Логика Бота ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    
    if user and user.get('portrait'):
        bot.send_message(cid, f"Рад твоему возвращению, {user['name']}. Твой путь записан в звездах. Используй /profile, чтобы вспомнить нашу прошлую беседу.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
               types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    
    bot.send_message(cid, DISCLAIMER, parse_mode='HTML')
    bot.send_message(cid, "На каком языке мы начнем наше погружение?", reply_markup=markup)

@bot.message_handler(commands=['profile'])
def profile_cmd(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    if user and user.get('portrait'):
        profile_msg = (
            f"<b>📜 Твоя Карта Судьбы:</b>\n\n"
            f"<b>Имя:</b> {user['name']}\n"
            f"<b>Стихия:</b> {user['element']}\n"
            f"<b>Дата рождения:</b> {user['birth_date']}\n\n"
            f"<b>Твой Портрет:</b>\n{user['portrait']}"
        )
        bot.send_message(cid, profile_msg, parse_mode='HTML')
    else:
        bot.send_message(cid, "Твой путь еще не начат. Нажми /start")

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    cid = call.message.chat.id
    lang = call.data.split('_')[1]
    save_to_cloud(cid, {'lang': lang, 'step': 'char_selection'})
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ори 🕯️", callback_data="char_ori"),
               types.InlineKeyboardButton("Эйра ❄️", callback_data="char_eira"))
    
    bot.edit_message_text("Выбери своего Проводника:", cid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_from_cloud(cid) or {}
    user['char'] = char
    user['step'] = 'get_name'
    save_to_cloud(cid, user)
    
    msg = "Как мне называть твое земное воплощение?" if char == 'ori' else "Какое имя мне шептать, обращаясь к тебе?"
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.message_handler(func=lambda m: True)
def handle_steps(m):
    cid = m.chat.id
    user = load_from_cloud(cid)
    if not user: return
    step = user.get('step')

    if step == 'get_name':
        user.update({'name': m.text, 'step': 'get_date'})
        save_to_cloud(cid, user)
        bot.send_message(cid, f"{m.text}, в какой день ты явился под звезды? (дд.мм.гггг)")
        
    elif step == 'get_date':
        user.update({'birth_date': m.text, 'step': 'get_time'})
        save_to_cloud(cid, user)
        bot.send_message(cid, "А в какой час? (15:15 или 'не знаю')")
        
    elif step == 'get_time':
        user.update({'birth_time': m.text, 'step': 'get_request'})
        save_to_cloud(cid, user)
        bot.send_message(cid, "О чем болит или мечтает твоя душа? Твой запрос...")
        
    elif step == 'get_request':
        user.update({'request': m.text, 'step': 'get_heart'})
        save_to_cloud(cid, user)
        bot.send_message(cid, "Какое чувство сейчас самое громкое в сердце?")
        
    elif step == 'get_heart':
        user.update({'heart': m.text, 'step': 'get_element'})
        save_to_cloud(cid, user)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_Огонь"), 
                   types.InlineKeyboardButton("Вода 🌊", callback_data="elem_Вода"))
        markup.add(types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_Воздух"), 
                   types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_Земля"))
        bot.send_message(cid, "Твоя стихия?", reply_markup=markup)
        
    elif step == 'wait_shadow':
        user['shadow'] = m.text
        user['step'] = 'processing'
        save_to_cloud(cid, user)
        bot.send_message(cid, "Сонастраиваюсь с твоим ритмом... 🌌")
        bot.send_chat_action(cid, 'typing')
        
        # Промпт для портрета
        prompt = (f"Ты {'Ори, мудрец' if user['char']=='ori' else 'Эйра, эмпат'}. Напиши глубокий портрет для {user['name']}. "
                  f"Дата: {user['birth_date']}. Стихия: {user['element']}. Тень: {user['shadow']}. Запрос: {user['request']}. "
                  "Используй психологию Юнга. В конце добавь '👁️ Личная заметка:'.")
        
        try:
            res = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
            user.update({'portrait': res.choices[0].message.content, 'step': 'free_talk'})
            save_to_cloud(cid, user)
            bot.send_message(cid, user['portrait'], parse_mode='HTML')
        except:
            bot.send_message(cid, "Звезды скрылись. Попробуй ответить еще раз.")

    elif step == 'free_talk':
        bot.send_chat_action(cid, 'typing')
        # (Логика истории чата аналогична предыдущей)
        sys_p = f"Ты {'Ори' if user['char']=='ori' else 'Эйра'}. Суть: {user['portrait'][:500]}"
        try:
            res = client.chat_completion(messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": m.text}], max_tokens=800)
            bot.send_message(cid, res.choices[0].message.content, parse_mode='HTML')
        except:
            bot.send_message(cid, "Туман сгустился...")

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_from_cloud(cid)
    user.update({'element': elem, 'step': 'wait_shadow'})
    save_to_cloud(cid, user)
    bot.edit_message_text(f"Стихия: {elem}. А теперь — что тебя сильнее всего бесит в людях?", cid, call.message.message_id)

# --- Flask ---
@app.route('/')
def home(): return "MindTrace Cloud Live", 200

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
