import os
import telebot
from telebot import types
from huggingface_hub import InferenceClient
from threading import Thread
from flask import Flask

# --- СЕРВЕР-ЗАГЛУШКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "MindTrace is protected and running."

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# --- БЕЗОПАСНАЯ КОНФИГУРАЦИЯ (Берем из настроек Render) ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)

user_states = {}

TEXTS = {
    'ru': {
        'start': "✨ Здравствуй, Жора. Я — MindTrace. Твоя тихая гавань. Как мне тебя называть?",
        'lang_selected': "Выбран русский язык. 🇷🇺",
        'element': "Какая стихия тебе сейчас ближе?",
        'heart': "💓 Что сейчас у тебя на сердце?",
        'shadow': "🌑 О чем ты обычно молчишь?",
        'genre': "🎭 В каком жанре твоя жизнь?",
        'processing': "🧬 Соединяю нити... Твой портрет почти готов.",
        'disclaimer': "\n\n--- \n⚠️ Помни: я — ИИ. Если тяжело, обратись к врачу.",
        'error': "🔮 Туман в гавани... Попробуй еще раз через минуту."
    },
    'en': {
        'start': "✨ Hello. I am MindTrace. Your safe haven. How should I call you?",
        'lang_selected': "English selected. 🇺🇸",
        'element': "Which element is closest to you?",
        'heart': "💓 What is on your heart?",
        'shadow': "🌑 What is in your shadow?",
        'genre': "🎭 Life genre?",
        'processing': "🧬 Creating portrait...",
        'disclaimer': "\n\n--- \n⚠️ I am an AI. Consult a professional if needed.",
        'error': "🔮 Mist in the harbor... Try again."
    }
}

def get_ai_response(user_data):
    lang = user_data.get('lang', 'ru')
    system_msg = f"You are MindTrace, an empathetic AI psychologist. Be poetic and supportive. Answer strictly in {lang}."
    user_msg = f"Name: {user_data.get('name')}, Element: {user_data.get('element')}, Heart: {user_data.get('heart')}, Shadow: {user_data.get('shadow')}, Genre: {user_data.get('genre')}."

    try:
        # Упрощенный запрос без стриминга для стабильности
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content + TEXTS[lang]['disclaimer']
    except Exception as e:
        print(f"!!! AI ERROR: {e}")
        return TEXTS[lang]['error']

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['start'])
def start(m):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Русский 🇷🇺', 'English 🇺🇸')
    bot.send_message(m.chat.id, "Выберите язык / Choose language:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Русский 🇷🇺', 'English 🇺🇸'])
def set_l(m):
    lang = 'ru' if 'Русский' in m.text else 'en'
    user_states[m.chat.id] = {'lang': lang, 'step': 'name'}
    bot.send_message(m.chat.id, TEXTS[lang]['start'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'name')
def get_n(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'name': m.text, 'step': 'element'})
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btns = ['🔥 Огонь', '💧 Вода', '🌬 Воздух', '🌱 Земля'] if lang == 'ru' else ['🔥 Fire', '💧 Water', '🌬 Air', '🌱 Earth']
    markup.add(*btns)
    bot.send_message(m.chat.id, TEXTS[lang]['element'], reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'element')
def get_e(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'element': m.text, 'step': 'heart'})
    bot.send_message(m.chat.id, TEXTS[lang]['heart'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'heart')
def get_h(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'heart': m.text, 'step': 'shadow'})
    bot.send_message(m.chat.id, TEXTS[lang]['shadow'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'shadow')
def get_s(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'shadow': m.text, 'step': 'genre'})
    bot.send_message(m.chat.id, TEXTS[lang]['genre'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'genre')
def get_g(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'genre': m.text, 'step': 'done'})
    bot.send_message(m.chat.id, TEXTS[lang]['processing'])
    bot.send_message(m.chat.id, get_ai_response(user_states[m.chat.id]))
    del user_states[m.chat.id]

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
