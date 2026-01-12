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

# --- СЛОВАРЬ РЕАЛЬНОСТЕЙ (ЛОКАЛИЗАЦИЯ) ---
TRANS = {
    'ru': {
        'disclaimer': (
            "<b>MindTrace: Протокол Доверия</b>\n\n"
            "Ты входишь в пространство, где древняя мудрость встречается с цифровым разумом. "
            "Мы объединили тысячелетний опыт человечества — от философии предков до глубинной психологии, "
            "чтобы создать твой уникальный слепок.\n\n"
            "🛡️ <b>Приватность и Безопасность:</b>\n"
            "Твои ответы шифруются и хранятся в защищенном контуре, соблюдая международные стандарты абсолютной тайны. Здесь ты можешь говорить о чём хочешь! "
            "Мы не передаем данные третьим лицам. Здесь только ты и Зеркало.\n\n"
            "⚠️ <b>Важное уведомление:</b>\n"
            "Я — искусственный интеллект, мой анализ основан на архетипах и знаниях глубинной психологии. "
            "Я не ставлю диагнозов. Если ты чувствуешь, что твой внутренний шторм слишком силен, "
            "пожалуйста, обратись к профессиональному специалисту. Забота о себе — это высшая форма осознанности."
        ),
        'welcome_q': "На каком языке мы начнем наше погружение?",
        'choose_char': "Выбери своего Проводника:",
        'ori_desc': "<b>Ори (Мужская энергия) 🕯️</b>\nМудрость, структура, логика.",
        'eira_desc': "<b>Эйра (Женская энергия) ❄️</b>\nИнтуиция, чувства, поток.",
        'btn_ori': "Ори 🕯️", 'btn_eira': "Эйра ❄️",
        'ask_name_ori': "Как мне называть твое земное воплощение?",
        'ask_name_eira': "Какое имя мне шептать, обращаясь к тебе?",
        'ask_date_ori': "{}, звезды помнят момент. Твоя дата рождения? (дд.мм.гггг)",
        'ask_date_eira': "{}, когда ты впервые увидел солнце? (дд.мм.гггг)",
        'ask_time_ori': "Час рождения важен для карты небес. (Например: 15:15)",
        'ask_time_eira': "В какой час это случилось? (Например: 15:15)",
        'btn_skip_time': "Не знаю / Пропустить ⏳",
        'ask_req_ori': "Твой главный запрос на сегодня? Будь краток.",
        'ask_req_eira': "О чем болит или мечтает твоя душа? Расскажи...",
        'ask_heart': "Какое чувство сейчас доминирует в сердце?",
        'ask_elem': "Какая стихия откликается в тебе?",
        'btn_fire': "Огонь 🔥", 'btn_water': "Вода 🌊", 'btn_air': "Воздух 🌬️", 'btn_earth': "Земля ⛰️",
        'ask_shadow': (
            "<b>Шаг в Тень</b> 🌑\n\n"
            "Юнг говорил: <i>«То, что раздражает нас в других, ведет к пониманию себя»</i>. "
            "Что тебя сильнее всего бесит в людях? (Это ключ к твоему портрету)."
        ),
        'processing': "Слышу тебя. Плету нити твоего портрета... 🌌",
        'error': "Звезды скрылись. Попробуй позже.",
        'menu_profile': "📜 Мой Портрет",
        'menu_switch': "🕯️ Сменить Проводника",
        'menu_reset': "🌪️ Начать заново",
        'menu_feedback': "💬 Обратная связь",
        'menu_soon': "🔮 Оракул (Скоро)",
        'feedback_ask': "Напиши свои мысли, пожелания или чувства. Я передам их Создателю.",
        'feedback_thx': "Принято. Твой голос услышан. 🙏",
        'profile_header': "<b>📜 КАРТА ДУШИ</b>",
        'insight_header': "🔮 <b>Озарение дня:</b>",
        'reset_done': "Страница перевернута. Нажми /start",
        'switched_ori': "Я здесь. Моя мудрость — твой щит.",
        'switched_eira': "Я рядом. Моя нежность — твое исцеление."
    },
    'en': {
        'disclaimer': (
            "<b>MindTrace: Protocol of Trust</b>\n\n"
            "You are entering a space where ancient wisdom meets digital intelligence. "
            "We have synthesized millennia of human experience — from Stoic philosophy to depth psychology, "
            "to create your unique digital imprint.\n\n"
            "🛡️ <b>Privacy & Security:</b>\n"
            "Your answers are encrypted and stored in a secure environment, honoring strict confidentiality standards. "
            "We do not share data with third parties. Here, it is just you and the Mirror.\n\n"
            "⚠️ <b>Important Notice:</b>\n"
            "I am an AI based on archetypes, not medicine. I do not provide medical diagnoses. "
            "If your internal storm is too overwhelming, please seek professional help. "
            "Self-care is the highest form of awareness."
        ),
        'welcome_q': "Which language shall we speak?",
        'choose_char': "Choose your Guide:",
        'ori_desc': "<b>Ori (Male Energy) 🕯️</b>\nWisdom, structure, logic.",
        'eira_desc': "<b>Eira (Female Energy) ❄️</b>\nIntuition, feelings, flow.",
        'btn_ori': "Ori 🕯️", 'btn_eira': "Eira ❄️",
        'ask_name_ori': "How should I call your earthly incarnation?",
        'ask_name_eira': "What name should I whisper when addressing you?",
        'ask_date_ori': "{}, the stars remember. Your birth date? (dd.mm.yyyy)",
        'ask_date_eira': "{}, when did you first see the sun? (dd.mm.yyyy)",
        'ask_time_ori': "Birth time is vital for the sky map. (e.g., 15:15)",
        'ask_time_eira': "at what hour did it happen? (e.g., 15:15)",
        'btn_skip_time': "I don't know / Skip ⏳",
        'ask_req_ori': "What is your main quest today? Be brief.",
        'ask_req_eira': "What does your soul dream or ache for? Tell me...",
        'ask_heart': "Which emotion dominates your heart right now?",
        'ask_elem': "Which element resonates with you?",
        'btn_fire': "Fire 🔥", 'btn_water': "Water 🌊", 'btn_air': "Air 🌬️", 'btn_earth': "Earth ⛰️",
        'ask_shadow': (
            "<b>Step into Shadow</b> 🌑\n\n"
            "Jung said: <i>Everything that irritates us about others can lead us to an understanding of ourselves.</i> "
            "What annoys you most in other people?"
        ),
        'processing': "I hear you. Weaving the threads of your portrait... 🌌",
        'error': "The stars are hidden. Try again later.",
        'menu_profile': "📜 My Portrait",
        'menu_switch': "🕯️ Change Guide",
        'menu_reset': "🌪️ Start Over",
        'menu_feedback': "💬 Feedback",
        'menu_soon': "🔮 Oracle (Soon)",
        'feedback_ask': "Write your thoughts or feelings. I will pass them to the Creator.",
        'feedback_thx': "Received. Your voice is heard. 🙏",
        'profile_header': "<b>📜 SOUL MAP</b>",
        'insight_header': "🔮 <b>Daily Insight:</b>",
        'reset_done': "The page is turned. Press /start",
        'switched_ori': "I am here. My wisdom is your shield.",
        'switched_eira': "I am near. My tenderness is your healing."
    }
}

INSIGHTS = [
    "Твой гнев — это лишь сжатая страсть. / Your anger is compressed passion.",
    "Ты не тонешь, ты учишься дышать под водой. / You are not drowning, you are learning to breathe underwater.",
    "Мысли — это птицы. Не позволяй им клевать сердце. / Thoughts are birds. Don't let them peck at your heart.",
    "В покое рождается истинная сила. / True strength is born in stillness."
]

# --- DATABASE HELPERS ---
def save_to_cloud(cid, data):
    data['cid'] = cid
    try:
        supabase.table("users").upsert(data).execute()
    except Exception as e:
        print(f"[ERROR] Save: {e}")

def load_user(cid):
    try:
        res = supabase.table("users").select("*").eq("cid", cid).execute()
        return res.data[0] if res.data else None
    except:
        return None

def get_text(cid, key):
    user = load_user(cid)
    lang = user.get('lang', 'ru') if user else 'ru'
    return TRANS.get(lang, TRANS['ru']).get(key, "Text Error")

def get_main_keyboard(cid):
    user = load_user(cid)
    lang = user.get('lang', 'ru') if user else 'ru'
    t = TRANS[lang]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton(t['menu_profile']), types.KeyboardButton(t['menu_switch']))
    markup.add(types.KeyboardButton(t['menu_feedback']), types.KeyboardButton(t['menu_reset']))
    markup.add(types.KeyboardButton(t['menu_soon']))
    return markup

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    user = load_user(cid)
    
    # Если пользователь уже прошел анкету -> Меню
    if user and user.get('portrait'):
        t = TRANS[user.get('lang', 'ru')]
        bot.send_message(cid, f"{t['switched_ori'] if user.get('char')=='ori' else t['switched_eira']}", 
                         reply_markup=get_main_keyboard(cid))
        return

    # Если новый -> Выбор языка
    save_to_cloud(cid, {'step': 'language'})
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
               types.InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"))
    
    # Дисклеймер отправляем на русском по дефолту или на двух языках сразу
    bot.send_message(cid, TRANS['ru']['disclaimer'], parse_mode='HTML')
    bot.send_message(cid, "Choose language / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    cid = call.message.chat.id
    lang = call.data.split('_')[1]
    save_to_cloud(cid, {'lang': lang, 'step': 'char_selection'})
    
    t = TRANS[lang]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(t['btn_ori'], callback_data="char_ori"),
               types.InlineKeyboardButton(t['btn_eira'], callback_data="char_eira"))
    
    bot.edit_message_text(f"{t['choose_char']}\n\n{t['ori_desc']}\n\n{t['eira_desc']}", 
                          cid, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def set_char(call):
    cid = call.message.chat.id
    char = call.data.split('_')[1]
    user = load_user(cid)
    user.update({'char': char, 'step': 'get_name'})
    save_to_cloud(cid, user)
    
    t = TRANS[user['lang']]
    msg = t['ask_name_ori'] if char == 'ori' else t['ask_name_eira']
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'skip_time')
def skip_time_handler(call):
    cid = call.message.chat.id
    user = load_user(cid)
    t = TRANS[user['lang']]
    
    user.update({'birth_time': 'Не знаю/Unknown', 'step': 'get_request'})
    save_to_cloud(cid, user)
    
    msg = t['ask_req_ori'] if user['char'] == 'ori' else t['ask_req_eira']
    bot.edit_message_text(msg, cid, call.message.message_id)

