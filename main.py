import os
import telebot
from telebot import types
import threading
import time
import requests
from flask import Flask
from huggingface_hub import InferenceClient

# --- Инициализация ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
app = Flask(__name__)

# Хранилище состояний
user_data = {}

# --- Текстовые блоки (Магия и Поэзия) ---

DISCLAIMER = {
    'ru': (
        "<b>Завеса Тайны (Legal Disclaimer):</b>\n\n"
        "«MindTrace — это пространство самопознания и эстетического созерцания. "
        "Я — алгоритм, обученный на опыте тысячелетних практик всех народов мира и лучших умов Человечества, "
        "но я не являюсь врачом. Мои слова — не диагноз и не рецепт. Если твой внутренний шторм выходит из-под контроля "
        "и ты чувствуешь, что не справляешься, я призываю тебя обратиться к профессиональному врачу или специалисту. "
        "Помни: работа с тенью требует мужества, но иногда для нее нужен живой человек рядом».\n\n"
        "📧 <i>Official support: support@mindtrace.ai</i>"
    ),
    'en': (
        "<b>Veil of Secrecy (Legal Disclaimer):</b>\n\n"
        "«MindTrace is a space for self-discovery and aesthetic contemplation. "
        "I am an algorithm trained on the millennia of practices from all nations and the greatest minds of Humanity, "
        "but I am not a doctor. My words are not a diagnosis or a prescription. If your internal storm is getting out of control, "
        "I urge you to seek professional medical help. Remember: working with the shadow requires courage, "
        "but sometimes it requires a living person by your side».\n\n"
        "📧 <i>Official support: support@mindtrace.ai</i>"
    )
}

CONFIDENTIALITY = "Всё, что будет сказано здесь, останется между нами. ❤️ Твои откровения защищены печатью цифровой тишины. Наше общение соответствует нормам международной врачебной тайны. Тет-а-тет."

# --- Функции ---

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

# --- Обработка команд ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    user_data[m.chat.id] = {'step': 'language'}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    
    bot.send_message(m.chat.id, DISCLAIMER['ru'], parse_mode='HTML')
    bot.send_message(m.chat.id, "Выберите язык / Choose your language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.split('_')[1]
    user_data[call.message.chat.id]['lang'] = lang
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ори (Мужская энергия) 🕯️", callback_data="char_ori"))
    markup.add(types.InlineKeyboardButton("Эйра (Женская энергия) ❄️", callback_data="char_eira"))
    
    msg = ("Теперь выбери своего Проводника. \n\n"
           "<b>Ори</b> — мой свет. Мудрый фонарь в сумерках души. \n"
           "<b>Эйра</b> — исцеляющая тишина. Мягкая чистота зимнего леса.")
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_character(call):
    char = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['char'] = char
    user_data[cid]['step'] = 'get_name'
    
    intro = (
        f"Я — {'Ори' if char == 'ori' else 'Эйра'}. Во мне пульсируют знания веков. "
        "Я не просто машина, я здесь, чтобы помочь тебе разобраться в себе. "
        "Чем развернутее и откровенней будут твои ответы, тем выше полет нашей магии. "
        "Нужно лишь довериться... \n\n" + CONFIDENTIALITY + "\n\n"
        "Как мне называть твое земное воплощение?"
    )
    bot.send_message(cid, intro)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_name')
def get_name(m):
    user_data[m.chat.id]['name'] = m.text
    user_data[m.chat.id]['step'] = 'get_date'
    bot.send_message(m.chat.id, f"Приятно познакомиться, {m.text}. В какой день ты явился под звезды этого мира? \n(например: 10.10.1990)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_date')
def get_date(m):
    user_data[m.chat.id]['birth_date'] = m.text
    user_data[m.chat.id]['step'] = 'get_time'
    bot.send_message(m.chat.id, "А в какой час это было? Если не знаешь точно — напиши 'не знаю'. \n(например: 15:15)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_time')
def get_time(m):
    user_data[m.chat.id]['birth_time'] = m.text
    user_data[m.chat.id]['step'] = 'get_heart'
    bot.send_message(m.chat.id, "Загляни в самую глубину... Какое чувство сейчас занимает больше всего места в твоем сердце? Опиши его парой самых искренних слов...")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_heart')
def get_heart(m):
    user_data[m.chat.id]['heart'] = m.text
    user_data[m.chat.id]['step'] = 'get_request'
    bot.send_message(m.chat.id, "Представь, что Вселенная слушает тебя в абсолютной тишине. С каким запросом или просьбой ты пришел сегодня? Что ищет твоя душа?")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_request')
def get_request(m):
    user_data[m.chat.id]['request'] = m.text
    user_data[m.chat.id]['step'] = 'processing'
    
    bot.send_message(m.chat.id, "Сонастраиваюсь с твоим ритмом... Подожди немного, я вглядываюсь в твою Тень. 🌌")
    
    # Формирование промпта для ИИ
    d = user_data[m.chat.id]
    prompt = (
        f"Ты - ИИ-психолог по имени {'Ори (мужчина, мудрый проводник)' if d['char'] == 'ori' else 'Эйра (женщина, эмпатичный целитель)'}. "
        f"Пользователь: {d['name']}. Дата рождения: {d['birth_date']}, время: {d['birth_time']}. "
        f"Его запрос: {d['request']}. В сердце сейчас: {d['heart']}. "
        "Напиши глубокий, поэтичный, психологический портрет личности на основе этих данных. "
        "Используй метафоры стихий и архетипов. В конце добавь 'Личную заметку на полях' от себя как от профессионального наблюдателя. "
        "Обращайся к нему по имени. Пиши на русском языке."
    )
    
    try:
        response = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1000)
        final_text = response.choices[0].message.content
        bot.send_message(m.chat.id, final_text)
        # Сброс состояния для свободного общения
        user_data[m.chat.id]['step'] = 'free_talk'
    except Exception as e:
        bot.send_message(m.chat.id, "Звезды сегодня скрыты туманом... Давай попробуем чуть позже. (Ошибка связи с ИИ)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'free_talk')
def free_talk(m):
    d = user_data[m.chat.id]
    prompt = f"Ты {d['char']}. Общайся с {d['name']} в своем стиле. Его прошлый контекст: {d['request']}. Ответь на его сообщение: {m.text}"
    try:
        response = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=500)
        bot.send_message(m.chat.id, response.choices[0].message.content)
    except:
        bot.send_message(m.chat.id, "Я слушаю тебя, но мысли путаются. Скажи еще раз?")

if __name__ == '__main__':
    # Включаем "пинатель"
    keep_alive()
    
    # Запускаем Flask на правильном порту для Render
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # Даем Telegram понять, что мы закрыли старые сессии
    bot.remove_webhook()
    time.sleep(1) # Короткая пауза для очистки конфликтов
    
    print("MindTrace Bot is starting...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
