import os
import telebot
from telebot import types
from huggingface_hub import InferenceClient
from threading import Thread
from flask import Flask

# --- СЕРВЕР-ЗАГЛУШКА ДЛЯ RENDER (Чтобы сервис не засыпал и не выдавал ошибку порта) ---
app = Flask('')

@app.route('/')
def home():
    return "MindTrace Safe Haven is Online!"

def run():
    # Render автоматически назначает порт через переменную окружения
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- КОНФИГУРАЦИЯ (Твои актуальные токены) ---
BOT_TOKEN = "8255523498:AAFCEOEYV84iLyieHHrTkU3dTQzlZwrSdMs"
HF_TOKEN = "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"

bot = telebot.TeleBot(BOT_TOKEN)
client = InferenceClient(api_key=HF_TOKEN)

user_states = {}

# Тексты сообщений (Русский / English)
TEXTS = {
    'ru': {
        'start': "✨ Здравствуй, дорогой друг. Я — MindTrace. Здесь твоя тихая гавань. Как мне тебя называть?",
        'lang_selected': "Выбран русский язык. 🇷🇺",
        'element': "Какая стихия тебе сейчас ближе?",
        'heart': "💓 Что сейчас у тебя на сердце?",
        'shadow': "🌑 О чем ты обычно молчишь? Что скрыто в твоей тени?",
        'genre': "🎭 В каком жанре сейчас твоя жизнь?",
        'processing': "🧬 Соединяю нити твоей истории... Подожди немного.",
        'disclaimer': "\n\n--- \n⚠️ Пожалуйста, помни: я — ИИ. Если тебе очень тяжело, обратись к профессиональному врачу.",
        'error': "🔮 Туман сгустился над гаванью... Попробуй еще раз через минуту."
    },
    'en': {
        'start': "✨ Hello, dear friend. I am MindTrace. Your safe haven. How should I call you?",
        'lang_selected': "English language selected. 🇺🇸",
        'element': "Which element is closest to your soul right now?",
        'heart': "💓 What is on your heart right now?",
        'shadow': "🌑 What is in your shadow? What do you keep silent about?",
        'genre': "🎭 What genre is your life in right now?",
        'processing': "🧬 Connecting the threads... Creating your portrait.",
        'disclaimer': "\n\n--- \n⚠️ Remember: I am an AI. If you are struggling, please consult a professional.",
        'error': "🔮 The mist has thickened... Please try again."
    }
}

def get_ai_response(user_data):
    lang = user_data.get('lang', 'ru')
    system_prompt = (
        "You are MindTrace, an empathetic AI psychologist. Be warm, poetic, and supportive. "
        f"Answer strictly in {lang}."
    )
    user_content = (
        f"Name: {user_data.get('name')}, "
        f"Element: {user_data.get('element')}, "
        f"Heart: {user_data.get('heart')}, "
        f"Shadow: {user_data.get('shadow')}, "
        f"Genre: {user_data.get('genre')}."
    )

    try:
        response = ""
        for message in client.chat_completion(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=1000,
            temperature=0.7,
            stream=True,
        ):
            token = message.choices[0].delta.content
            if token:
                response += token
        return response + TEXTS[lang]['disclaimer']
    except Exception as e:
        print(f"AI Error: {e}")
        return TEXTS[lang]['error']

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Русский 🇷🇺', 'English 🇺🇸')
    bot.send_message(message.chat.id, "Выберите язык / Choose your language:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Русский 🇷🇺', 'English 🇺🇸'])
def handle_language(message):
    lang = 'ru' if 'Русский' in message.text else 'en'
    user_states[message.chat.id] = {'lang': lang, 'step': 'name'}
    bot.send_message(message.chat.id, TEXTS[lang]['lang_selected'])
    bot.send_message(message.chat.id, TEXTS[lang]['start'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'name')
def handle_name(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'name': m.text, 'step': 'element'})
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btns = ['🔥 Огонь', '💧 Вода', '🌬 Воздух', '🌱 Земля'] if lang == 'ru' else ['🔥 Fire', '💧 Water', '🌬 Air', '🌱 Earth']
    markup.add(*btns)
    bot.send_message(m.chat.id, TEXTS[lang]['element'], reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'element')
def handle_element(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'element': m.text, 'step': 'heart'})
    bot.send_message(m.chat.id, TEXTS[lang]['heart'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'heart')
def handle_heart(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'heart': m.text, 'step': 'shadow'})
    bot.send_message(m.chat.id, TEXTS[lang]['shadow'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'shadow')
def handle_shadow(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'shadow': m.text, 'step': 'genre'})
    bot.send_message(m.chat.id, TEXTS[lang]['genre'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'genre')
def handle_genre(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'genre': m.text, 'step': 'done'})
    bot.send_message(m.chat.id, TEXTS[lang]['processing'])
    
    # Генерация ответа через ИИ
    ai_response = get_ai_response(user_states[m.chat.id])
    bot.send_message(m.chat.id, ai_response)
    
    # Сброс состояния
    del user_states[m.chat.id]

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    keep_alive()
    # Запуск бота
    bot.infinity_polling()
