import asyncio
import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta, time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, InputMediaPhoto, InputMediaDocument,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8538246825:AAG2lYfwxnvxbr6bOFydx5hIbcVFckvU3dc")
ADMIN_IDS = [7237228038, 1027040557, 1071264428]
ALLOWED_THREAD_ID = 2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ================= РАСПИСАНИЕ =================
SCHEDULE = {
    "even": {
        "Monday": [
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Высшая математика", "room": "309А",
             "teacher": "доц. Вронский Б.М."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК История России", "room": "211А",
             "teacher": "доц. Манаев А.Ю."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Математическая логика и теория алгоритмов",
             "room": "306В", "teacher": "ст.пр. Степанова Е.И."},
            {"start": time(15, 00), "end": time(16, 30), "name": "ЛК Человек и право", "room": "309А",
             "teacher": "Шевченко В.И."},
        ],
        "Tuesday": [
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Цифровые технологии в профессиональной сфере",
             "room": "309А", "teacher": "доц. Филиппов Д.М."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ПЗ Цифровые технологии в профессиональной сфере",
             "room": "8А", "teacher": "доц. Филиппов Д.М."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Физическая культура", "room": "спортзал ТА",
             "teacher": "Ковальчук Елена Сергеевна"},
            {"start": time(15, 00), "end": time(16, 30), "name": "ПЗ История России", "room": "201В",
             "teacher": "Маргасов В.С."},
        ],
        "Wednesday": [
            {"start": time(9, 50), "end": time(11, 20), "name": "ПЗ Теория и технологии программирования",
             "room": "119А", "teacher": "Енина А.А."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК Теория и технологии программирования",
             "room": "18А", "teacher": "Степанов А.В"},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Иностранный язык", "room": "531Б",
             "teacher": "Ермоленко О.В."},
        ],
        "Thursday": [
            {"start": time(8, 00), "end": time(9, 30), "name": "ПЗ Высшая математика", "room": "302В",
             "teacher": "доц. Вронский Б.М."},
            {"start": time(9, 50), "end": time(11, 20), "name": "ПЗ Основы российской государственности",
             "room": "411В", "teacher": "Валуев Д.Г."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК Экономическая культура и финансовая грамотность",
             "room": "411В", "teacher": "Друзин Р.В."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Экономическая культура и финансовая грамотность",
             "room": "411В", "teacher": "Друзин Р.В."},
        ],
        "Friday": [
            {"start": time(8, 00), "end": time(9, 30), "name": "ПЗ Теория и технологии программирования",
             "room": "119А", "teacher": "Енина А.А."},
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Математическая логика и теория алгоритмов",
             "room": "302В", "teacher": "Степанова Е.И."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК Метрология, стандартизация и сертификация",
             "room": "301В", "teacher": "куратор группы Дементьев М.Ю."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Метрология, стандартизация и сертификация",
             "room": "301В", "teacher": "куратор группы Дементьев М.Ю."},
        ],
    },
    "odd": {
        "Monday": [
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Высшая математика", "room": "309А",
             "teacher": "доц. Вронский Б.М."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК История России", "room": "211А",
             "teacher": "доц. Манаев А.Ю."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Математическая логика и теория алгоритмов",
             "room": "306В", "teacher": "ст.пр. Степанова Е.И."},
        ],
        "Tuesday": [
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Цифровые технологии в профессиональной сфере",
             "room": "309А", "teacher": "доц. Филиппов Д.М."},
            {"start": time(11, 30), "end": time(13, 00), "name": "ПЗ Цифровые технологии в профессиональной сфере",
             "room": "8А", "teacher": "доц. Филиппов Д.М."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Физическая культура", "room": "спортзал ТА",
             "teacher": "Ковальчук Елена Сергеевна"},
            {"start": time(15, 00), "end": time(16, 30), "name": "ПЗ История России", "room": "201В",
             "teacher": "Маргасов В.С."},
        ],
        "Wednesday": [
            {"start": time(8, 00), "end": time(9, 30), "name": "ПЗ Теория и технологии программирования",
             "room": "119А", "teacher": "Енина А.А."},
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Теория и технологии программирования",
             "room": "18А", "teacher": "Степанов А.В"},
            {"start": time(11, 30), "end": time(13, 00), "name": "ЛК Основы российской государственности",
             "room": "309В", "teacher": "Валуев Д.Г."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ПЗ Иностранный язык", "room": "531Б",
             "teacher": "Ермоленко О.В."},
            {"start": time(15, 00), "end": time(16, 30), "name": "ПЗ Человек и право", "room": "301В",
             "teacher": "Шевченко В.И."},
        ],
        "Thursday": [
            {"start": time(8, 00), "end": time(9, 30), "name": "ПЗ Высшая математика", "room": "309А",
             "teacher": "доц. Вронский Б.М."},
            {"start": time(9, 50), "end": time(11, 20), "name": "ПЗ Основы российской государственности",
             "room": "304А", "teacher": "Валуев Д.Г."},
        ],
        "Friday": [
            {"start": time(8, 00), "end": time(9, 30), "name": "ПЗ Теория и технологии программирования",
             "room": "119А", "teacher": "Енина А.А."},
            {"start": time(9, 50), "end": time(11, 20), "name": "ЛК Математическая логика и теория алгоритмов",
             "room": "401В", "teacher": "Степанова Е.И."},
            {"start": time(13, 20), "end": time(14, 50), "name": "ЛК Материаловедение",
             "room": "ул.Генерала Васильева,32а (завод СЭЛМА)", "teacher": "Скиданчук А.Г."},
            {"start": time(15, 00), "end": time(16, 30), "name": "ПЗ Материаловедение",
             "room": "ул.Генерала Васильева,32а (завод СЭЛМА)", "teacher": "Скиданчук А.Г."},
        ],
    }
}


def is_allowed_thread(message):
    """Проверяет, в той ли теме написано сообщение"""
    logging.debug(
        f"🔍 Проверка темы: chat.type={message.chat.type}, thread_id={getattr(message, 'message_thread_id', None)}")

    # Личные сообщения ВСЕГДА пропускаются
    if message.chat.type == "private":
        logging.debug(f"   ✅ Личный чат — пропускаем")
        return True

    # Если фильтр тем не настроен — пропускаем все
    if ALLOWED_THREAD_ID is None:
        logging.debug(f"   ✅ ALLOWED_THREAD_ID=None — пропускаем")
        return True

    current_thread = getattr(message, 'message_thread_id', None) or 1
    if current_thread != ALLOWED_THREAD_ID:
        logging.warning(f"   ⛔ Тема {current_thread} не совпадает с {ALLOWED_THREAD_ID}")
        return False

    logging.debug(f"   ✅ Тема {current_thread} разрешена")
    return True
# ================= БАЗА ДАННЫХ =================
class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            files_json TEXT,
            deadline TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.cursor.execute("PRAGMA table_info(homework)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if 'file_id' in columns and 'files_json' not in columns:
            logging.info("🔄 Миграция старых данных...")
            self.cursor.execute("ALTER TABLE homework ADD COLUMN files_json TEXT")
            self.cursor.execute("SELECT id, file_id, file_type FROM homework WHERE file_id IS NOT NULL")
            for row in self.cursor.fetchall():
                hw_id, file_id, file_type = row
                if file_id:
                    files_list = [{'file_id': file_id, 'file_type': file_type or 'document'}]
                    self.cursor.execute(
                        "UPDATE homework SET files_json = ? WHERE id = ?",
                        (json.dumps(files_list, ensure_ascii=False), hw_id)
                    )
        self.connection.commit()

    def add_homework(self, subject, description, files_list, deadline):
        query = "INSERT INTO homework (subject, description, files_json, deadline) VALUES (?, ?, ?, ?)"
        self.cursor.execute(query, (subject, description, json.dumps(files_list, ensure_ascii=False), deadline))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_all_homework(self):
        self.cursor.execute("SELECT * FROM homework ORDER BY deadline ASC")
        return self.cursor.fetchall()

    def get_homework_by_date(self, target_date):
        self.cursor.execute("SELECT * FROM homework WHERE deadline = ?", (target_date,))
        return self.cursor.fetchall()

    def get_homework_by_id(self, hw_id):
        self.cursor.execute("SELECT * FROM homework WHERE id = ?", (hw_id,))
        return self.cursor.fetchone()

    def delete_homework(self, hw_id):
        self.cursor.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
        self.connection.commit()

    def update_homework(self, hw_id, subject=None, description=None, deadline=None, files_list=None):
        updates, values = [], []
        if subject: updates.append("subject = ?"); values.append(subject)
        if description: updates.append("description = ?"); values.append(description)
        if deadline: updates.append("deadline = ?"); values.append(deadline)
        if files_list is not None: updates.append("files_json = ?"); values.append(
            json.dumps(files_list, ensure_ascii=False))
        if not updates: return False
        values.append(hw_id)
        self.cursor.execute(f"UPDATE homework SET {', '.join(updates)} WHERE id = ?", values)
        self.connection.commit()
        return True


db = Database("school_bot.db")


# ================= СОСТОЯНИЯ (FSM) =================
class AdminState(StatesGroup):
    waiting_for_subject = State()
    waiting_for_files = State()
    waiting_for_date = State()
    waiting_for_delete_id = State()
    waiting_for_edit_id = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_desc = State()
    waiting_for_edit_subject = State()
    waiting_for_edit_date = State()
    waiting_for_edit_files = State()


class UserState(StatesGroup):
    viewing_subject_catalog = State()


# ================= ФУНКЦИИ ЭКРАНИРОВАНИЯ =================
def escape_html_text(text: str) -> str:
    """✅ Экранирует HTML спецсимволы для безопасного отображения"""
    if not text:
        return text
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


# ================= ФУНКЦИИ РАСПИСАНИЯ =================
def get_week_type(date: datetime = None) -> str:
    """Определяет тип недели (even/odd) для даты"""
    if date is None:
        date = datetime.now()
    # Номер недели в году
    week_number = date.isocalendar()[1]
    # Четная или нечетная
    return "even" if week_number % 2 == 0 else "odd"


def get_all_subjects_from_schedule() -> list:
    """Извлекает все уникальные предметы из расписания"""
    subjects = set()
    for week_type in SCHEDULE.values():
        for day_lessons in week_type.values():
            for lesson in day_lessons:
                # Очищаем название предмета от типа занятия (ЛК, ПЗ и т.д.)
                name = lesson['name']
                # Удаляем префиксы
                for prefix in ["ЛК ", "ПЗ ", "ЛР ", "1 подгруппа - ", "2 подгруппа - ", "нет пары | ",
                               " | 2 подгруппа - нет пары"]:
                    name = name.replace(prefix, "")
                # Берем основную часть названия
                if " - " in name:
                    name = name.split(" - ")[0].strip()
                if name and name != "нет пары":
                    subjects.add(name.strip())
    return sorted(list(subjects))


def get_subject_dates(subject: str, count: int = 5) -> list:
    """Находит ближайшие даты когда есть предмет по расписанию"""
    dates = []
    today = datetime.now().date()

    # Ищем на 4 недели вперед
    for i in range(28):
        if len(dates) >= count:
            break

        check_date = today + timedelta(days=i)
        week_type = get_week_type(datetime.combine(check_date, time(0, 0)))
        day_name = check_date.strftime("%A")  # Monday, Tuesday...

        # Проверяем расписание для этого дня
        if day_name in SCHEDULE.get(week_type, {}):
            for lesson in SCHEDULE[week_type][day_name]:
                lesson_name = lesson['name']
                # Проверяем совпадение с предметом
                if subject in lesson_name and "нет пары" not in lesson_name:
                    dates.append(check_date.strftime("%d.%m.%Y"))
                    break

    return dates


# ================= КЛАВИАТУРЫ =================
def get_main_reply_keyboard(is_admin, is_private_chat):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🤖 Вызов бота")
    if is_admin and is_private_chat:
        builder.button(text="🛠 Управление ДЗ")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_main_inline_keyboard(is_admin, is_private_chat):
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 ДЗ на завтра", callback_data="view_tomorrow")
    builder.button(text="🔥 Активное ДЗ", callback_data="view_active")
    builder.button(text="🗄 Архив", callback_data="view_archive")
    builder.adjust(3)
    return builder.as_markup()


def get_admin_manage_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить ДЗ", callback_data="admin_add")
    builder.button(text="🗑 Удалить ДЗ", callback_data="admin_delete")
    builder.button(text="✏️ Редактировать ДЗ", callback_data="admin_edit")
    builder.button(text="🔙 В главное меню", callback_data="cmd_start")
    builder.adjust(2, 2)
    return builder.as_markup()


def get_subjects_inline_keyboard():
    """✅ Кнопки с предметами из расписания (с безопасными callback_data)"""
    builder = InlineKeyboardBuilder()
    subjects = get_all_subjects_from_schedule()

    for i, subject in enumerate(subjects):
        # ✅ Используем индекс вместо полного названия (укладываемся в 64 байта)
        display = subject[:18] + "…" if len(subject) > 18 else subject
        callback_data = f"subj_{i}"  # Короткий ID: subj_0, subj_1, etc.
        builder.button(text=f"📖 {display}", callback_data=callback_data)

    builder.button(text="✍️ Ввести вручную", callback_data="subj_manual")
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    builder.adjust(2)
    return builder.as_markup()


def get_dates_inline_keyboard(subject: str):
    """✅ Кнопки с ближайшими датами по предмету"""
    builder = InlineKeyboardBuilder()
    dates = get_subject_dates(subject, count=6)

    for i, date_str in enumerate(dates):
        # ✅ Короткий callback_data
        callback_data = f"date_{i}_{date_str.replace('.', '')}"  # date_0_25032026
        if len(callback_data) > 64:
            callback_data = f"date_{i}"  # Ещё короче если нужно

        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            day_name = dt.strftime("%d.%m (%a)")
            builder.button(text=f"📅 {day_name}", callback_data=callback_data)
        except:
            builder.button(text=f"📅 {date_str}", callback_data=callback_data)

    builder.button(text="✍️ Ввести вручную", callback_data="date_manual")
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    builder.adjust(2)
    return builder.as_markup()


def get_edit_choice_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Описание", callback_data="edit_desc")
    builder.button(text="📚 Предмет", callback_data="edit_subject")
    builder.button(text="📅 Дата", callback_data="edit_date")
    builder.button(text="📎 Файлы", callback_data="edit_files")
    builder.button(text="✅ Готово", callback_data="edit_finish")
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_cancel_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    return builder.as_markup()


def get_files_collection_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово (файлы)", callback_data="files_done")
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    return builder.as_markup()


def get_subject_catalog_inline_keyboard(subjects, view_type):
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Все предметы", callback_data=f"all_{view_type}")

    for i, subject in enumerate(subjects):
        safe_name = subject[:20].replace(" ", "_").replace(".", "")
        callback_data = f"sub_{i}_{safe_name}_{view_type}"
        if len(callback_data) > 64:
            callback_data = callback_data[:64]
        display_name = subject[:18] + "…" if len(subject) > 18 else subject
        builder.button(text=f"📖 {display_name}", callback_data=callback_data)

    builder.adjust(2)
    builder.button(text="🔙 В меню", callback_data="cmd_start")
    return builder.as_markup()


# ================= ИНИЦИАЛИЗАЦИЯ =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= ПРОВЕРКИ =================
def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_private_chat(chat_type):
    return chat_type == "private"


def is_allowed_thread(message):
    if message.chat.type == "private":
        return True
    if ALLOWED_THREAD_ID is None:
        return True
    current_thread = getattr(message, 'message_thread_id', None) or 1
    if current_thread != ALLOWED_THREAD_ID:
        logging.debug(f"⛔ Игнорирую сообщение из темы {current_thread}")
        return False
    return True


# ================= ХЕНДЛЕРЫ =================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    logging.info(f"📩 /start от {message.from_user.id} в чате {message.chat.id}")
    await state.clear()
    is_adm = is_admin(message.from_user.id)
    is_private = is_private_chat(message.chat.type)
    text = "👋 Привет! Выберите раздел ниже:" if not is_adm else "👋 Привет, Администратор!"
    reply_kb = get_main_reply_keyboard(is_adm, is_private)
    inline_kb = get_main_inline_keyboard(is_adm, is_private)
    await message.answer(text, reply_markup=reply_kb)
    await message.answer("📌 Быстрый доступ:", reply_markup=inline_kb)


@dp.message(F.text == "🤖 Вызов бота")
async def bot_call_button(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    await state.clear()
    is_adm = is_admin(message.from_user.id)
    is_private = is_private_chat(message.chat.type)
    text = "👋 Главное меню!" if not is_adm else "👋 Главное меню администратора!"
    reply_kb = get_main_reply_keyboard(is_adm, is_private)
    inline_kb = get_main_inline_keyboard(is_adm, is_private)
    await message.answer(text, reply_markup=reply_kb)
    await message.answer("📌 Быстрый доступ:", reply_markup=inline_kb)


@dp.message(F.text == "🛠 Управление ДЗ")
async def admin_manage_button(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    if not is_private_chat(message.chat.type):
        await message.answer("⛔ Управление доступно только в личных сообщениях с ботом.")
        return
    await message.answer("🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard())


@dp.callback_query(F.data == "cmd_start")
async def callback_start(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Бот работает в другой теме", show_alert=True)
        return
    await state.clear()
    is_adm = is_admin(call.from_user.id)
    is_private = is_private_chat(call.message.chat.type)
    text = "👋 Главное меню!" if not is_adm else "👋 Главное меню администратора!"
    inline_kb = get_main_inline_keyboard(is_adm, is_private)
    try:
        await call.message.edit_text(text, reply_markup=inline_kb)
    except:
        await call.message.answer(text, reply_markup=inline_kb)
    await call.answer()


@dp.callback_query(F.data == "admin_manage")
async def admin_manage_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен.", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Управление доступно только в личных сообщениях", show_alert=True)
        return
    try:
        await call.message.edit_text("🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard())
    except:
        await call.message.answer("🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard())
    await call.answer()


# --- ДОБАВИТЬ ДЗ ---
@dp.callback_query(F.data == "admin_add")
async def admin_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Только для админов!", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в личных сообщениях!", show_alert=True)
        return

    await state.set_state(AdminState.waiting_for_subject)

    # ✅ Сохраняем список предметов в state для последующего использования
    subjects = get_all_subjects_from_schedule()
    await state.update_data(subjects_list=subjects)

    await call.message.answer(
        "📚 Выберите предмет из расписания или введите вручную:",
        reply_markup=get_subjects_inline_keyboard()
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_subject, F.data.startswith("subj_"))
async def admin_subject_selected(call: CallbackQuery, state: FSMContext):
    subject_id = call.data.replace("subj_", "")

    if subject_id == "manual":
        await call.message.answer("✍️ Введите название предмета:")
        await call.answer()
        return

    data = await state.get_data()
    subjects = data.get('subjects_list', get_all_subjects_from_schedule())

    try:
        idx = int(subject_id)
        subject = subjects[idx]
    except (ValueError, IndexError):
        await call.answer("⚠️ Ошибка выбора предмета", show_alert=True)
        return

    # ✅ Сохраняем предмет и файлы
    await state.update_data(subject=subject, files=[], description=None)
    await state.set_state(AdminState.waiting_for_files)

    logging.info(f"📝 Ожидание файлов для предмета: {subject} (user: {call.from_user.id})")

    await call.message.answer(
        f"✅ Предмет: <b>{escape_html_text(subject)}</b>\n\n"
        f"📎 <b>Пришлите файлы или напишите текстовое описание:</b>\n"
        f"• Фото/документы — прикрепятся к ДЗ\n"
        f"• Текст — будет описанием задания\n\n"
        f"Нажмите «✅ Готово» когда закончите.",
        parse_mode="HTML",
        reply_markup=get_files_collection_inline_keyboard()
    )
    await call.answer()


@dp.message(AdminState.waiting_for_files)
async def admin_add_file(message: Message, state: FSMContext):
    # ✅ Логирование для отладки
    logging.info(f"📩 Получено сообщение в state waiting_for_files от {message.from_user.id}")
    logging.info(f"   Тип: photo={bool(message.photo)}, document={bool(message.document)}, text={bool(message.text)}")

    if not is_allowed_thread(message):
        logging.warning(f"⛔ Сообщение заблокировано фильтром тем")
        return

    # ✅ Игнорируем команды отмены через текст
    if message.text and message.text in ["✅ Готово (файлы)", "❌ Отмена"]:
        logging.info(f"   Игнорируем текст кнопки: {message.text}")
        return

    data = await state.get_data()
    files = data.get('files', [])

    # ✅ Обработка текста как описания
    if message.text and not data.get('description'):
        logging.info(f"   Сохраняем текст как описание: {message.text[:50]}...")
        await state.update_data(description=message.text)
        await message.answer(
            "📝 <b>Текст сохранен как описание!</b>\n\n"
            "Можете добавить файлы или нажать «✅ Готово».",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard()
        )
        return
    elif message.text:
        # Текст есть, но описание уже сохранено — игнорируем
        logging.info(f"   Текст игнорируется (описание уже есть)")
        await message.answer("ℹ️ Описание уже сохранено. Пришлите файл или нажмите «✅ Готово».",
                             reply_markup=get_files_collection_inline_keyboard())
        return

    # ✅ Обработка файлов
    file_info = None
    if message.photo:
        file_info = {'file_id': message.photo[-1].file_id, 'file_type': 'photo'}
        logging.info(f"   Получено фото: {file_info['file_id']}")
    elif message.document:
        file_info = {'file_id': message.document.file_id, 'file_type': 'document'}
        logging.info(f"   Получен документ: {file_info['file_id']}")

    if file_info:
        files.append(file_info)
        await state.update_data(files=files)
        logging.info(f"   Файлов всего: {len(files)}")
        await message.answer(
            f"📎 <b>Файл принят!</b>\n"
            f"Всего файлов: {len(files)}\n\n"
            "Отправьте ещё или нажмите «✅ Готово».",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard()
        )
    else:
        logging.warning(f"   Файл не распознан")
        await message.answer(
            "❌ <b>Не распознал файл.</b>\n\n"
            "Пришлите фото или документ.",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard()
        )


@dp.callback_query(AdminState.waiting_for_files, F.data == "files_done")
async def admin_files_done_callback(call: CallbackQuery, state: FSMContext):
    logging.info(f"✅ Кнопка 'Готово' нажата (user: {call.from_user.id})")

    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    data = await state.get_data()
    files = data.get('files', [])
    description = data.get('description')

    logging.info(f"   Файлов: {len(files)}, Описание: {bool(description)}")

    if not files and not description:
        await call.answer("⚠️ Добавьте хотя бы файл или текст!", show_alert=True)
        return

    subject = data.get('subject', '')
    await state.set_state(AdminState.waiting_for_date)

    await call.message.answer(
        f"📅 <b>Выберите дату сдачи</b> для предмета:\n"
        f"<i>{escape_html_text(subject)}</i>",
        parse_mode="HTML",
        reply_markup=get_dates_inline_keyboard(subject)
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_date, F.data.startswith("date_"))
async def admin_date_selected(call: CallbackQuery, state: FSMContext):
    parts = call.data.replace("date_", "").split("_", 1)

    if parts[0] == "manual":
        await call.message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ:")
        await call.answer()
        return

    if len(parts) > 1:
        date_raw = parts[1]  # 25032026
        try:
            date_str = f"{date_raw[:2]}.{date_raw[2:4]}.{date_raw[4:8]}"
            datetime.strptime(date_str, "%d.%m.%Y")  # Проверка валидности
        except:
            await call.answer("⚠️ Ошибка даты", show_alert=True)
            return
    else:
        await call.answer("⚠️ Ошибка даты", show_alert=True)
        return

    data = await state.get_data()
    db.add_homework(
        subject=data['subject'],
        description=data.get('description') or "Без описания",
        files_list=data.get('files', []),
        deadline=date_str  # ✅ Сохраняем как DD.MM.YYYY
    )

    await state.clear()
    logging.info(f"✅ ДЗ добавлено: {data['subject']} (до {date_str})")
    await call.message.answer(
        f"✅ Задание добавлено!\n📚 {escape_html_text(data['subject'])}\n📅 до {date_str}",
        parse_mode="HTML",
        reply_markup=get_admin_manage_inline_keyboard()
    )
    await call.answer()


@dp.message(AdminState.waiting_for_date)
async def admin_add_date_manual(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if message.text and message.text.startswith("❌"):
        await state.clear()
        is_adm = is_admin(message.from_user.id)
        is_private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(is_adm, is_private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return

    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y")
        date_str = dt.strftime("%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат! ДД.ММ.ГГГГ", reply_markup=get_cancel_inline_keyboard())
        return

    data = await state.get_data()
    db.add_homework(
        subject=data['subject'],
        description=data.get('description') or "Без описания",
        files_list=data.get('files', []),
        deadline=date_str
    )

    await state.clear()
    logging.info(f"✅ ДЗ добавлено: {data['subject']}")
    await message.answer("✅ Задание добавлено!", reply_markup=get_admin_manage_inline_keyboard())


# --- УДАЛИТЬ ДЗ ---
@dp.callback_query(F.data == "admin_delete")
async def admin_delete_list(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в ЛС!", show_alert=True)
        return

    all_hw = db.get_all_homework()
    if not all_hw:
        await call.message.answer("Список пуст.", reply_markup=get_admin_manage_inline_keyboard())
        await call.answer()
        return

    text = "Введите ID задания для удаления:\n\n"
    for hw in all_hw:
        subject = escape_html_text(hw['subject'])
        text += f"ID: <code>{hw['id']}</code> | {subject} ({hw['deadline']})\n"

    await state.set_state(AdminState.waiting_for_delete_id)
    await call.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_inline_keyboard())
    await call.answer()


@dp.message(AdminState.waiting_for_delete_id)
async def admin_delete_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if message.text and message.text.startswith("❌"):
        await state.clear()
        is_adm = is_admin(message.from_user.id)
        is_private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(is_adm, is_private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return
    try:
        hw_id = int(message.text)
        db.delete_homework(hw_id)
        await state.clear()
        await message.answer(f"🗑 Задание #{hw_id} удалено.", reply_markup=get_admin_manage_inline_keyboard())
    except ValueError:
        await message.answer("Введите число (ID).", reply_markup=get_cancel_inline_keyboard())


# --- РЕДАКТИРОВАТЬ ДЗ ---
@dp.callback_query(F.data == "admin_edit")
async def admin_edit_list(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в ЛС!", show_alert=True)
        return

    all_hw = db.get_all_homework()
    if not all_hw:
        await call.message.answer("Список пуст.", reply_markup=get_admin_manage_inline_keyboard())
        await call.answer()
        return

    text = "Введите ID задания для редактирования:\n\n"
    for hw in all_hw:
        subject = escape_html_text(hw['subject'])
        text += f"ID: <code>{hw['id']}</code> | {subject} ({hw['deadline']})\n"

    await state.set_state(AdminState.waiting_for_edit_id)
    await call.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_inline_keyboard())
    await call.answer()


@dp.message(AdminState.waiting_for_edit_id)
async def admin_edit_id_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if message.text and message.text.startswith("❌"):
        await state.clear()
        is_adm = is_admin(message.from_user.id)
        is_private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(is_adm, is_private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return
    try:
        hw_id = int(message.text)
        hw = db.get_homework_by_id(hw_id)
        if not hw:
            await message.answer("Такого ID нет.", reply_markup=get_cancel_inline_keyboard())
            return

        await state.update_data(edit_id=hw_id)
        await state.set_state(AdminState.waiting_for_edit_choice)

        files_count = len(json.loads(hw['files_json'])) if hw['files_json'] else 0
        subject = escape_html_text(hw['subject'])
        description = escape_html_text(hw['description'])
        text = (
            f"✏️ Редактирование #{hw_id}\n\n"
            f"📚 Предмет: <b>{subject}</b>\n"
            f"📝 Описание: <i>{description}</i>\n"
            f"📅 Дата: {hw['deadline']}\n"
            f"📎 Файлов: {files_count}\n\n"
            f"Что изменить?"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=get_edit_choice_inline_keyboard())
    except ValueError:
        await message.answer("Введите число.", reply_markup=get_cancel_inline_keyboard())


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_desc")
async def admin_edit_desc_choice(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_desc)
    await call.message.answer("Введите новое описание:", reply_markup=get_cancel_inline_keyboard())
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_subject")
async def admin_edit_subject_choice(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_subject)
    await call.message.answer("📚 Выберите предмет:", reply_markup=get_subjects_inline_keyboard())
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_date")
async def admin_edit_date_choice(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get('edit_id')
    hw = db.get_homework_by_id(hw_id)
    if hw:
        await state.set_state(AdminState.waiting_for_edit_date)
        await call.message.answer(
            f"📅 Выберите дату для {escape_html_text(hw['subject'])}:",
            parse_mode="HTML",
            reply_markup=get_dates_inline_keyboard(hw['subject'])
        )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_files")
async def admin_edit_files_choice(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_files)
    await state.update_data(edit_files=[])
    await call.message.answer("Пришлите файлы. Нажмите «✅ Готово».",
                              reply_markup=get_files_collection_inline_keyboard())
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_finish")
async def admin_edit_finish(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("✅ Готово!", reply_markup=get_admin_manage_inline_keyboard())
    except:
        await call.message.answer("✅ Готово!", reply_markup=get_admin_manage_inline_keyboard())
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "cmd_start")
async def admin_edit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_adm = is_admin(call.from_user.id)
    is_private = is_private_chat(call.message.chat.type)
    try:
        await call.message.edit_text("Отменено.", reply_markup=get_main_inline_keyboard(is_adm, is_private))
    except:
        await call.message.answer("Отменено.", reply_markup=get_main_inline_keyboard(is_adm, is_private))
    await call.answer()


@dp.message(AdminState.waiting_for_edit_desc)
async def admin_edit_desc_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    data = await state.get_data()
    db.update_homework(data['edit_id'], description=message.text)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard())


@dp.message(AdminState.waiting_for_edit_subject)
async def admin_edit_subject_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    data = await state.get_data()
    db.update_homework(data['edit_id'], subject=message.text)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard())


@dp.callback_query(AdminState.waiting_for_edit_subject, F.data.startswith("subj_"))
async def admin_edit_subject_selected(call: CallbackQuery, state: FSMContext):
    subject = call.data.replace("subj_", "")
    if subject == "manual":
        await call.message.answer("✍️ Введите название предмета:")
        await call.answer()
        return
    data = await state.get_data()
    db.update_homework(data['edit_id'], subject=subject)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer(f"✅ Предмет обновлён: {escape_html_text(subject)}", parse_mode="HTML",
                              reply_markup=get_edit_choice_inline_keyboard())
    await call.answer()


@dp.message(AdminState.waiting_for_edit_date)
async def admin_edit_date_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if message.text and message.text.startswith("❌"):
        await state.set_state(AdminState.waiting_for_edit_choice)
        await message.answer("Выберите поле:", reply_markup=get_edit_choice_inline_keyboard())
        return
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y")
        date_str = dt.strftime("%d.%m.%Y")
    except ValueError:
        await message.answer("Ошибка формата!", reply_markup=get_cancel_inline_keyboard())
        return
    data = await state.get_data()
    db.update_homework(data['edit_id'], deadline=date_str)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard())


@dp.callback_query(AdminState.waiting_for_edit_date, F.data.startswith("date_"))
async def admin_edit_date_selected(call: CallbackQuery, state: FSMContext):
    date_str = call.data.replace("date_", "")
    if date_str == "manual":
        await call.message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ:")
        await call.answer()
        return
    data = await state.get_data()
    db.update_homework(data['edit_id'], deadline=date_str)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer(f"✅ Дата обновлена: {date_str}", reply_markup=get_edit_choice_inline_keyboard())
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_files, F.data == "files_done")
async def admin_edit_files_done(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return
    data = await state.get_data()
    files = data.get('edit_files', [])
    if not files:
        await call.answer("Добавьте файлы!", show_alert=True)
        return
    db.update_homework(data['edit_id'], files_list=files)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer("✅ Файлы обновлены!", reply_markup=get_edit_choice_inline_keyboard())
    await call.answer()


@dp.message(AdminState.waiting_for_edit_files)
async def admin_edit_file_upload(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return
    if message.text and message.text.startswith("❌"):
        await state.set_state(AdminState.waiting_for_edit_choice)
        await message.answer("Отмена.", reply_markup=get_edit_choice_inline_keyboard())
        return
    data = await state.get_data()
    files = data.get('edit_files', [])
    if message.photo:
        files.append({'file_id': message.photo[-1].file_id, 'file_type': 'photo'})
    elif message.document:
        files.append({'file_id': message.document.file_id, 'file_type': 'document'})
    else:
        return
    await state.update_data(edit_files=files)
    await message.answer(f"Файл добавлен ({len(files)})", reply_markup=get_files_collection_inline_keyboard())


# ================= ПРОСМОТР ДЗ =================
@dp.callback_query(F.data.startswith("view_"))
async def view_handler(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    action = call.data.split("_")[1]
    today_str = datetime.now().strftime("%d.%m.%Y")  # ✅ Исправлено: DD.MM.YYYY
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d.%m.%Y")  # ✅ Исправлено: DD.MM.YYYY

    hw_list = []
    title = ""

    if action == "tomorrow":
        hw_list = db.get_homework_by_date(tomorrow_str)
        title = f"📅 ДЗ на завтра ({tomorrow_str})"

    elif action == "active":
        all_hw = db.get_all_homework()
        # ✅ Исправлено: сравнение через datetime, не строки
        today_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hw_list = []
        for hw in all_hw:
            try:
                deadline_date = datetime.strptime(hw['deadline'], "%d.%m.%Y")
                if deadline_date >= today_date:
                    hw_list.append(hw)
            except:
                pass  # Пропускаем записи с неверной датой
        title = "🔥 Активное ДЗ"

    elif action == "archive":
        all_hw = db.get_all_homework()
        # ✅ Исправлено: сравнение через datetime
        today_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hw_list = []
        for hw in all_hw:
            try:
                deadline_date = datetime.strptime(hw['deadline'], "%d.%m.%Y")
                if deadline_date < today_date:
                    hw_list.append(hw)
            except:
                hw_list.append(hw)  # Показываем если дата некорректна
        title = "🗄 Архив"

    if not hw_list:
        is_adm = is_admin(call.from_user.id)
        is_private = is_private_chat(call.message.chat.type)
        try:
            await call.message.edit_text(f"{title}\nНичего не найдено.",
                                         reply_markup=get_main_inline_keyboard(is_adm, is_private))
        except:
            await call.message.answer(f"{title}\nНичего не найдено.",
                                      reply_markup=get_main_inline_keyboard(is_adm, is_private))
        await call.answer()
        return

    subjects = sorted(list(set(hw['subject'] for hw in hw_list)))
    await state.update_data(view_type=action, homework_list=[dict(hw) for hw in hw_list], subjects=subjects)
    await state.set_state(UserState.viewing_subject_catalog)
    try:
        await call.message.edit_text(f"{title}\nВыберите предмет:",
                                     reply_markup=get_subject_catalog_inline_keyboard(subjects, action))
    except:
        await call.message.answer(f"{title}\nВыберите предмет:",
                                  reply_markup=get_subject_catalog_inline_keyboard(subjects, action))
    await call.answer()


@dp.callback_query(UserState.viewing_subject_catalog, F.data.startswith("all_"))
async def show_all_subjects(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return
    data = await state.get_data()
    hw_list = data.get('homework_list', [])
    view_type = data.get('view_type', 'active')
    await state.clear()
    is_adm = is_admin(call.from_user.id)
    is_private = is_private_chat(call.message.chat.type)
    try:
        await call.message.edit_text(f"📂 Все задания ({len(hw_list)}):",
                                     reply_markup=get_main_inline_keyboard(is_adm, is_private))
    except:
        await call.message.answer(f"📂 Все задания ({len(hw_list)}):",
                                  reply_markup=get_main_inline_keyboard(is_adm, is_private))
    await call.answer()
    await send_homework_grouped(call.message, hw_list, show_status=(view_type != "tomorrow"))


@dp.callback_query(UserState.viewing_subject_catalog, F.data.startswith("sub_"))
async def show_subject_homework(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return
    parts = call.data.split("_")
    if len(parts) < 3:
        await call.answer("⚠️ Ошибка кнопки", show_alert=True)
        return
    view_type = parts[-1]
    subject_parts = parts[2:-1]
    subject_safe = "_".join(subject_parts).replace("_", " ")
    data = await state.get_data()
    subjects = data.get('subjects', [])
    hw_list = data.get('homework_list', [])
    try:
        idx = int(parts[1])
        if 0 <= idx < len(subjects):
            selected_subject = subjects[idx]
        else:
            selected_subject = subject_safe
    except:
        selected_subject = subject_safe
    filtered_hw = [hw for hw in hw_list if hw['subject'] == selected_subject]
    if not filtered_hw:
        await call.answer("Заданий не найдено.", show_alert=True)
        return
    await state.clear()
    is_adm = is_admin(call.from_user.id)
    is_private = is_private_chat(call.message.chat.type)
    try:
        await call.message.edit_text(f"📖 {selected_subject}", reply_markup=get_main_inline_keyboard(is_adm, is_private))
    except:
        await call.message.answer(f"📖 {selected_subject}", reply_markup=get_main_inline_keyboard(is_adm, is_private))
    await call.answer()
    await send_homework_grouped(call.message, filtered_hw, show_status=(view_type != "tomorrow"),
                                subject_filter=selected_subject)


# --- ОТПРАВКА ГРУПП ---
async def send_homework_grouped(message: Message, homework_list, show_status=False, subject_filter=None):
    if not homework_list:
        return
    is_adm = is_admin(message.from_user.id) if hasattr(message, 'from_user') else False
    is_private = is_private_chat(message.chat.type) if hasattr(message, 'chat') else True
    reply_kb = get_main_reply_keyboard(is_adm, is_private)
    for hw in homework_list:
        text, files = format_homework_message(hw, show_status, include_subject=not subject_filter)
        if not files:
            await message.answer(text, parse_mode="HTML", reply_markup=reply_kb)
            continue
        file_groups = [files[i:i + 10] for i in range(0, len(files), 10)]
        for group_idx, file_group in enumerate(file_groups):
            media_items = []
            for f in file_group:
                if f['file_type'] == 'photo':
                    media_items.append(InputMediaPhoto(media=f['file_id']))
                else:
                    media_items.append(InputMediaDocument(media=f['file_id']))
            if media_items:
                try:
                    media_items[0].caption = text
                    media_items[0].parse_mode = "HTML"
                    await message.answer_media_group(media=media_items)
                    await message.answer("━━━━━━━━━━━━━━━━━━", reply_markup=reply_kb)
                except Exception as e:
                    logging.error(f"Ошибка медиа: {e}")
                    for i, f in enumerate(file_group):
                        cap = text if i == 0 else ""
                        if f['file_type'] == 'photo':
                            await message.answer_photo(f['file_id'], caption=cap, parse_mode="HTML")
                        else:
                            await message.answer_document(f['file_id'], caption=cap, parse_mode="HTML")
                    await message.answer("━━━━━━━━━━━━━━━━━━", reply_markup=reply_kb)
            await asyncio.sleep(0.5)


def format_homework_message(hw_row, show_status=False, include_subject=True):
    subject = hw_row['subject']
    desc = hw_row['description']
    files_json = hw_row['files_json']
    deadline = hw_row['deadline']  # Формат: DD.MM.YYYY

    try:
        files = json.loads(files_json) if files_json else []
    except:
        files = []

    subject = escape_html_text(subject)
    desc = escape_html_text(desc)

    status_icon = ""

    # ✅ Исправлено: преобразуем обе даты в datetime для сравнения
    try:
        deadline_date = datetime.strptime(deadline, "%d.%m.%Y")
        today_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if show_status:
            if deadline_date < today_date:
                status_icon = "🔴 (Просрочено)"
            else:
                status_icon = "🟢 (Активно)"
    except Exception as e:
        logging.error(f"Ошибка сравнения дат: {e}")
        if show_status:
            status_icon = "⚪ (Ошибка даты)"

    text = ""
    if include_subject:
        text += f"📚 <b>{subject}</b>\n"
    text += f"📝 {desc}\n"
    text += f"📅 До: {deadline}\n"
    if files:
        text += f"📎 Файлов: {len(files)}\n"
    if show_status:
        text += f"{status_icon}\n"
        try:
            if deadline_date >= today_date:
                text += f"⏳ {get_time_remaining(deadline)}\n"
        except:
            pass

    return text, files


def get_time_remaining(deadline_str):
    """✅ Исправлено: правильный парсинг формата DD.MM.YYYY"""
    try:
        dl = datetime.strptime(deadline_str, "%d.%m.%Y").replace(hour=23, minute=59, second=59)
        now = datetime.now()
        diff = dl - now
        if diff.total_seconds() < 0:
            return "Истекло"
        d = diff.days
        h, rem = divmod(diff.seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{d} дн. {h} ч. {m} мин."
    except Exception as e:
        logging.error(f"Ошибка расчёта времени: {e}")
        return "Ошибка даты"


# ================= ЗАПУСК =================
async def main():
    logging.info("🤖 Бот запущен...")
    print("🤖 Бот запущен...")
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Стоп")
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        raise
