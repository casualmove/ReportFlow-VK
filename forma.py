import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import sqlite3
import json
import time

TOKEN = ""
GROUP_ID =

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# Подключение к базе данных (один файл bot.db)
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

# Таблица для заполненных форм
cursor.execute('''
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        nickname TEXT,
        direction TEXT,
        position_reason TEXT,
        discord TEXT,
        forum_link TEXT,
        vk_link TEXT,
        server TEXT,
        screenshot TEXT,
        admin_commands TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# Таблица для администраторов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        date_added DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()


# Функция для удаления администратора
def remove_admin(user_id):
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()


# Функция для добавления администратора
def add_admin(user_id, username=None):
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()

# Добавляем главного администратора, если его ещё нет
MAIN_ADMIN_ID = 646813077
add_admin(MAIN_ADMIN_ID, "ГлавныйАдмин")

def is_admin(user_id):
    cursor.execute('SELECT user_id FROM admins WHERE user_id=?', (user_id,))
    return cursor.fetchone() is not None

# Состояние заполнения формы для каждого пользователя (ключ – user_id)
user_forms = {}

# Список вопросов (9 вопросов) для формы
questions = [
    "Введите никнейм:",
    "Ваш сервер?:",
    "Укажите вашу должность:",
    "За какое число вы подаете отчёт?:",
    "Проделанная работа:",
    "Доказательства(Загружать доказательства через imgur,япикс):",
    "Брали ли вы дополнительное задание(Если Да то какое и у кого брали?):",
    "Доказательства выполненого дополнительного задания:",
    "Какие наказание вы выдавали(Для лидеров /members)?:"
]

def save_submission(user_id, answers):
    cursor.execute('''
        INSERT INTO submissions 
        (user_id, nickname, direction, position_reason, discord, forum_link, vk_link, server, screenshot, admin_commands)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, answers[0], answers[1], answers[2], answers[3],
          answers[4], answers[5], answers[6], answers[7], answers[8]))
    conn.commit()

