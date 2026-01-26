import os
import logging
import random
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# --- ИНИЦИАЛИЗАЦИЯ ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"

SERIES_LIMITS = {1: 42, 2: 27, 3: 25}
SERIES_IMAGES = {
    1: "https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Other/Primary.png",
    2: "https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Other/Intermediate.png",
    3: "https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Other/Advanced2.png",
    'mix': "https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Other/Primary.png"
}

user_data = {}
test_data = {}
ASK_START, ASK_END = range(2)

# --- БЛОК РАБОТЫ С БАЗОЙ ---
async def fetch_asanas(series: int = None):
    url = f"{SUPABASE_URL}/rest/v1/asanas"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {"order": "order_num.asc"}
    if series: params["series"] = f"eq.{series}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, params=params)
        return r.json() if r.status_code == 200 else []

async def get_asana_by_id(aid: int):
    url = f"{SUPABASE_URL}/rest/v1/asanas"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {"id": f"eq.{aid}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, params=params)
        data = r.json()
        return data[0] if data else None

async def upsert_user(chat_id: int):
    url = f"{SUPABASE_URL}/rest/v1/users"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    # Try to update first (if user exists)
    update_url = f"{url}?chat_id=eq.{chat_id}"
    update_data = {"latest_interaction": "now()"}
    async with httpx.AsyncClient() as client:
        r = await client.patch(update_url, headers=headers, json=update_data)
        if r.status_code == 200 and r.json():  # Updated successfully
            return chat_id
        else:
            # Insert new user
            data = {"chat_id": chat_id, "latest_interaction": "now()"}
            r2 = await client.post(url, headers=headers, json=data)
            if r2.status_code == 201:
                return chat_id
            elif r2.status_code == 409:  # Conflict, user exists
                return chat_id  # Assume it exists
    return None

async def log_interaction(user_id: int, interaction_type: str, num_asanas: int):
    print(f"Logging interaction: user_id={user_id}, type={interaction_type}, num_asanas={num_asanas}")
    url = f"{SUPABASE_URL}/rest/v1/interactions"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {"user_id": user_id, "type": interaction_type, "number_of_asanas": num_asanas}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=data)
        print(f"Log interaction response: {r.status_code}")

# --- ШАВАСАНА ---


async def send_shavasana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    img_id = random.randint(1, 11)
    img_url = f"https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Wishes/{img_id}.png"

    await query.message.reply_photo(
        photo=img_url,
        caption="✨ Твое пожелание на сегодня. Намасте! 🙏"
    )

    uid = update.effective_user.id
    user_data.pop(uid, None)
    test_data.pop(uid, None)

    return await start(update, context)



