import asyncio
import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, InputMediaPhoto, InputMediaDocument

# ================= КОНФИГУРАЦИЯ =================
# 🔐 Токен лучше хранить в переменных окружения (.env)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8538246825:AAG2lYfwxnvxbr6bOFydx5hIbcVFckvU3dc")
ADMIN_IDS = [7237228038, 1027040557, 1071264428]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# ================= БАЗА ДАННЫХ (SQLite) =================
class Database:
    def __init__(self, db_file):
        """✅ Исправлено: __init__ вместо init"""
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

        # Проверка и миграция старых данных
        self.cursor.execute("PRAGMA table_info(homework)")
        columns = [col[1] for col in self.cursor.fetchall()]

        if 'file_id' in columns and 'files_json' not in columns:
            logging.info("🔄 Выполняю миграцию старых данных...")
            self.cursor.execute("ALTER TABLE homework ADD COLUMN files_json TEXT")

            self.cursor.execute("SELECT id, file_id, file_type FROM homework WHERE file_id IS NOT NULL")
            for row in self.cursor.fetchall():
                hw_id, file_id, file_type = row
                if file_id:
                    files_list = [{'file_id': file_id, 'file_type': file_type or 'document'}]
                    files_json = json.dumps(files_list, ensure_ascii=False)
                    self.cursor.execute(
                        "UPDATE homework SET files_json = ? WHERE id = ?",
                        (files_json, hw_id)
                    )

        self.connection.commit()

    def add_homework(self, subject, description, files_list, deadline):
        query = """
        INSERT INTO homework (subject, description, files_json, deadline)
        VALUES (?, ?, ?, ?)
        """
        files_json = json.dumps(files_list, ensure_ascii=False)
        self.cursor.execute(query, (subject, description, files_json, deadline))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_all_homework(self):
        query = "SELECT * FROM homework ORDER BY deadline ASC"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_homework_by_date(self, target_date):
        query = "SELECT * FROM homework WHERE deadline = ?"
        self.cursor.execute(query, (target_date,))
        return self.cursor.fetchall()

    def get_homework_by_id(self, hw_id):
        query = "SELECT * FROM homework WHERE id = ?"
        self.cursor.execute(query, (hw_id,))
        return self.cursor.fetchone()

    def delete_homework(self, hw_id):
        query = "DELETE FROM homework WHERE id = ?"
        self.cursor.execute(query, (hw_id,))
        self.connection.commit()

    def update_homework(self, hw_id, subject=None, description=None, deadline=None, files_list=None):
        """✅ Исправлено: метод перемещён ВНУТРЬ класса"""
        updates = []
        values = []

        if subject is not None:
            updates.append("subject = ?")
            values.append(subject)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if deadline is not None:
            updates.append("deadline = ?")
            values.append(deadline)
        if files_list is not None:
            updates.append("files_json = ?")
            values.append(json.dumps(files_list, ensure_ascii=False))

        if not updates:
            return False

        values.append(hw_id)
        query = f"UPDATE homework SET {', '.join(updates)} WHERE id = ?"
        self.cursor.execute(query, values)
        self.connection.commit()
        return True


db = Database("school_bot.db")


# ================= МАШИНА СОСТОЯНИЙ (FSM) =================
class AdminState(StatesGroup):
    waiting_for_subject = State()
    waiting_for_files = State()
    waiting_for_date = State()
    waiting_for_delete_id = State()
    waiting_for_edit_id = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_subject = State()
    waiting_for_edit_desc = State()
    waiting_for_edit_date = State()
    waiting_for_edit_files = State()


class UserState(StatesGroup):
    viewing_subject_catalog = State()