print("Бот запущен...")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        text = event.text.strip()
        user_id = event.user_id
        peer_id_event = event.peer_id
        # Если peer_id равен user_id, значит сообщение пришло в ЛС
        is_private = (peer_id_event == user_id)
        
        # Обработка команды /add для добавления нового администратора (только для админов)
        if text.startswith("/add"):
            if not is_admin(user_id):
                vk.messages.send(user_id=user_id,
                                 message="У вас нет прав для добавления администраторов.",
                                 random_id=int(time.time()*1000))
                continue
            parts = text.split()
            if len(parts) < 2:
                vk.messages.send(user_id=user_id,
                                 message="Используйте команду: /add [id123456|username] или /add @username или /add username",
                                 random_id=int(time.time()*1000))
                continue
            candidate = parts[1]
            candidate_id = None
            # Если кандидат указан в виде упоминания, например: [id123456|Name]
            if candidate.startswith('[') and candidate.endswith(']') and "id" in candidate:
                try:
                    inner = candidate[1:-1]  # удаляем [ и ]
                    if inner.startswith("id"):
                        candidate_id_str = inner.split("|")[0][2:]
                        candidate_id = int(candidate_id_str)
                except Exception as e:
                    candidate_id = None
            # Если кандидат указан в виде "id123456"
            elif candidate.startswith("id") and candidate[2:].isdigit():
                candidate_id = int(candidate[2:])
            # Если кандидат указан с @, убираем @
            elif candidate.startswith("@"):
                candidate = candidate[1:]
            # Если кандидат не определён как числовой id, пробуем разрешить короткое имя
            if candidate_id is None:
                try:
                    result = vk.utils.resolveScreenName(screen_name=candidate)
                    if result is None or result.get("type") != "user":
                        vk.messages.send(user_id=user_id,
                                         message="Невозможно добавить данного пользователя как администратора. Проверьте корректность ввода.",
                                         random_id=int(time.time()*1000))
                        continue
                    candidate_id = result.get("object_id")
                except Exception as e:
                    vk.messages.send(user_id=user_id,
                                     message=f"Ошибка при разрешении имени: {str(e)}",
                                     random_id=int(time.time()*1000))
                    continue
            add_admin(candidate_id, candidate)
            vk.messages.send(user_id=user_id,
                             message=f"Пользователь с ID {candidate_id} добавлен как администратор.",
                             random_id=int(time.time()*1000))
            vk.messages.send(user_id=candidate_id,
                             message="Вам предоставлены права администратора.",
                             random_id=int(time.time()*1000))
            continue





    # Обработка команды /unadmin для снятия административных прав (только для админов)
    if text.startswith("/unadmin"):
        if not is_admin(user_id):
            vk.messages.send(user_id=user_id,
                             message="У вас нет прав для снятия административных прав.",
                             random_id=int(time.time() * 1000))
            continue

        parts = text.split()
        if len(parts) < 2:
            vk.messages.send(user_id=user_id,
                             message="Используйте команду: /unadmin [id123456|username] или /unadmin @username или /unadmin username",
                             random_id=int(time.time() * 1000))
            continue

        candidate = parts[1]
        candidate_id = None
        
        # Если кандидат указан в виде упоминания, например: [id123456|Name]
        if candidate.startswith('[') and candidate.endswith(']') and "id" in candidate:
            try:
                inner = candidate[1:-1]  # удаляем [ и ]
                if inner.startswith("id"):
                    candidate_id_str = inner.split("|")[0][2:]  # Получаем только id
                    candidate_id = int(candidate_id_str)
            except ValueError:
                candidate_id = None

        # Если кандидат указан в виде "id123456"
        elif candidate.startswith("id") and candidate[2:].isdigit():
            candidate_id = int(candidate[2:])

        # Если кандидат указан с @, убираем @
        elif candidate.startswith("@"):
            candidate = candidate[1:]

        # Если кандидат не определён как числовой id, пробуем разрешить короткое имя
        if candidate_id is None:
            try:
                result = vk.utils.resolveScreenName(screen_name=candidate)
                if result is None or result.get("type") != "user":
                    vk.messages.send(user_id=user_id,
                                     message="Невозможно снять права у данного пользователя. Проверьте корректность ввода.",
                                     random_id=int(time.time() * 1000))
                    continue
                candidate_id = result.get("object_id")
            except Exception as e:
                vk.messages.send(user_id=user_id,
                                 message=f"Ошибка при разрешении имени: {str(e)}",
                                 random_id=int(time.time() * 1000))
                continue

        # Проверяем, является ли пользователь администратором перед его удалением
        cursor.execute('SELECT * FROM admins WHERE user_id = ?', (candidate_id,))
        admin_check = cursor.fetchone()
        
        if admin_check is None:
            vk.messages.send(user_id=user_id,
                             message=f"Пользователь с ID {candidate_id} не является администратором.",
                             random_id=int(time.time() * 1000))
            continue

        remove_admin(candidate_id)
        vk.messages.send(user_id=user_id,
                         message=f"Пользователь с ID {candidate_id} снят с прав администратора.",
                         random_id=int(time.time() * 1000))
        vk.messages.send(user_id=candidate_id,
                         message="Ваши права администратора были сняты.",
                         random_id=int(time.time() * 1000))

    # Здесь можно добавить другие команды или логику обработки сообщений








        # Команда /forma для заполнения формы (работает только в ЛС)
        if text.startswith("/forma") and is_private:
            user_forms[user_id] = {"answers": [], "current_q": 0}
            vk.messages.send(user_id=user_id,
                             message=questions[0],
                             random_id=int(time.time()*1000))
            continue

        # Если пользователь заполняет форму (работает только в ЛС)
        if user_id in user_forms and is_private:
            state = user_forms[user_id]
            state["answers"].append(text)
            state["current_q"] += 1

            if state["current_q"] < len(questions):
                vk.messages.send(user_id=user_id,
                                 message=questions[state["current_q"]],
                                 random_id=int(time.time()*1000))
            else:
                # Форма заполнена – сохраняем данные и отправляем уведомление
                save_submission(user_id, state["answers"])
                del user_forms[user_id]
                vk.messages.send(user_id=user_id,
                                 message="Ваша форма успешно отправлена!",
                                 random_id=int(time.time()*1000))
                # Формируем итог формы для отправки администраторам
                form_text = (
                    f"Новая форма от пользователя {user_id}:\n"
                    f"Никнейм: {state['answers'][0]}\n"
                    f"Сервер: {state['answers'][1]}\n"
                    f"Должность: {state['answers'][2]}\n"
                    f"Число выполненой нормы: {state['answers'][3]}\n"
                    f"Проделанная работа: {state['answers'][4]}\n"
                    f"Доказательство проделанной работы: {state['answers'][5]}\n"
                    f"Дополнительное задания: {state['answers'][6]}\n"
                    f"Доказательства дополнительной работы: {state['answers'][7]}\n"
                    f"Выданные наказания: {state['answers'][8]}"
                )
               # Отправляем форму всем администраторам
                cursor.execute('SELECT user_id FROM admins')
                admins = cursor.fetchall()
                for admin in admins:
                    admin_id = admin[0]
                    vk.messages.send(user_id=admin_id,
                                     message=form_text,
                                     random_id=int(time.time()*1000))
            continue

        # Можно добавить обработку других команд или сообщений здесь.

forms = {}