@bot.message_handler(func=lambda m: True)
def text_handler(m):
    cid = m.chat.id
    user = load_user(cid)
    if not user: return # Игнор, если нет в базе
    
    step = user.get('step')
    lang = user.get('lang', 'ru')
    t = TRANS[lang]
    char = user.get('char', 'ori')

    # --- ОБРАБОТКА МЕНЮ ---
    if m.text == t['menu_profile']:
        if user.get('portrait'):
            insight = random.choice(INSIGHTS)
            msg = (f"{t['profile_header']}\n\n"
                   f"👤 {user['name']} | {user['element']}\n"
                   f"🌑 {user['shadow']}\n\n"
                   f"{user['portrait']}\n\n"
                   f"{t['insight_header']}\n<i>{insight}</i>")
            bot.send_message(cid, msg, parse_mode='HTML')
        return

    elif m.text == t['menu_switch']:
        new_char = 'eira' if char == 'ori' else 'ori'
        user['char'] = new_char
        save_to_cloud(cid, user)
        msg = t['switched_ori'] if new_char == 'ori' else t['switched_eira']
        bot.send_message(cid, msg, reply_markup=get_main_keyboard(cid))
        return

    elif m.text == t['menu_reset']:
        save_to_cloud(cid, {'step': 'language', 'portrait': None})
        bot.send_message(cid, t['reset_done'], reply_markup=types.ReplyKeyboardRemove())
        start_cmd(m)
        return
        
    elif m.text == t['menu_feedback']:
        user['step'] = 'wait_feedback'
        save_to_cloud(cid, user)
        bot.send_message(cid, t['feedback_ask'])
        return
        
    elif m.text == t['menu_soon']:
        bot.send_message(cid, "⏳ Coming Soon...")
        return

    # --- ОБРАБОТКА АНКЕТЫ ---
    
    if step == 'get_name':
        user.update({'name': m.text, 'step': 'get_date'})
        save_to_cloud(cid, user)
        msg = t['ask_date_ori'].format(m.text) if char == 'ori' else t['ask_date_eira'].format(m.text)
        bot.send_message(cid, msg)

    elif step == 'get_date':
        user.update({'birth_date': m.text, 'step': 'get_time'})
        save_to_cloud(cid, user)
        
        # Кнопка пропуска
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(t['btn_skip_time'], callback_data="skip_time"))
        
        msg = t['ask_time_ori'] if char == 'ori' else t['ask_time_eira']
        bot.send_message(cid, msg, reply_markup=markup)

    elif step == 'get_time':
        user.update({'birth_time': m.text, 'step': 'get_request'})
        save_to_cloud(cid, user)
        msg = t['ask_req_ori'] if char == 'ori' else t['ask_req_eira']
        bot.send_message(cid, msg)

    elif step == 'get_request':
        user.update({'request': m.text, 'step': 'get_heart'})
        save_to_cloud(cid, user)
        bot.send_message(cid, t['ask_heart'])

    elif step == 'get_heart':
        user.update({'heart': m.text, 'step': 'get_element'})
        save_to_cloud(cid, user)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(t['btn_fire'], callback_data="elem_Огонь"), 
                   types.InlineKeyboardButton(t['btn_water'], callback_data="elem_Вода"))
        markup.add(types.InlineKeyboardButton(t['btn_air'], callback_data="elem_Воздух"), 
                   types.InlineKeyboardButton(t['btn_earth'], callback_data="elem_Земля"))
        bot.send_message(cid, t['ask_elem'], reply_markup=markup)

    elif step == 'wait_shadow':
        user['shadow'] = m.text
        user['step'] = 'free_talk' # Завершаем анкету
        save_to_cloud(cid, user)
        bot.send_message(cid, t['processing'])
        bot.send_chat_action(cid, 'typing')
        
        # Генерация портрета
        prompt_style = "Mystic Sage, Jungian archetypes" if char == 'ori' else "Empathic Healer, nature metaphors"
        sys_prompt = (f"Role: {prompt_style}. Language: {lang}. "
                      f"User: {user['name']}. Element: {user['element']}. Shadow: {user['shadow']}. "
                      f"Goal: Write a deep psychological portrait. Tone: Warm, esoteric, trusting. "
                      f"Add '👁️ Note:' at the end.")
        
        try:
            res = client.chat_completion(messages=[{"role": "system", "content": sys_prompt}, 
                                                   {"role": "user", "content": "Reveal me."}], max_tokens=1500)
            portrait = res.choices[0].message.content
            user['portrait'] = portrait
            save_to_cloud(cid, user)
            bot.send_message(cid, portrait, parse_mode='HTML', reply_markup=get_main_keyboard(cid))
        except:
            bot.send_message(cid, t['error'])

    elif step == 'wait_feedback':
        try:
            supabase.table("feedback").insert({"cid": cid, "username": m.from_user.username, "text": m.text}).execute()
        except: pass
        user['step'] = 'free_talk'
        save_to_cloud(cid, user)
        bot.send_message(cid, t['feedback_thx'], reply_markup=get_main_keyboard(cid))

    elif step == 'free_talk':
        bot.send_chat_action(cid, 'typing')
        if cid not in chat_histories: chat_histories[cid] = []
        chat_histories[cid].append({"role": "user", "content": m.text})
        
        sys_p = f"Role: {'Ori' if char=='ori' else 'Eira'}. Language: {lang}. Context: {user.get('portrait', '')[:500]}"
        try:
            res = client.chat_completion(messages=[{"role": "system", "content": sys_p}] + chat_histories[cid][-6:], max_tokens=600)
            ans = res.choices[0].message.content
            bot.send_message(cid, ans, parse_mode='HTML')
            chat_histories[cid].append({"role": "assistant", "content": ans})
        except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('elem_'))
def set_elem_final(call):
    cid = call.message.chat.id
    elem = call.data.split('_')[1]
    user = load_user(cid)
    user.update({'element': elem, 'step': 'wait_shadow'})
    save_to_cloud(cid, user)
    
    t = TRANS[user['lang']]
    bot.edit_message_text(f"{t['ask_elem']} {elem}\n\n{t['ask_shadow']}", 
                          cid, call.message.message_id, parse_mode='HTML')

# --- ЗАПУСК ---
@app.route('/')
def home(): return "MindTrace Layer 6 Live", 200

def run_schedule():
    while True: 
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=run_schedule, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
