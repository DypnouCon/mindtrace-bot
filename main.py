import os
import telebot
from telebot import types
import threading
import time
import requests
from flask import Flask
from huggingface_hub import InferenceClient
import random # Для "озарений"

# --- Инициализация ---
TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(TOKEN)
client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=HF_TOKEN)
app = Flask(__name__)

# Хранилище состояний и краткосрочной памяти
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

# --- Функции Flask для Render ---

@app.route('/')
def hello():
    return "MindTrace is breathing...", 200

def keep_alive():
    def run():
        while True:
            try:
                requests.get("https://mindtrace-bot.onrender.com") # Замени на свой актуальный URL Render
            except:
                pass
            time.sleep(600) # Пингуем каждые 10 минут
    threading.Thread(target=run, daemon=True).start()

# --- Обработка команд Telegram ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    user_data[m.chat.id] = {'step': 'language', 'chat_history': []} # Добавляем историю чата
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
           "<b>Ори</b> — мой свет. Мудрый фонарь в сумерках души, несущий древние знания. \n"
           "<b>Эйра</b> — исцеляющая тишина. Мягкая чистота зимнего леса, укрывающая от мирской суеты.")
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_character(call):
    char = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['char'] = char
    user_data[cid]['step'] = 'get_name'
    
    intro = (
        f"Я — {'Ори' if char == 'ori' else 'Эйра'}. {'Мой голос звучит как вековой дуб, полный историй.' if char == 'ori' else 'Мой шепот — как легкое дуновение ветра, несущее мудрость.'} "
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
    bot.send_message(m.chat.id, f"Приятно познакомиться, {m.text}. В какой день ты явился под звезды этого мира? \n(Например: 10.10.1990)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_date')
def get_date(m):
    user_data[m.chat.id]['birth_date'] = m.text
    user_data[m.chat.id]['step'] = 'get_time'
    bot.send_message(m.chat.id, "А в какой час это было? Если не знаешь точно — напиши 'не знаю'. \n(Например: 15:15)")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_time')
def get_time(m):
    user_data[m.chat.id]['birth_time'] = m.text
    user_data[m.chat.id]['step'] = 'get_heart'
    bot.send_message(m.chat.id, "Загляни в самую глубину... Какое чувство сейчас занимает больше всего места в твоем сердце? Опиши его парой самых искренних слов...")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_heart')
def get_heart(m):
    user_data[m.chat.id]['heart'] = m.text
    user_data[m.chat.id]['step'] = 'get_element' # Новый шаг
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Огонь 🔥", callback_data="elem_fire"))
    markup.add(types.InlineKeyboardButton("Вода 🌊", callback_data="elem_water"))
    markup.add(types.InlineKeyboardButton("Воздух 🌬️", callback_data="elem_air"))
    markup.add(types.InlineKeyboardButton("Земля ⛰️", callback_data="elem_earth"))
    bot.send_message(m.chat.id, "Если бы ты был природным явлением, то какой стихией ощущаешь себя больше всего?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_element(call):
    element = call.data.split('_')[1]
    cid = call.message.chat.id
    user_data[cid]['element'] = element
    user_data[cid]['step'] = 'get_shadow' # Новый шаг
    bot.edit_message_text(f"Твоя стихия — {element.capitalize()}. Теперь позволь мне заглянуть глубже...\n\nЧто в других людях раздражает тебя больше всего? Это ключ к твоей Тени.", cid, call.message.message_id)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'get_shadow')
def get_shadow(m):
    cid = m.chat.id
    user_data[cid]['shadow'] = m.text
    user_data[cid]['step'] = 'processing'
    
    bot.send_chat_action(cid, 'typing')
    bot.send_message(cid, "Собираю все нити твоего бытия воедино... Это займет минуту. 🌌")
    
    d = user_data[cid]
    char_desc = (
        "Ты — Ори, мудрый старец, твой голос спокоен, как вековой дуб. Ты говоришь метафорами света и тени, архетипов Юнга. Твои ответы глубоки и философски. Используй *жирный шрифт* для ключевых истин и `моноширинный текст` для формул души." 
        if d['char'] == 'ori' else 
        "Ты — Эйра, эмпатичная и глубокая женщина, твой голос — как шепот зимнего ветра. Ты исцеляешь тишиной и интуицией. Твои ответы эмоциональны, но мудры. Используй _курсив_ для эмоциональных акцентов и многоточия для создания ритма дыхания."
    )
    
    prompt = (
        f"ИНСТРУКЦИЯ: {char_desc}. Ты не ИИ, ты — этот персонаж. "
        f"Пользователь {d['name']}. Дата рождения: {d['birth_date']}, время: {d['birth_time']}. "
        f"Его состояние сердца: {d['heart']}. Его природная стихия: {d['element']}. Его Тень (что раздражает в других): {d['shadow']}. "
        f"Его главный запрос/поиск в жизни: {d['request']}. "
        "ЗАДАЧА: Напиши глубокий психологический и архетипический портрет личности на основе ВСЕХ этих данных. "
        "Обязательно используй астрологические данные (дату/время) для создания атмосферы судьбоносности и связи со звездами. "
        "Интегрируй стихию и теневой аспект в портрет. "
        "Избегай списков и канцеляризмов. Пиши как мистик-философ/целитель. "
        "Обращайся к нему по имени. Пиши на русском языке, используя свой характерный стиль форматирования. "
        "В конце добавь блок: '👁️ Личная заметка на полях моего сознания:' — здесь напиши одну глубокую психологическую догадку о его скрытых талантах или вызове, с которым он сталкивается, учитывая его Тень."
    )
    
    try:
        response = client.chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=1500)
        final_text = response.choices[0].message.content
        bot.send_message(cid, final_text, parse_mode='HTML')
        user_data[cid]['step'] = 'free_talk'
        user_data[cid]['portrait_summary'] = final_text[:1000] # Сохраняем более длинный summary для контекста
        user_data[cid]['chat_history'].append({"role": "assistant", "content": final_text})
    except Exception as e:
        bot.send_message(cid, "Звезды затянуло тучами... Попробуй написать мне еще раз через минуту. (Ошибка обработки)")
        print(f"Error in get_shadow: {e}")
        user_data[cid]['step'] = 'get_shadow' # Возвращаем на этот шаг для повторной попытки

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('step') == 'free_talk')
def free_talk(m):
    cid = m.chat.id
    d = user_data[cid]
    bot.send_chat_action(cid, 'typing')
    
    # Добавляем сообщение пользователя в историю чата
    d['chat_history'].append({"role": "user", "content": m.text})
    # Обрезаем историю, чтобы она не была слишком длинной (последние 5 сообщений)
    if len(d['chat_history']) > 5:
        d['chat_history'] = d['chat_history'][-5:]

    char_desc = (
        "Ты — Ори, мудрый старец, твой голос спокоен, как вековой дуб. Ты говоришь метафорами света и тени, архетипов Юнга. Твои ответы глубоки и философски. Используй *жирный шрифт* для ключевых истин и `моноширинный текст` для формул души." 
        if d['char'] == 'ori' else 
        "Ты — Эйра, эмпатичная и глубокая женщина, твой голос — как шепот зимнего ветра. Ты исцеляешь тишиной и интуицией. Твои ответы эмоциональны, но мудры. Используй _курсив_ для эмоциональных акцентов и многоточия для создания ритма дыхания."
    )
    
    # Формируем системный промпт для ИИ, включающий всю личность и краткую историю
    system_prompt_content = (
        f"КОНТЕКСТ: {char_desc}. Ты общаешься с {d['name']}. "
        f"Ты уже создал его портрет: {d['portrait_summary']}. "
        f"Его главный запрос/поиск в жизни: {d['request']}. "
        "ОТВЕТЬ ему, оставаясь в образе на 100%. Если он спрашивает советы (например, про деньги или жизнь), "
        "не давай списков 1-2-3. Отвечай как духовный наставник — через образы, смыслы и внутреннюю силу. "
        "Будь лаконичен, но меток. Используй свой характерный стиль форматирования (жирный/курсив). "
        "Иногда, примерно в 10% случаев, в конце ответа добавь короткое, загадочное 'Озарение:' (например: 'Озарение: Зеркало души не терпит лжи.')"
    )
    
    messages = [{"role": "system", "content": system_prompt_content}]
    # Добавляем предыдущие сообщения из истории чата
    messages.extend(d['chat_history'])
    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": m.text})
    
    try:
        response = client.chat_completion(messages=messages, max_tokens=800)
        final_response = response.choices[0].message.content
        
        # Добавляем "Озарение" с 10% шансом
        if random.random() < 0.1:
            epiphanies = [
                "Озарение: Истинная сила покоится в тишине...",
                "Озарение: Каждый ответ несет новый вопрос...",
                "Озарение: Тень танцует, когда свет угасает...",
                "Озарение: Зеркало души не терпит лжи...",
                "Озарение: То, что ищешь, уже внутри...",
                "Озарение: Ветер перемен шепчет о новом пути...",
                "Озарение: В каждом завершении скрыто новое начало..."
            ]
            final_response += f"\n\n__{random.choice(epiphanies)}__" # Делаем озарение курсивом
            
        bot.send_message(cid, final_response, parse_mode='HTML')
        d['chat_history'].append({"role": "assistant", "content": final_response})
    except Exception as e:
        bot.send_message(cid, "Мои мысли сейчас как туман над водой... Повтори, я слушаю.")
        print(f"Error in free_talk: {e}")

# --- Запуск бота ---
if __name__ == '__main__':
    keep_alive()
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    bot.remove_webhook()
    time.sleep(1) 
    
    print("MindTrace Bot is starting...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