def create_inline_keyboard(form_id):
    """
    Формирует inline-клавиатуру с двумя кнопками "Одобрено" и "Отклонить",
    которая отображается непосредственно под сообщением бота.
    Payload каждой кнопки содержит тип действия и идентификатор формы.
    """
    keyboard = {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Одобрено",
                        "payload": json.dumps({"button": "approve", "form_id": form_id})
                    },
                    "color": "positive"
                },
                {
                    "action": {
                        "type": "text",
                        "label": "Отклонить",
                        "payload": json.dumps({"button": "reject", "form_id": form_id})
                    },
                    "color": "negative"
                }
            ]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def get_user_mention(user_id):
    """
    Возвращает строку для упоминания пользователя в формате: [id12345|Имя Фамилия]
    """
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        first_name = user_info.get("first_name", "")
        last_name = user_info.get("last_name", "")
        return f"[id{user_id}|{first_name} {last_name}]"
    except Exception as e:
        print("Ошибка получения данных пользователя:", e)
        return f"[id{user_id}]"

def send_pm_or_chat(peer_id, user_id, message):
    """
    Пытается отправить ЛС (личное сообщение) пользователю.
    Если не удаётся (например, из-за настроек приватности), отправляет сообщение в беседу.
    """
    try:
        vk.messages.send(
            peer_id=user_id,
            random_id=int(time.time() * 1000),
            message=message,
            from_group=1
        )
        print(f"ЛС отправлено пользователю {user_id}: {message}")
    except Exception as e:
        print("Не удалось отправить ЛС, отправляем в беседу:", e)
        vk.messages.send(
            peer_id=peer_id,
            random_id=int(time.time() * 1000),
            message=message,
            from_group=1
        )

print("Бот запущен и работает в беседах...")

for event in longpoll.listen():
    try:
   
        print("Новое сообщение в peer_id:", event.peer_id)
        
        if event.type == VkEventType.MESSAGE_NEW:
      
            if hasattr(event, "payload") and event.payload:
                try:
                    payload = json.loads(event.payload)
                except Exception as e:
                    print("Ошибка декодирования payload:", e)
                    continue

                if "button" in payload and "form_id" in payload:
                    form_id = payload["form_id"]
                    button_type = payload["button"]
                    current_time = time.time()

                    if form_id not in forms:
                        vk.messages.send(
                            peer_id=event.peer_id,
                            random_id=int(time.time() * 1000),
                            message="Ошибка: Форма не найдена.",
                            from_group=1
                        )
                        continue

                    if forms[form_id].get("processed", False):
                        processed_time = forms[form_id].get("processed_time", current_time)
                        minutes_ago = int((current_time - processed_time) / 60)
                        status = forms[form_id].get("status", "обработана")
                        sender_mention = get_user_mention(forms[form_id]["sender_id"])
                        pm_text = f"Форма от {sender_mention} уже {status} {minutes_ago} минут назад."
                        send_pm_or_chat(event.peer_id, event.user_id, pm_text)
                        continue

                    try:
                        vk.messages.delete(
                            message_ids=event.message_id,
                            delete_for_all=1
                        )
                    except Exception as e:
                        print("Ошибка удаления сообщения с кнопкой:", e)

                    forms[form_id]["processed"] = True
                    forms[form_id]["processed_time"] = current_time
                    if button_type == "approve":
                        status_text = "одобрена"
                    elif button_type == "reject":
                        status_text = "отклонена"
                    else:
                        status_text = "обработана"
                    forms[form_id]["status"] = status_text

                    sender_id = forms[form_id]["sender_id"]
                    action_text = forms[form_id]["action"]
                    sender_mention = get_user_mention(sender_id)
                    actor_mention = get_user_mention(event.user_id)

                    if button_type == "approve":
                        response_text = f"{actor_mention} одобрил форму от {sender_mention} - {action_text}"
                    elif button_type == "reject":
                        response_text = f"{actor_mention} отклонил форму от {sender_mention} - {action_text}"
                    else:
                        response_text = "Неизвестное действие."

                    vk.messages.send(
                        peer_id=event.peer_id,
                        random_id=int(time.time() * 1000),
                        message=response_text,
                        from_group=1
                    )
                    continue

            if event.text.startswith("/af"):
                command_body = event.text[3:].strip()
                if " - " not in command_body:
                    vk.messages.send(
                        peer_id=event.peer_id,
                        random_id=int(time.time() * 1000),
                        message="Неверный формат команды. Используйте: /af NickName - действие",
                        from_group=1
                    )
                    continue

                nickname, action = command_body.split(" - ", 1)
                form_id = str(int(time.time() * 1000))

                try:
                    vk.messages.delete(
                        message_ids=event.message_id,
                        delete_for_all=1
                    )
                except Exception as e:
                    print("Ошибка удаления сообщения команды /af:", e)

                sender_mention = get_user_mention(event.user_id)
                form_message = f"Форма от {sender_mention} ({nickname}) отправил форму - {action}"
                keyboard = create_inline_keyboard(form_id)

                sent_message_id = vk.messages.send(
                    peer_id=event.peer_id,
                    random_id=int(time.time() * 1000),
                    message=form_message,
                    keyboard=keyboard,
                    from_group=1
                )

                forms[form_id] = {
                    "sender_id": event.user_id,
                    "nickname": nickname,
                    "action": action,
                    "processed": False
                }
    except Exception as e:
        print("Общая ошибка в обработке события:", e)