# ================= КЛАВИАТУРЫ =================
def get_admin_main_keyboard():
    kb = [
        [KeyboardButton(text="🛠 Управление ДЗ")],
        [KeyboardButton(text="📅 ДЗ на завтра"), KeyboardButton(text="🔥 Активное ДЗ")],
        [KeyboardButton(text="🗄 Архив (Все ДЗ)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_admin_manage_keyboard():
    kb = [
        [KeyboardButton(text="➕ Добавить ДЗ")],
        [KeyboardButton(text="🗑 Удалить ДЗ"), KeyboardButton(text="✏️ Редактировать ДЗ")],
        [KeyboardButton(text="🔙 В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_edit_choice_keyboard():
    kb = [
        [KeyboardButton(text="📝 Изменить описание")],
        [KeyboardButton(text="📚 Изменить предмет")],
        [KeyboardButton(text="📅 Изменить дату")],
        [KeyboardButton(text="📎 Изменить файлы")],
        [KeyboardButton(text="✅ Завершить редактирование")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_user_main_keyboard():
    kb = [
        [KeyboardButton(text="📅 ДЗ на завтра"), KeyboardButton(text="🔥 Активное ДЗ")],
        [KeyboardButton(text="🗄 Архив (Все ДЗ)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_cancel_keyboard():
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_files_collection_keyboard():
    kb = [
        [KeyboardButton(text="✅ Готово")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_subject_catalog_keyboard(subjects):
    kb = []
    kb.append([KeyboardButton(text="📚 Все предметы")])

    for i in range(0, len(subjects), 2):
        row = []
        for j in range(2):
            if i + j < len(subjects):
                subject = subjects[i + j]
                display_name = subject[:18] + "…" if len(subject) > 18 else subject
                row.append(KeyboardButton(text=f"📖 {display_name}"))
        kb.append(row)

    kb.append([KeyboardButton(text="🔙 В главное меню")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ================= ИНИЦИАЛИЗАЦИЯ БОТА =================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def is_admin(user_id):
    return user_id in ADMIN_IDS


def get_keyboard_for_user(message: Message):
    if is_admin(message.from_user.id):
        return get_admin_main_keyboard()
    else:
        return get_user_main_keyboard()


def format_date_input(date_str):
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return dt.strftime("%Y-%m-%d"), dt
    except ValueError:
        return None, None


def get_time_remaining(deadline_str):
    try:
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        now = datetime.now()
        diff = deadline_date - now
        if diff.total_seconds() < 0:
            return "Срок истек"
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days} дн. {hours} ч. {minutes} мин."
    except Exception as e:
        logging.warning(f"Ошибка расчёта времени: {e}")
        return "Ошибка даты"


def format_homework_message(hw_row, show_status=False, include_subject=True):
    subject = hw_row['subject']
    desc = hw_row['description']
    files_json = hw_row['files_json']
    deadline = hw_row['deadline']

    try:
        files = json.loads(files_json) if files_json else []
    except json.JSONDecodeError:
        files = []

    status_icon = ""
    today_str = datetime.now().strftime("%Y-%m-%d")

    if show_status:
        if deadline < today_str:
            status_icon = "🔴 (Срок вышел)"
        else:
            status_icon = "🟢 (Активно)"

    text = ""
    if include_subject:
        text += f"📚 <b>{subject}</b>\n"
    text += f"📝 Задание: <i>{desc}</i>\n"
    text += f"📅 Сдать до: {deadline}\n"

    if files:
        text += f"📎 Файлов: {len(files)}\n"

    if show_status:
        text += f"Статус: {status_icon}\n"
        if deadline >= today_str:
            time_left = get_time_remaining(deadline)
            text += f"⏳ Осталось: {time_left}\n"

    return text, files


# ================= ХЕНДЛЕРЫ =================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = get_keyboard_for_user(message)
    if is_admin(message.from_user.id):
        await message.answer("Привет, Администратор! Выберите действие:", reply_markup=keyboard)
    else:
        await message.answer("Привет, Ученик! Выбирай раздел:", reply_markup=keyboard)


@dp.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    keyboard = get_keyboard_for_user(message)
    await message.answer("Отменено.", reply_markup=keyboard)


@dp.message(F.text == "🔙 В главное меню")
async def cmd_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    keyboard = get_keyboard_for_user(message)
    await message.answer("Возврат в главное меню.", reply_markup=keyboard)


# --- ЛОГИКА АДМИНИСТРАТОРА: МЕНЮ ---
@dp.message(F.text == "🛠 Управление ДЗ")
async def admin_manage_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Выберите операцию:", reply_markup=get_admin_manage_keyboard())


# --- ЛОГИКА АДМИНИСТРАТОРА: ДОБАВИТЬ ДЗ ---
@dp.message(F.text == "➕ Добавить ДЗ")
async def admin_add_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminState.waiting_for_subject)
    await message.answer("Введите название предмета (например, Математика):",
                         reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_subject)
async def admin_add_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text, files=[])
    await state.set_state(AdminState.waiting_for_files)
    await message.answer(
        "📎 Пришлите файлы, фото или напишите текстовое описание.\n"
        "Можно отправить несколько файлов подряд.\n"
        "Когда закончите — нажмите «✅ Готово»",
        reply_markup=get_files_collection_keyboard()
    )


@dp.message(AdminState.waiting_for_files, F.text == "✅ Готово")
async def admin_files_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get('files') and not data.get('description'):
        await message.answer("⚠️ Добавьте хотя бы один файл или текстовое описание!")
        return
    await state.set_state(AdminState.waiting_for_date)
    await message.answer("Введите дату сдачи в формате ДД.ММ.ГГГГ (например, 25.10.2024):",
                         reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_files)
async def admin_add_file(message: Message, state: FSMContext):
    if message.text in ["✅ Готово", "❌ Отмена"]:
        return

    # ✅ Исправлено: get_value() → get_data() для aiogram 3.x
    data = await state.get_data()
    files = data.get('files', [])

    if message.photo:
        file_id = message.photo[-1].file_id
        files.append({'file_id': file_id, 'file_type': 'photo'})
    elif message.document:
        file_id = message.document.file_id
        files.append({'file_id': file_id, 'file_type': 'document'})
    elif message.text and not data.get('description'):
        await state.update_data(description=message.text)
        await message.answer("📝 Описание сохранено. Можете добавить файлы или нажать «✅ Готово»")
        return

    await state.update_data(files=files)

    if files:
        await message.answer(f"📎 Файл добавлен! Всего: {len(files)}\n"
                             "Отправьте ещё или нажмите «✅ Готово»",
                             reply_markup=get_files_collection_keyboard())
    else:
        await message.answer("📝 Файл не распознан. Отправьте фото, документ или текст описания.")


@dp.message(AdminState.waiting_for_date)
async def admin_add_date(message: Message, state: FSMContext):
    date_str, _ = format_date_input(message.text)
    if not date_str:
        await message.answer("❌ Ошибка формата! Используйте ДД.ММ.ГГГГ. Попробуйте еще раз:")
        return

    data = await state.get_data()
    db.add_homework(
        subject=data['subject'],
        description=data.get('description', 'Без описания'),
        files_list=data.get('files', []),
        deadline=date_str
    )

    logging.info(f"✅ ДЗ добавлено: {data['subject']} (до {date_str})")
    await state.clear()
    await message.answer("✅ Задание успешно добавлено!",
                         reply_markup=get_admin_manage_keyboard())


# --- ЛОГИКА АДМИНИСТРАТОРА: УДАЛИТЬ ДЗ ---
@dp.message(F.text == "🗑 Удалить ДЗ")
async def admin_delete_list(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    all_hw = db.get_all_homework()
    if not all_hw:
        await message.answer("Список заданий пуст.", reply_markup=get_admin_manage_keyboard())
        return

    text = "Введите ID задания, которое нужно удалить:\n\n"
    for hw in all_hw:
        text += f"ID: {hw['id']} | {hw['subject']} (до {hw['deadline']})\n"

    await state.set_state(AdminState.waiting_for_delete_id)
    await message.answer(text, reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_delete_id)
async def admin_delete_process(message: Message, state: FSMContext):
    try:
        hw_id = int(message.text)
        db.delete_homework(hw_id)
        logging.info(f"🗑 ДЗ #{hw_id} удалено админом")
        await state.clear()
        await message.answer(f"Задание с ID {hw_id} удалено.", reply_markup=get_admin_manage_keyboard())
    except ValueError:
        await message.answer("Введите число (ID). Попробуйте еще раз:")


# --- ЛОГИКА АДМИНИСТРАТОРА: РЕДАКТИРОВАТЬ ДЗ ---
@dp.message(F.text == "✏️ Редактировать ДЗ")
async def admin_edit_list(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    all_hw = db.get_all_homework()
    if not all_hw:
        await message.answer("Список заданий пуст.", reply_markup=get_admin_manage_keyboard())
        return

    text = "Введите ID задания, которое нужно редактировать:\n\n"
    for hw in all_hw:
        text += f"ID: {hw['id']} | {hw['subject']} (до {hw['deadline']})\n"

    await state.set_state(AdminState.waiting_for_edit_id)
    await message.answer(text, reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_edit_id)
async def admin_edit_id_process(message: Message, state: FSMContext):
    try:
        hw_id = int(message.text)
        hw = db.get_homework_by_id(hw_id)

        if not hw:
            await message.answer("Такого ID нет. Введите корректный ID:")
            return

        await state.update_data(edit_id=hw_id)
        await state.set_state(AdminState.waiting_for_edit_choice)

        files = json.loads(hw['files_json']) if hw['files_json'] else []
        text = (
            f"📝 <b>Редактирование задания #{hw_id}</b>\n\n"
            f"📚 Предмет: {hw['subject']}\n"
            f"📝 Описание: {hw['description']}\n"
            f"📅 Дата: {hw['deadline']}\n"
            f"📎 Файлов: {len(files)}\n\n"
            f"Что хотите изменить?"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=get_edit_choice_keyboard())
    except ValueError:
        await message.answer("Введите число (ID):")


# 🔧 Выбор что редактировать
@dp.message(AdminState.waiting_for_edit_choice, F.text == "📝 Изменить описание")
async def admin_edit_desc_choice(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_desc)
    await message.answer("Введите новое описание задания:", reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_edit_choice, F.text == "📚 Изменить предмет")
async def admin_edit_subject_choice(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_subject)
    await message.answer("Введите новое название предмета:", reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_edit_choice, F.text == "📅 Изменить дату")
async def admin_edit_date_choice(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_date)
    await message.answer("Введите новую дату сдачи (ДД.ММ.ГГГГ):", reply_markup=get_cancel_keyboard())


@dp.message(AdminState.waiting_for_edit_choice, F.text == "📎 Изменить файлы")
async def admin_edit_files_choice(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_files)
    await state.update_data(edit_files=[])
    await message.answer(
        "📎 Пришлите новые файлы (фото/документы).\n"
        "Можно отправить несколько файлов.\n"
        "Нажмите «✅ Готово» когда закончите:",
        reply_markup=get_files_collection_keyboard()
    )


@dp.message(AdminState.waiting_for_edit_choice, F.text == "✅ Завершить редактирование")
async def admin_edit_finish(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Редактирование завершено!", reply_markup=get_admin_manage_keyboard())


# 🔧 Обработка новых файлов при редактировании
@dp.message(AdminState.waiting_for_edit_files, F.text == "✅ Готово")
async def admin_edit_files_done(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('edit_files', [])

    if not files:
        await message.answer("⚠️ Добавьте хотя бы один файл!")
        return

    hw_id = data.get('edit_id')
    db.update_homework(hw_id, files_list=files)

    logging.info(f"✏️ Файлы ДЗ #{hw_id} обновлены")
    await state.clear()
    await message.answer("✅ Файлы обновлены!", reply_markup=get_admin_manage_keyboard())


@dp.message(AdminState.waiting_for_edit_files)
async def admin_edit_file_upload(message: Message, state: FSMContext):
    if message.text in ["✅ Готово", "❌ Отмена"]:
        return

    # ✅ Исправлено: get_value() → get_data()
    data = await state.get_data()
    files = data.get('edit_files', [])

    if message.photo:
        file_id = message.photo[-1].file_id
        files.append({'file_id': file_id, 'file_type': 'photo'})
    elif message.document:
        file_id = message.document.file_id
        files.append({'file_id': file_id, 'file_type': 'document'})

    await state.update_data(edit_files=files)
    await message.answer(f"📎 Файл добавлен! Всего: {len(files)}",
                         reply_markup=get_files_collection_keyboard())


# 🔧 Обработка полей для редактирования
@dp.message(AdminState.waiting_for_edit_subject)
async def admin_edit_subject_process(message: Message, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get('edit_id')
    db.update_homework(hw_id, subject=message.text)

    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Предмет обновлён! Что ещё изменить?",
                         reply_markup=get_edit_choice_keyboard())


@dp.message(AdminState.waiting_for_edit_desc)
async def admin_edit_desc_process(message: Message, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get('edit_id')
    db.update_homework(hw_id, description=message.text)

    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Описание обновлено! Что ещё изменить?",
                         reply_markup=get_edit_choice_keyboard())


@dp.message(AdminState.waiting_for_edit_date)
async def admin_edit_date_process(message: Message, state: FSMContext):
    date_str, _ = format_date_input(message.text)
    if not date_str:
        await message.answer("❌ Ошибка формата! ДД.ММ.ГГГГ:")
        return

    data = await state.get_data()
    hw_id = data.get('edit_id')
    db.update_homework(hw_id, deadline=date_str)

    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer("✅ Дата обновлена! Что ещё изменить?",
                         reply_markup=get_edit_choice_keyboard())


# --- ЛОГИКА ПРОСМОТРА: КАТАЛОГ ПРЕДМЕТОВ ---
@dp.message(F.text == "📅 ДЗ на завтра")
async def view_tomorrow(message: Message, state: FSMContext):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    hw_list = db.get_homework_by_date(tomorrow)

    if not hw_list:
        keyboard = get_keyboard_for_user(message)
        await message.answer(f"📅 ДЗ на завтра ({tomorrow})\nНичего не найдено.", reply_markup=keyboard)
        return

    await state.set_state(UserState.viewing_subject_catalog)
    await state.update_data(
        view_type="tomorrow",
        homework_list=[dict(hw) for hw in hw_list],
        subjects=list(set(hw['subject'] for hw in hw_list))
    )

    subjects = list(set(hw['subject'] for hw in hw_list))
    subjects.sort()

    await message.answer(
        f"📂 Домашняя работа на завтра ({tomorrow})\nНайдено предметов: {len(subjects)}\n\n"
        "Выберите предмет или нажмите «📚 Все предметы»",
        reply_markup=get_subject_catalog_keyboard(subjects)
    )


@dp.message(F.text == "🔥 Активное ДЗ")
async def view_active(message: Message, state: FSMContext):
    all_hw = db.get_all_homework()
    today_str = datetime.now().strftime("%Y-%m-%d")
    active_hw = [hw for hw in all_hw if hw['deadline'] >= today_str]

    if not active_hw:
        keyboard = get_keyboard_for_user(message)
        await message.answer("🔥 Активная домашняя работа\nНичего не найдено.", reply_markup=keyboard)
        return

    await state.set_state(UserState.viewing_subject_catalog)
    await state.update_data(
        view_type="active",
        homework_list=[dict(hw) for hw in active_hw],
        subjects=list(set(hw['subject'] for hw in active_hw))
    )

    subjects = list(set(hw['subject'] for hw in active_hw))
    subjects.sort()

    await message.answer(
        f"📂 🔥 Активная домашняя работа\nНайдено предметов: {len(subjects)}\n\n"
        "Выберите предмет или нажмите «📚 Все предметы»",
        reply_markup=get_subject_catalog_keyboard(subjects)
    )


@dp.message(F.text == "🗄 Архив (Все ДЗ)")
async def view_archive(message: Message, state: FSMContext):
    all_hw = db.get_all_homework()
    today_str = datetime.now().strftime("%Y-%m-%d")
    sorted_hw = sorted(all_hw, key=lambda x: x['deadline'] < today_str)

    if not sorted_hw:
        keyboard = get_keyboard_for_user(message)
        await message.answer("🗄 Архив всех заданий\nНичего не найдено.", reply_markup=keyboard)
        return

    await state.set_state(UserState.viewing_subject_catalog)
    await state.update_data(
        view_type="archive",
        homework_list=[dict(hw) for hw in sorted_hw],
        subjects=list(set(hw['subject'] for hw in sorted_hw))
    )

    subjects = list(set(hw['subject'] for hw in sorted_hw))
    subjects.sort()

    await message.answer(
        f"📂 🗄 Архив всех заданий\nНайдено предметов: {len(subjects)}\n\n"
        "Выберите предмет или нажмите «📚 Все предметы»",
        reply_markup=get_subject_catalog_keyboard(subjects)
    )


# --- ОБРАБОТКА ВЫБОРА ПРЕДМЕТА ---
@dp.message(UserState.viewing_subject_catalog, F.text == "📚 Все предметы")
async def show_all_subjects(message: Message, state: FSMContext):
    data = await state.get_data()
    homework_list = data.get('homework_list', [])
    view_type = data.get('view_type', 'active')

    await state.clear()
    keyboard = get_keyboard_for_user(message)
    await send_homework_grouped(message, homework_list, show_status=(view_type != "tomorrow"))
    await message.answer("Выберите действие:", reply_markup=keyboard)


@dp.message(UserState.viewing_subject_catalog, F.text.startswith("📖 "))
async def show_subject_homework(message: Message, state: FSMContext):
    button_text = message.text
    data = await state.get_data()
    subjects = data.get('subjects', [])
    homework_list = data.get('homework_list', [])
    view_type = data.get('view_type', 'active')

    display_name = button_text[3:].rstrip("…")

    selected_subject = None
    for subject in subjects:
        if subject.startswith(display_name) or subject == display_name:
            selected_subject = subject
            break

    if not selected_subject:
        for subject in subjects:
            if display_name in subject:
                selected_subject = subject
                break

    if not selected_subject:
        await message.answer(f"⚠️ Предмет не найден: {button_text}")
        return

    filtered_hw = [hw for hw in homework_list if hw['subject'] == selected_subject]

    if not filtered_hw:
        await message.answer(f"📖 {selected_subject}\nЗаданий не найдено.")
        return

    await state.clear()
    keyboard = get_keyboard_for_user(message)
    await send_homework_grouped(message, filtered_hw, show_status=(view_type != "tomorrow"),
                                subject_filter=selected_subject)
    await message.answer("Выберите действие:", reply_markup=keyboard)


@dp.message(UserState.viewing_subject_catalog, F.text == "🔙 В главное меню")
async def back_from_catalog(message: Message, state: FSMContext):
    await state.clear()
    keyboard = get_keyboard_for_user(message)
    await message.answer("Возврат в главное меню.", reply_markup=keyboard)


# --- ОТПРАВКА ДЗ ГРУППАМИ ---
async def send_homework_grouped(message: Message, homework_list, show_status=False, subject_filter=None):
    """✅ Исправлено: весь цикл отправки теперь ВНУТРИ функции"""
    if not homework_list:
        await message.answer("Ничего не найдено.")
        return

    title = f"📖 {subject_filter}" if subject_filter else "📂 Все задания"
    await message.answer(f"{title}\nНайдено заданий: {len(homework_list)}")

    for hw in homework_list:
        text, files = format_homework_message(hw, show_status, include_subject=not subject_filter)

        if not files:
            await message.answer(text, parse_mode="HTML")
            continue

        file_groups = [files[i:i + 10] for i in range(0, len(files), 10)]

        for group_idx, file_group in enumerate(file_groups):
            media_items = []

            for file_info in file_group:
                file_id = file_info.get('file_id')
                file_type = file_info.get('file_type')

                if file_type == "photo" and file_id:
                    media_items.append(InputMediaPhoto(media=file_id))
                elif file_type == "document" and file_id:
                    media_items.append(InputMediaDocument(media=file_id))

            if media_items:
                try:
                    media_items[0].caption = text
                    media_items[0].parse_mode = "HTML"
                    await message.answer_media_group(media=media_items)
                except Exception as e:
                    logging.error(f"Ошибка отправки группы файлов: {e}")
                    for i, file_info in enumerate(file_group):
                        file_id = file_info.get('file_id')
                        file_type = file_info.get('file_type')
                        caption = text if i == 0 else f"📎 Файл {i + 1}"
                        try:
                            if file_type == "photo" and file_id:
                                await message.answer_photo(photo=file_id, caption=caption, parse_mode="HTML")
                            elif file_type == "document" and file_id:
                                await message.answer_document(document=file_id, caption=caption, parse_mode="HTML")
                        except Exception as ex:
                            logging.error(f"Не удалось отправить файл: {ex}")
                            await message.answer(f"⚠️ Не удалось отправить файл")

            await asyncio.sleep(0.5)


# ================= ЗАПУСК БОТА =================
async def main():
    print("🤖 Бот запущен и готов к работе...")
    logging.info("🚀 Бот стартовал")
    await bot.delete_webhook()
    await dp.start_polling(bot)


# ✅ Исправлено: __name__ == "__main__"
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен пользователем")
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise