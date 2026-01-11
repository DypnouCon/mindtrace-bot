import telebot
from telebot import types
from huggingface_hub import InferenceClient

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8255523498:AAFCEOEYV84iLyieHHrTkU3dTQzlZwrSdMs"
HF_TOKEN = "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"

bot = telebot.TeleBot(BOT_TOKEN)
client = InferenceClient(api_key=HF_TOKEN)

# Данные пользователей (временно в памяти)
user_states = {}

# Тексты на двух языках
TEXTS = {
    'ru': {
        'start': "✨ Здравствуй, дорогой друг. Я — MindTrace, твоя тихая гавань. Здесь ты можешь быть собой. Как мне тебя называть?",
        'lang_selected': "Выбран русский язык. 🇷🇺",
        'element': "Какая стихия сейчас ближе твоей душе?",
        'heart': "💓 Что сейчас у тебя на сердце?",
        'shadow': "🌑 О чем ты обычно молчишь? Что скрыто в твоей тени?",
        'genre': "🎭 В каком жанре сейчас твоя жизнь?",
        'processing': "🧬 Соединяю нити судьбы, создаю твой портрет...",
        'disclaimer': "\n\n--- \n⚠️ Пожалуйста, помни, что я — лишь ИИ. Если тебе очень тяжело, обратись к профессиональному врачу, ты не должен быть один в этом.",
        'error': "🔮 Туман сгустился над гаванью... Попробуй еще раз через минуту."
    },
    'en': {
        'start': "✨ Hello, dear friend. I am MindTrace, your safe haven. Here you can be yourself. How should I call you?",
        'lang_selected': "English language selected. 🇺🇸",
        'element': "Which element is closest to your soul right now?",
        'heart': "💓 What is on your heart right now?",
        'shadow': "🌑 What do you usually keep silent about? What's in your shadow?",
        'genre': "🎭 What genre is your life in right now?",
        'processing': "🧬 Connecting the threads of fate, creating your portrait...",
        'disclaimer': "\n\n--- \n⚠️ Please remember that I am only an AI. If you are going through a hard time, please consult a professional doctor; you don't have to be alone in this.",
        'error': "🔮 The mist has thickened over the harbor... Please try again in a minute."
    }
}

def get_ai_response(user_data):
    lang = user_data.get('lang', 'ru')
    system_prompt = (
        "You are MindTrace, an empathetic AI psychologist and advisor. "
        "Your goal is to create a deep psychological portrait based on user answers. "
        "Be warm, supportive, and poetic. Use emojis. "
        f"Answer strictly in the following language: {lang}"
    )
    
    user_content = (
        f"Name: {user_data.get('name')}. "
        f"Element: {user_data.get('element')}. "
        f"Heart: {user_data.get('heart')}. "
        f"Shadow: {user_data.get('shadow')}. "
        f"Genre: {user_data.get('genre')}."
    )

    try:
        response = ""
        # Используем мощную модель Qwen 2.5
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
        print(f"Error: {e}")
        return TEXTS[lang]['error']

@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Русский 🇷🇺', 'English 🇺🇸')
    bot.send_message(message.chat.id, "Выберите язык / Choose your language:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Русский 🇷🇺', 'English 🇺🇸'])
def set_language(message):
    lang = 'ru' if 'Русский' in message.text else 'en'
    user_states[message.chat.id] = {'lang': lang, 'step': 'name'}
    bot.send_message(message.chat.id, TEXTS[lang]['lang_selected'])
    bot.send_message(message.chat.id, TEXTS[lang]['start'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'name')
def get_name(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'name': m.text, 'step': 'element'})
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if lang == 'ru':
        markup.add('🔥 Огонь', '💧 Вода', '🌬 Воздух', '🌱 Земля')
    else:
        markup.add('🔥 Fire', '💧 Water', '🌬 Air', '🌱 Earth')
    
    bot.send_message(m.chat.id, TEXTS[lang]['element'], reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'element')
def get_element(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'element': m.text, 'step': 'heart'})
    bot.send_message(m.chat.id, TEXTS[lang]['heart'], reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'heart')
def get_heart(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'heart': m.text, 'step': 'shadow'})
    bot.send_message(m.chat.id, TEXTS[lang]['shadow'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'shadow')
def get_shadow(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'shadow': m.text, 'step': 'genre'})
    bot.send_message(m.chat.id, TEXTS[lang]['genre'])

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'genre')
def get_genre(m):
    lang = user_states[m.chat.id]['lang']
    user_states[m.chat.id].update({'genre': m.text, 'step': 'done'})
    bot.send_message(m.chat.id, TEXTS[lang]['processing'])
    
    result = get_ai_response(user_states[m.chat.id])
    bot.send_message(m.chat.id, result)
    # Очистка данных после завершения
    del user_states[m.chat.id]

if __name__ == '__main__':
    bot.infinity_polling()