# --- ГЛАВНОЕ МЕНЮ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🧘 Учить асаны", callback_data='menu_learn')],
        [InlineKeyboardButton("💪 Проверить мастерство", callback_data='menu_test')],
        [InlineKeyboardButton("☕️ Поддержать проект", callback_data='menu_donate')]
    ]
    txt = '🙏 Добро пожаловать в бот для изучения асан Аштанга Йоги!\nВыберите режим:'

    uid = update.effective_user.id
    await upsert_user(uid)
    user_data.pop(uid, None)
    test_data.pop(uid, None)

    if update.message:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    else:
        try:
            await update.callback_query.message.delete()
        except:
            pass
        await context.bot.send_message(chat_id=update.effective_chat.id, text=txt, reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("🧘 Учить асаны", callback_data='menu_learn')],
        [InlineKeyboardButton("💪 Проверить мастерство", callback_data='menu_test')],
        [InlineKeyboardButton("☕️ Поддержать проект", callback_data='menu_donate')]
    ]
    txt = '🙏 Добро пожаловать в бот для изучения асан Аштанга Йоги!\nВыберите режим:'
    await query.message.delete()
    await context.bot.send_message(chat_id=query.message.chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'menu_learn':
        kb = [
            [InlineKeyboardButton("Первая серия", callback_data='select_series_1')],
            [InlineKeyboardButton("Вторая серия", callback_data='select_series_2')],
            [InlineKeyboardButton("Третья серия", callback_data='select_series_3')],
            [InlineKeyboardButton("◀️ Назад", callback_data='to_start')]
        ]
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text='🧘 Выберите серию для изучения:', reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == 'menu_donate':
        # Ваш текст с форматированием
        donate_text = (
            "Этот ботик был сделан из любви к Аштанге и комьюнити 🙏🏼\n\n"
            "Знание названий асан не изменит вашу жизнь (тут уж придется самим стараться 💪🏽), "
            "но поможет глубже понять практику и не растеряться, "
            "когда учитель попросит еще раз повторить бхуджапидасану 👹\n\n"
            "*Если этот ботик был полезным и вы хотите отблагодарить его создательницу - жмите на донат. "
            "Ботик сможет стать лучше, как и вы 💙*\n\n"
            "_Продолжайте практиковать! And all, как мы знаем, is coming 🙌🏽_"
        )

        kb = [
            [InlineKeyboardButton("🔥 Добаввить тапаса (CloudTips)", url="https://pay.cloudtips.ru/p/6b21b46b")],
            [InlineKeyboardButton("◀️ В меню", callback_data='to_start')]
        ]

        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=donate_text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='Markdown'
        )

    elif query.data.startswith('select_series_'):
        series = int(query.data.split('_')[-1])
        context.user_data['series'] = series
        await query.message.delete()

        kb = [
            [InlineKeyboardButton("📖 Учить по порядку", callback_data=f'set_l_{series}')],
            [InlineKeyboardButton("👀 Посмотреть асаны", callback_data=f'view_all_{series}_0')],
            [InlineKeyboardButton("◀️ Назад", callback_data='menu_learn')]
        ]
        caption = (
            f"{'Первая' if series==1 else 'Вторая' if series==2 else 'Третья'} серия. "
            "Хотите следовать по серии или выбрать асаны из списка?"
        )
        await query.message.reply_photo(
            photo=SERIES_IMAGES[series],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif query.data == 'menu_test':
        kb = [
            [InlineKeyboardButton("Первая серия", callback_data='pretest_1')],
            [InlineKeyboardButton("Вторая серия", callback_data='pretest_2')],
            [InlineKeyboardButton("Третья серия", callback_data='pretest_3')],
            [InlineKeyboardButton("Микс", callback_data='pretest_mix')],
            [InlineKeyboardButton("◀️ Назад", callback_data='to_start')]
        ]
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text='💪 Выберите серию для теста:', reply_markup=InlineKeyboardMarkup(kb))

# --- ЛОГИКА ТЕСТА ---
async def pre_test_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_id = await upsert_user(uid)
    await log_interaction(user_id, 'test', 10)
    series_type = query.data.split('_')[-1]
    img_key = int(series_type) if series_type.isdigit() else 'mix'
    kb = [[InlineKeyboardButton("🚀 Вперед!", callback_data=f"start_test_{series_type}")],
          [InlineKeyboardButton("◀️ Назад", callback_data="menu_test")]]
    await query.message.delete()
    await query.message.reply_photo(photo=SERIES_IMAGES[img_key], caption="Крепкая мулабандха поможет вам ответить на следующие 10 вопросов 🦾 ", reply_markup=InlineKeyboardMarkup(kb))

async def init_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    s_val = query.data.split('_')[-1]
    series = int(s_val) if s_val.isdigit() else None
    all_asanas = await fetch_asanas(series)
    selected = random.sample(all_asanas, min(10, len(all_asanas)))
    test_data[uid] = {'pool': all_asanas, 'questions': selected, 'index': 0, 'errors': [], 'score': 0}
    await query.message.delete()
    await send_q(query.message, uid)

