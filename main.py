import os
import telebot
from telebot import types
import threading
import time
import requests
from flask import Flask
from huggingface_hub import InferenceClient
import random

# --- Инициализация ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
app = Flask(__name__)

user_data = {}

# --- Текстовые блоки ---

ELEMENT_DESCRIPTIONS = {
    'fire': "🔥 Огонь — это искра творения, страсть и воля. Энергия трансформации и активного действия.",
    'water': "🌊 Вода — это глубина чувств, интуиция и адаптивность. Умение обтекать препятствия и сопереживать.",
    'air': "🌬️ Воздух — это полет мысли, свобода и интеллект. Пространство идей, общения и перемен.",
    'earth': "⛰️ Земля — это опора, структура и созидание. Сила корней, надежности и материального воплощения."
}

SHADOW_EXPLANATION = (
    "<b>Что такое Тень?</b> 🌑\n\n"
    "По Карлу Юнгу, Тень — это те части нашей личности, которые мы не признаем в себе или подавляем. "
    "Проще всего найти свою Тень, ответив на вопрос: <i>«Что меня сильнее всего бесит в других?»</i>. "
    "Обычно нас раздражает в людях то, что мы запрещаем проявлять себе.\n\n"
    "Попробуй ответить честно: какое качество в людях вызывает у тебя внутренний протест?"
)

# --- Функции Flask ---

@app.route('/')
def hello():
    return "MindTrace is breathing...", 200

def keep_alive():
    def run():
        while True:
            try:
                requests.get("https://mindtrace-bot.onrender.com")
            except:
                pass
            time.sleep(600)
    threading.Thread(target=run, daemon=True).start()

# --- Логика Бота ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    user_data[m.chat.id] = {'step': 'language', 'chat_history': []}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    bot.send_message(m.chat.id, "Выбери язык / Choose language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['lang'] = lang
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ори (Мудрость) 🕯️", callback_data="char_ori"))
    markup.add(types.InlineKeyboardButton("Эйра (Чувства) ❄️", callback_data="char_eira"))
    
    msg = "Выбери своего Проводника:"
    bot.edit_message_text(msg, cid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_character(call):
    char = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['char'] = char
    user_data[cid]['step'] = 'get_name'
    bot.send_message(cid, f"Я — {'Ори' if char == 'ori' else 'Эйра'}. Как мне называть тебя в нашем путешествии?")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_name')
def get_name(m):
    user_data[m.chat.id]['name'] = m.text
    user_data[m.chat.id]['step'] = 'get_date'
    bot.send_message(m.chat.id, f"{m.text}, в какой день ты явился под звезды? (дд.мм.гггг)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_date')
def get_date(m):
    user_data[m.chat.id]['birth_date'] = m.text
    user_data[m.chat.id]['step'] = 'get_time'
    bot.send_message(m.chat.id, "И в какой час? (Например: 15:15 или 'не знаю')")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_time')
def get_time(m):
    user_data[m.chat.id]['birth_time'] = m.text
    user_data[m.chat.id]['step'] = 'get_request' # Возвращаем запрос, чтобы не было KeyError
    bot.send_message(m.chat.id, "С каким главным вопросом или поиском ты пришел ко мне сегодня?")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_request')
def get_request(m):
    user_data[m.chat.id]['request'] = m.text
    user_data[m.chat.id]['step'] = 'get_heart'
    bot.send_message(m.chat.id, "Какое чувство сейчас самое громкое в твоем сердце?")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_heart')
def get_heart(m):
    user_data[m.chat.id]['heart'] = m.text
    user_data[m.chat.id]['step'] = 'get_element'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Огонь", callback_data="elem_Огонь"))
    markup.add(types.InlineKeyboardButton("Вода", callback_data="elem_Вода"))
    markup.add(types.InlineKeyboardButton("Воздух", callback_data="elem_Воздух"))
    markup.add(types.InlineKeyboardButton("Земля", callback_data="elem_Земля"))
    
    bot.send_message(m.chat.id, "Прислушайся к своей природе. Какая стихия тебе ближе всего?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_element(call):
    element_name = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['element'] = element_name
    user_data[cid]['step'] = 'get_shadow'
    
    # Показываем описание стихии и переходим к Тени
    elem_key = 'fire' if element_name == 'Огонь' else 'water' if element_name == 'Вода' else 'air' if element_name == 'Воздух' else 'earth'
    desc = ELEMENT_DESCRIPTIONS[elem_key]
    
    bot.edit_message_text(f"{desc}\n\nТеперь самый глубокий вопрос...\n\n{SHADOW_EXPLANATION}", cid, call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_shadow')
def get_shadow(m):
    cid = m.chat.id
    user_data[cid]['shadow'] = m.text
    user_data[cid]['step'] = 'processing'
    bot.send_message(cid, "Твоя честность открывает врата... Плету узоры твоего портрета. Подожди немного. 🌌")
    
    d = user_data[cid]
    char_desc = (
        "Ты — Ори, мудрый философ. Стиль: архетипы, Юнг, глубокий смысл. Используй жирный шрифт для ключевых истин." 
        if d['char'] == 'ori' else 
        "Ты — Эйра, эмпатичный проводник. Стиль: чувства, шепот, интуиция. Используй курсив для эмоциональных акцентов."
    )
    
    prompt = (
        f"ИНСТРУКЦИЯ: {char_desc}. Ты не ИИ, ты — этот персонаж. Пользователь {d['name']}. "
        f"Родился: {d['birth_date']} в {d['birth_time']}. Состояние: {d['heart']}. Стихия: {d['element']}. "
        f"Тень: {d['shadow']}. Запрос: {d['request']}. "
        "НАПИШИ глубокий психологический портрет. Используй астрологию и стихии как метафоры судьбы. "
        "Обращайся к человеку по имени. В конце добавь: '👁️ Личная заметка:' с догадкой о его скрытой силе."
    )
    
    try:
        response = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
        final_text = response.choices[0].message.content
        bot.send_message(cid, final_text, parse_mode='HTML')
        user_data[cid]['step'] = 'free_talk'
        user_data[cid]['portrait_summary'] = final_text[:800]
    except Exception as e:
        bot.send_message(cid, "Звезды затянуло тучами... Попробуй еще раз через минуту.")
        user_data[cid]['step'] = 'get_shadow'

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'free_talk')
def free_talk(m):
    cid = m.chat.id
    d = user_data[cid]
    bot.send_chat_action(cid, 'typing')
    
    # Добавляем историю
    d['chat_history'].append({"role": "user", "content": m.text})
    if len(d['chat_history']) > 6: d['chat_history'] = d['chat_history'][-6:]

    system_prompt = (
        f"Ты — {'Ори' if d['char'] == 'ori' else 'Эйра'}. Общаешься с {d['name']}. "
        f"Его суть: {d['portrait_summary']}. Оставайся в образе. Не давай списков. Пиши метафорами."
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(d['chat_history'])
    
    try:
        response = client.chat_completion(messages=messages, max_tokens=800)
        res_text = response.choices[0].message.content
        bot.send_message(cid, res_text, parse_mode='HTML')
        d['chat_history'].append({"role": "assistant", "content": res_text})
    except:
        bot.send_message(cid, "Мои мысли сейчас как туман... Повтори.")

if __name__ == '__main__':
    keep_alive()
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