async def send_q(msg, uid, is_growth=False):
    data = test_data.get(uid)
    if not data or data['index'] >= len(data['questions']):
        await finish_test(msg, uid)
        return
    q = data['questions'][data['index']]
    others = [a for a in data['pool'] if a['id'] != q['id']]
    options = random.sample(others, 2) + [q]
    random.shuffle(options)
    kb = [[InlineKeyboardButton(opt['name'], callback_data=f"ans_{q['id']}_{opt['id']}")] for opt in options]
    cap = "🌱 Точка роста! Вспомни название:" if is_growth else f"Вопрос {data['index']+1}/10\nКак называется эта асана?"
    await msg.reply_photo(q['image_url'], caption=cap, reply_markup=InlineKeyboardMarkup(kb))

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = test_data.get(uid)
    if not data: return
    _, correct_id, chosen_id = query.data.split('_')
    if correct_id == chosen_id:
        if int(correct_id) not in data['errors']: data['score'] += 1
        a = await get_asana_by_id(int(correct_id))
        await query.edit_message_caption(f"Верно! ✅\n\n{a['name']}")
        data['index'] += 1
        await send_q(query.message, uid)
    else:
        if int(correct_id) not in data['errors']: data['errors'].append(int(correct_id))
        if "❌" not in query.message.caption:
            await query.edit_message_caption(query.message.caption + "\n\nВыбрано неверно ❌ Попробуйте еще раз!", reply_markup=query.message.reply_markup)

async def finish_test(msg, uid):
    data = test_data.get(uid)
    if not data['errors']:
        video = "https://zhsqobhlvtarkksnwsfy.supabase.co/storage/v1/object/public/Other/IMG_4867.MP4"
        await msg.reply_video(video=video, caption="🎉 Безупречно! Теперь вы еще на один шаг ближе к самадхи!")
        kb = [[InlineKeyboardButton("🔄 Еще раз", callback_data='menu_test')],
              [InlineKeyboardButton("🏠 Меню", callback_data='to_start')],
              [InlineKeyboardButton("🧘 Шавасана", callback_data='shavasana')]]
    else:
        txt = f"🏁 Тест окончен!\n📊 Ваш счёт: {data['score']} из {len(data['questions'])}"
        await msg.reply_text(txt)
        kb = [[InlineKeyboardButton("🌱 Точки роста", callback_data='growth')],
              [InlineKeyboardButton("🔄 Еще раз", callback_data='menu_test')],
              [InlineKeyboardButton("🏠 Меню", callback_data='to_start')],
              [InlineKeyboardButton("🧘 Шавасана", callback_data='shavasana')]]
    await msg.reply_text("Что делаем дальше?", reply_markup=InlineKeyboardMarkup(kb))

async def handle_growth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = test_data.get(uid)
    err_asanas = [await get_asana_by_id(mid) for mid in data['errors']]
    data.update({'questions': err_asanas, 'index': 0, 'errors': [], 'score': 0})
    await query.message.reply_text("🚀 Работаем над вашими точками роста:")
    await send_q(query.message, uid, is_growth=True)

# --- ЛОГИКА ОБУЧЕНИЯ ---
async def start_learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_id = await upsert_user(uid)
    context.user_data['user_id'] = user_id
    series = int(query.data.split('_')[-1])
    context.user_data['series'] = series
    try:
        await query.message.delete()
    except:
        pass
    kb = [[InlineKeyboardButton("🏠 Меню", callback_data='to_start')]]
    await context.bot.send_message(query.message.chat_id, f"С какой асаны начнём? Введите цифру (1-{SERIES_LIMITS[series]}):", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_START

async def get_start_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text
    if not val.isdigit(): return ASK_START
    context.user_data['start'] = int(val)
    kb = [[InlineKeyboardButton("🏠 Меню", callback_data='to_start')]]
    await update.message.reply_text(f"Начинаем с {val}. Какой асаной закончим? Введите цифру", reply_markup=InlineKeyboardMarkup(kb))
    return ASK_END

async def get_end_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text
    if not val.isdigit(): return ASK_END
    s, e = context.user_data['start'], int(val)
    asanas = await fetch_asanas(context.user_data['series'])
    filtered = [a for a in asanas if s <= a['order_num'] <= e]
    user_data[update.effective_user.id] = {'list': filtered, 'idx': 0}
    user_id = context.user_data.get('user_id')
    if user_id:
        await log_interaction(user_id, 'learn', len(filtered))
    await show_asana(update.message, update.effective_user.id)
    return ConversationHandler.END

async def show_asana(msg, uid):
    d = user_data.get(uid)
    a = d['list'][d['idx']]
    kb = [[InlineKeyboardButton("◀️", callback_data='prev'), InlineKeyboardButton(f"{d['idx']+1}/{len(d['list'])}", callback_data='none'), InlineKeyboardButton("▶️", callback_data='next')],
          [InlineKeyboardButton("🏠 Меню", callback_data='to_start')]]
    cap = f"🧘 *{a['name']}*"
    transcription = a.get('transcription') or ''
    if transcription:
        cap += f"\n\n_{transcription}_"
    meaning = a.get('meaning') or ''
    if meaning:
        cap += f"\n\n{meaning}"
    await msg.reply_photo(a['image_url'], caption=cap, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

async def nav_learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data == 'next': user_data[uid]['idx'] += 1
    elif query.data == 'prev': user_data[uid]['idx'] = max(0, user_data[uid]['idx'] - 1)

    if user_data[uid]['idx'] >= len(user_data[uid]['list']):
        await query.message.reply_text("🎉 Все асаны изучены!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Меню", callback_data='to_start')],
            [InlineKeyboardButton("🧘 Шавасана", callback_data='shavasana')]
        ]))
    else:
        try:
            await query.message.delete()
        except:
            pass
        await show_asana(query.message, uid)

async def view_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_parts = query.data.split('_')
    series, offset = int(data_parts[2]), int(data_parts[3])
    all_a = await fetch_asanas(series)
    page = all_a[offset:offset+10]
    kb = [[InlineKeyboardButton(f"{a['order_num']}. {a['name']}", callback_data=f"info_{a['id']}")] for a in page]
    nav = []
    if offset > 0: nav.append(InlineKeyboardButton("◀️", callback_data=f"view_all_{series}_{offset-10}"))
    if offset + 10 < len(all_a): nav.append(InlineKeyboardButton("▶️", callback_data=f"view_all_{series}_{offset+10}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("🏠 Меню", callback_data='to_start')])
    await query.message.edit_caption(caption="📋 Список асан серии:", reply_markup=InlineKeyboardMarkup(kb))

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    asana = await get_asana_by_id(int(query.data.split('_')[-1]))
    await query.message.delete()
    kb = [[InlineKeyboardButton("◀️ К списку", callback_data=f"view_all_{asana['series']}_0")]]
    await query.message.reply_photo(photo=asana['image_url'], caption=f"🧘 {asana['name']}", reply_markup=InlineKeyboardMarkup(kb))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Exception while handling an update: {context.error}")

# --- MAIN ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_error_handler(error_handler)

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_learn, pattern='^set_l_')],
        states={
            ASK_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_num),
                CallbackQueryHandler(to_start_callback, pattern='^to_start$')
            ],
            ASK_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_num),
                CallbackQueryHandler(to_start_callback, pattern='^to_start$')
            ]
        },
        fallbacks=[CallbackQueryHandler(to_start_callback, pattern='^to_start$')],
        per_message=False,
        allow_reentry=True
    ))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(to_start_callback, pattern='^to_start$'))
    app.add_handler(CallbackQueryHandler(send_shavasana, pattern='^shavasana$'))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern='^(menu_|select_series_)'))
    app.add_handler(CallbackQueryHandler(pre_test_screen, pattern='^pretest_'))
    app.add_handler(CallbackQueryHandler(init_test, pattern='^start_test_'))
    app.add_handler(CallbackQueryHandler(check_answer, pattern='^ans_'))
    app.add_handler(CallbackQueryHandler(handle_growth, pattern='^growth$'))
    app.add_handler(CallbackQueryHandler(nav_learn, pattern='^(next|prev)$'))
    app.add_handler(CallbackQueryHandler(view_all, pattern='^view_all_'))
    app.add_handler(CallbackQueryHandler(show_info, pattern='^info_'))

    print("🤖 бот запущен и готов к работе!")
    print("WEBHOOK_URL =", WEBHOOK_URL)

    if WEBHOOK_URL:
        print("starting webhook")
        app.run_webhook(
            listen="0.0.0.0",
            port=8080,
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL + WEBHOOK_PATH,
        )
    else:
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
