import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InputMediaPhoto,
    InputMediaDocument,
    CallbackQuery,
)

from db import db
from config import BOT_TOKEN
from keyboards import (
    get_main_reply_keyboard,
    get_main_inline_keyboard,
    get_admin_manage_inline_keyboard,
    get_subjects_inline_keyboard,
    get_dates_inline_keyboard,
    get_edit_choice_inline_keyboard,
    get_cancel_inline_keyboard,
    get_files_collection_inline_keyboard,
    get_subject_catalog_inline_keyboard,
    get_edit_subject_catalog_inline_keyboard,
)
from schedule_utils import get_all_subjects_from_schedule
from utils import (
    escape_html_text,
    parse_date,
    format_date,
    get_time_remaining,
    is_admin,
    is_private_chat,
    is_allowed_thread,
    log_action,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= СОСТОЯНИЯ (FSM) =================

class AdminState(StatesGroup):
    waiting_for_subject = State()
    waiting_for_files = State()
    waiting_for_date = State()
    waiting_for_delete_id = State()
    waiting_for_edit_subject_filter = State()   # НОВОЕ: выбор предмета перед редактированием
    waiting_for_edit_id = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_desc = State()
    waiting_for_edit_subject = State()
    waiting_for_edit_date = State()
    waiting_for_edit_files = State()


class UserState(StatesGroup):
    viewing_subject_catalog = State()


# ================= ХЕНДЛЕРЫ =================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    logging.info("📩 /start от %s в чате %s", message.from_user.id, message.chat.id)
    await log_action(
        bot,
        f"Типок вызвал хуесоса id={message.from_user.id} "
        f"@{message.from_user.username or 'no_username'} "
        f"chat={message.chat.id} type={message.chat.type}",
    )

    await state.clear()
    adm = is_admin(message.from_user.id)
    private = is_private_chat(message.chat.type)

    text = "👋 Привет! Выберите раздел ниже:" if not adm else "👋 Привет, Администратор!"
    reply_kb = get_main_reply_keyboard(adm, private)
    inline_kb = get_main_inline_keyboard(adm, private)

    await message.answer(text, reply_markup=reply_kb)
    await message.answer("📌 Быстрый доступ:", reply_markup=inline_kb)


@dp.message(F.text == "🤖 Вызов бота")
async def bot_call_button(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    await state.clear()
    adm = is_admin(message.from_user.id)
    private = is_private_chat(message.chat.type)

    text = "👋 Главное меню!" if not adm else "👋 Главное меню администратора!"
    reply_kb = get_main_reply_keyboard(adm, private)
    inline_kb = get_main_inline_keyboard(adm, private)

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
        await message.answer(
            "⛔ Управление доступно только в личных сообщениях с ботом."
        )
        return

    await message.answer(
        "🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard()
    )


@dp.callback_query(F.data == "cmd_start")
async def callback_start(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Бот работает в другой теме", show_alert=True)
        return

    await state.clear()
    adm = is_admin(call.from_user.id)
    private = is_private_chat(call.message.chat.type)
    text = "👋 Главное меню!" if not adm else "👋 Главное меню администратора!"
    inline_kb = get_main_inline_keyboard(adm, private)

    try:
        await call.message.edit_text(text, reply_markup=inline_kb)
    except Exception:
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
        await call.message.edit_text(
            "🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard()
        )
    except Exception:
        await call.message.answer(
            "🛠 Панель управления:", reply_markup=get_admin_manage_inline_keyboard()
        )
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

    subjects = get_all_subjects_from_schedule()
    await state.update_data(subjects_list=subjects)

    await call.message.answer(
        "📚 Выберите предмет из расписания или введите вручную:",
        reply_markup=get_subjects_inline_keyboard(),
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_subject, F.data.startswith("subj_"))
async def admin_subject_selected(call: CallbackQuery, state: FSMContext):
    sub_id = call.data.replace("subj_", "")

    if sub_id == "manual":
        await call.message.answer("✍️ Введите название предмета:")
        await call.answer()
        return

    data = await state.get_data()
    subjects = data.get("subjects_list", get_all_subjects_from_schedule())

    try:
        idx = int(sub_id)
        subject = subjects[idx]
    except (ValueError, IndexError):
        await call.answer("⚠️ Ошибка выбора предмета", show_alert=True)
        return

    await state.update_data(subject=subject, files=[], description=None)
    await state.set_state(AdminState.waiting_for_files)

    logging.info(
        "📝 Ожидание файлов для предмета: %s (user: %s)",
        subject,
        call.from_user.id,
    )

    await call.message.answer(
        f"✅ Предмет: <b>{escape_html_text(subject)}</b>\n\n"
        f"📎 <b>Пришлите файлы или напишите текстовое описание:</b>\n"
        f"• Фото/документы — прикрепятся к ДЗ\n"
        f"• Текст — будет описанием задания\n\n"
        f"Нажмите «✅ Готово» когда закончите.",
        parse_mode="HTML",
        reply_markup=get_files_collection_inline_keyboard(),
    )
    await call.answer()


@dp.message(AdminState.waiting_for_files)
async def admin_add_file(message: Message, state: FSMContext):
    logging.info(
        "📩 Получено сообщение в state waiting_for_files от %s",
        message.from_user.id,
    )
    logging.info(
        "   Тип: photo=%s, document=%s, text=%s",
        bool(message.photo),
        bool(message.document),
        bool(message.text),
    )

    if not is_allowed_thread(message):
        logging.warning("⛔ Сообщение заблокировано фильтром тем")
        return

    if message.text and message.text in ["✅ Готово (файлы)", "❌ Отмена"]:
        logging.info("   Игнорируем текст кнопки: %s", message.text)
        return

    data = await state.get_data()
    files = data.get("files", [])

    if message.text and not data.get("description"):
        logging.info("   Сохраняем текст как описание: %s...", message.text[:50])
        await state.update_data(description=message.text)
        await message.answer(
            "📝 <b>Текст сохранен как описание!</b>\n\n"
            "Можете добавить файлы или нажать «✅ Готово».",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard(),
        )
        return
    elif message.text:
        logging.info("   Текст игнорируется (описание уже есть)")
        await message.answer(
            "ℹ️ Описание уже сохранено. Пришлите файл или нажмите «✅ Готово».",
            reply_markup=get_files_collection_inline_keyboard(),
        )
        return

    file_info = None
    if message.photo:
        file_info = {"file_id": message.photo[-1].file_id, "file_type": "photo"}
        logging.info("   Получено фото: %s", file_info["file_id"])
    elif message.document:
        file_info = {"file_id": message.document.file_id, "file_type": "document"}
        logging.info("   Получен документ: %s", file_info["file_id"])

    if file_info:
        files.append(file_info)
        await state.update_data(files=files)
        logging.info("   Файлов всего: %s", len(files))
        await message.answer(
            f"📎 <b>Файл принят!</b>\n"
            f"Всего файлов: {len(files)}\n\n"
            "Отправьте ещё или нажмите «✅ Готово».",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard(),
        )
    else:
        logging.warning("   Файл не распознан")
        await message.answer(
            "❌ <b>Не распознал файл.</b>\n\n"
            "Пришлите фото или документ.",
            parse_mode="HTML",
            reply_markup=get_files_collection_inline_keyboard(),
        )


@dp.callback_query(AdminState.waiting_for_files, F.data == "files_done")
async def admin_files_done_callback(call: CallbackQuery, state: FSMContext):
    logging.info("✅ Кнопка 'Готово' нажата (user: %s)", call.from_user.id)

    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    data = await state.get_data()
    files = data.get("files", [])
    description = data.get("description")

    logging.info("   Файлов: %s, Описание: %s", len(files), bool(description))

    if not files and not description:
        await call.answer("⚠️ Добавьте хотя бы файл или текст!", show_alert=True)
        return

    subject = data.get("subject", "")
    await state.set_state(AdminState.waiting_for_date)

    await call.message.answer(
        f"📅 <b>Выберите дату сдачи</b> для предмета:\n"
        f"<i>{escape_html_text(subject)}</i>",
        parse_mode="HTML",
        reply_markup=get_dates_inline_keyboard(subject),
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_date, F.data.startswith("date_"))
async def admin_date_selected(call: CallbackQuery, state: FSMContext):
    payload = call.data.replace("date_", "")

    if payload == "manual":
        await call.message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ:")
        await call.answer()
        return

    parts = payload.split("_", 1)
    if len(parts) < 2:
        await call.answer("⚠️ Ошибка даты", show_alert=True)
        return

    _, date_raw = parts
    try:
        date_str = f"{date_raw[:2]}.{date_raw[2:4]}.{date_raw[4:8]}"
        dt = parse_date(date_str)
        date_str = format_date(dt)
    except Exception:
        await call.answer("⚠️ Ошибка даты", show_alert=True)
        return

    data = await state.get_data()
    db.add_homework(
        subject=data["subject"],
        description=data.get("description") or "Без описания",
        files_list=data.get("files", []),
        deadline=date_str,
    )

    await log_action(
        bot,
        f"Пидор добавил дз admin={call.from_user.id} "
        f"subject='{data['subject']}' deadline={date_str} "
        f"files={len(data.get('files', []))}",
    )

    await state.clear()
    logging.info("✅ ДЗ добавлено: %s (до %s)", data["subject"], date_str)
    await call.message.answer(
        f"✅ Задание добавлено!\n📚 {escape_html_text(data['subject'])}\n📅 до {date_str}",
        parse_mode="HTML",
        reply_markup=get_admin_manage_inline_keyboard(),
    )
    await call.answer()


@dp.message(AdminState.waiting_for_date)
async def admin_add_date_manual(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    if message.text and message.text.startswith("❌"):
        await state.clear()
        adm = is_admin(message.from_user.id)
        private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(adm, private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return

    try:
        dt = parse_date(message.text)
        date_str = format_date(dt)
    except ValueError:
        await message.answer(
            "❌ Неверный формат! ДД.ММ.ГГГГ",
            reply_markup=get_cancel_inline_keyboard(),
        )
        return

    data = await state.get_data()
    db.add_homework(
        subject=data["subject"],
        description=data.get("description") or "Без описания",
        files_list=data.get("files", []),
        deadline=date_str,
    )

    await state.clear()
    logging.info("✅ ДЗ добавлено: %s", data["subject"])
    await message.answer(
        "✅ Задание добавлено!", reply_markup=get_admin_manage_inline_keyboard()
    )


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
        await call.message.answer(
            "Список пуст.", reply_markup=get_admin_manage_inline_keyboard()
        )
        await call.answer()
        return

    text = "Введите ID задания для удаления:\n\n"
    for hw in all_hw:
        subject = escape_html_text(hw["subject"])
        text += f"ID: <code>{hw['id']}</code> | {subject} ({hw['deadline']})\n"

    await state.set_state(AdminState.waiting_for_delete_id)
    await call.message.answer(
        text, parse_mode="HTML", reply_markup=get_cancel_inline_keyboard()
    )
    await call.answer()


@dp.message(AdminState.waiting_for_delete_id)
async def admin_delete_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    if message.text and message.text.startswith("❌"):
        await state.clear()
        adm = is_admin(message.from_user.id)
        private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(adm, private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return

    try:
        hw_id = int(message.text)
        db.delete_homework(hw_id)
        await log_action(
            bot,
            f"Парниша удалил дз admin={message.from_user.id} hw_id={hw_id}",
        )
        await state.clear()
        await message.answer(
            f"🗑 Задание #{hw_id} удалено.",
            reply_markup=get_admin_manage_inline_keyboard(),
        )
    except ValueError:
        await message.answer(
            "Введите число (ID).", reply_markup=get_cancel_inline_keyboard()
        )


# --- РЕДАКТИРОВАТЬ ДЗ ---

@dp.callback_query(F.data == "admin_edit")
async def admin_edit_list(call: CallbackQuery, state: FSMContext):
    """
    Новый сценарий:
    1) показываем список предметов, по которым есть ДЗ;
    2) после выбора предмета — список ID + дата + начало описания;
    3) затем админ вводит ID для редактирования.
    """
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в ЛС!", show_alert=True)
        return

    all_hw = db.get_all_homework()
    if not all_hw:
        await call.message.answer(
            "Список пуст.", reply_markup=get_admin_manage_inline_keyboard()
        )
        await call.answer()
        return

    subjects = sorted(list({hw["subject"] for hw in all_hw}))

    await state.update_data(
        edit_all_homework=[dict(hw) for hw in all_hw],
        edit_subjects=subjects,
    )
    await state.set_state(AdminState.waiting_for_edit_subject_filter)

    await call.message.answer(
        "📚 Выберите предмет, для которого хотите редактировать ДЗ:",
        reply_markup=get_edit_subject_catalog_inline_keyboard(subjects),
    )
    await call.answer()

@dp.callback_query(F.data.startswith("edit_id_"))
async def admin_edit_id_from_button(call: CallbackQuery, state: FSMContext):
    """
    Обработка клика по кнопке с конкретным ID ДЗ.
    Сразу открываем меню редактирования этого задания.
    """
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в ЛС!", show_alert=True)
        return

    hw_id_str = call.data.replace("edit_id_", "")
    try:
        hw_id = int(hw_id_str)
    except ValueError:
        await call.answer("⚠️ Некорректный ID", show_alert=True)
        return

    hw = db.get_homework_by_id(hw_id)
    if not hw:
        await call.answer("Такого задания нет", show_alert=True)
        return

    await state.update_data(edit_id=hw_id)
    await state.set_state(AdminState.waiting_for_edit_choice)

    files_count = len(json.loads(hw["files_json"])) if hw["files_json"] else 0
    subject = escape_html_text(hw["subject"])
    description = escape_html_text(hw["description"])
    text = (
        f"✏️ Редактирование #{hw_id}\n\n"
        f"📚 Предмет: <b>{subject}</b>\n"
        f"📝 Описание: <i>{description}</i>\n"
        f"📅 Дата: {hw['deadline']}\n"
        f"📎 Файлов: {files_count}\n\n"
        f"Что изменить?"
    )

    await call.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_edit_choice_inline_keyboard(),
    )
    await call.answer()


@dp.callback_query(
    AdminState.waiting_for_edit_subject_filter, F.data.startswith("edit_sub_")
)
async def admin_edit_subject_filter_selected(call: CallbackQuery, state: FSMContext):
    """
    Обработка выбора предмета для редактирования:
    показывает список ДЗ по выбранному предмету КНОПКАМИ.
    Каждая кнопка = одно ДЗ с ID, датой и началом описания.
    """
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещен", show_alert=True)
        return
    if not is_private_chat(call.message.chat.type):
        await call.answer("⛔ Только в ЛС!", show_alert=True)
        return

    data = await state.get_data()
    all_hw = data.get("edit_all_homework", [])
    subjects = data.get("edit_subjects", [])

    # edit_sub_{index}_{safe_name}
    parts = call.data.split("_")
    if len(parts) < 3:
        await call.answer("⚠️ Ошибка кнопки", show_alert=True)
        return

    try:
        idx = int(parts[2])
    except ValueError:
        await call.answer("⚠️ Ошибка выбора предмета", show_alert=True)
        return

    if idx < 0 or idx >= len(subjects):
        await call.answer("⚠️ Ошибка выбора предмета", show_alert=True)
        return

    selected_subject = subjects[idx]
    filtered_hw = [hw for hw in all_hw if hw["subject"] == selected_subject]

    if not filtered_hw:
        await call.answer("Заданий по этому предмету нет.", show_alert=True)
        return

    # Строим инлайн‑кнопки по каждому ДЗ
    kb = InlineKeyboardBuilder()

    # при большом количестве ДЗ можно ограничить, например, 20 последними
    filtered_hw_sorted = sorted(filtered_hw, key=lambda h: h["deadline"])
    for hw in filtered_hw_sorted:
        desc = (hw.get("description") or "").replace("\n", " ")
        short_desc = desc[:40] + "…" if len(desc) > 40 else desc
        btn_text = f"#{hw['id']} | {hw['deadline']} | {short_desc}"
        # на случай очень длинного текста кнопки
        if len(btn_text) > 64:
            btn_text = btn_text[:61] + "…"
        kb.button(
            text=btn_text,
            callback_data=f"edit_id_{hw['id']}",
        )

    kb.adjust(1)
    kb.button(text="❌ Отмена", callback_data="cmd_start")

    await call.message.answer(
        f"✏️ Выберите задание для редактирования по предмету:\n<b>{escape_html_text(selected_subject)}</b>",
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@dp.message(AdminState.waiting_for_edit_id)
async def admin_edit_id_process(message: Message, state: FSMContext):
    """
    После выбора предмета админ вводит ID нужного задания.
    Дальше логика такая же, как раньше: открываем меню редактирования этого ДЗ.
    """
    if not is_allowed_thread(message):
        return

    if message.text and message.text.startswith("❌"):
        await state.clear()
        adm = is_admin(message.from_user.id)
        private = is_private_chat(message.chat.type)
        reply_kb = get_main_reply_keyboard(adm, private)
        await message.answer("Отменено.", reply_markup=reply_kb)
        return

    try:
        hw_id = int(message.text)
        hw = db.get_homework_by_id(hw_id)
        if not hw:
            await message.answer(
                "Такого ID нет.", reply_markup=get_cancel_inline_keyboard()
            )
            return

        await state.update_data(edit_id=hw_id)
        await state.set_state(AdminState.waiting_for_edit_choice)

        files_count = len(json.loads(hw["files_json"])) if hw["files_json"] else 0
        subject = escape_html_text(hw["subject"])
        description = escape_html_text(hw["description"])
        text = (
            f"✏️ Редактирование #{hw_id}\n\n"
            f"📚 Предмет: <b>{subject}</b>\n"
            f"📝 Описание: <i>{description}</i>\n"
            f"📅 Дата: {hw['deadline']}\n"
            f"📎 Файлов: {files_count}\n\n"
            f"Что изменить?"
        )
        await message.answer(
            text, parse_mode="HTML", reply_markup=get_edit_choice_inline_keyboard()
        )
    except ValueError:
        await message.answer(
            "Введите число.", reply_markup=get_cancel_inline_keyboard()
        )


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_desc")
async def admin_edit_desc_choice(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_desc)
    await call.message.answer(
        "Введите новое описание:", reply_markup=get_cancel_inline_keyboard()
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_subject")
async def admin_edit_subject_choice(call: CallbackQuery, state: FSMContext):
    # сохраняем список предметов, чтобы по индексу получить реальное имя
    subjects = get_all_subjects_from_schedule()
    await state.update_data(subjects_list=subjects)
    await state.set_state(AdminState.waiting_for_edit_subject)
    await call.message.answer(
        "📚 Выберите предмет:", reply_markup=get_subjects_inline_keyboard()
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_date")
async def admin_edit_date_choice(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get("edit_id")
    hw = db.get_homework_by_id(hw_id)
    if hw:
        await state.set_state(AdminState.waiting_for_edit_date)
        await call.message.answer(
            f"📅 Выберите дату для {escape_html_text(hw['subject'])}:",
            parse_mode="HTML",
            reply_markup=get_dates_inline_keyboard(hw["subject"]),
        )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_files")
async def admin_edit_files_choice(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_edit_files)
    await state.update_data(edit_files=[])
    await call.message.answer(
        "Пришлите файлы. Нажмите «✅ Готово».",
        reply_markup=get_files_collection_inline_keyboard(),
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "edit_finish")
async def admin_edit_finish(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text(
            "✅ Готово!", reply_markup=get_admin_manage_inline_keyboard()
        )
    except Exception:
        await call.message.answer(
            "✅ Готово!", reply_markup=get_admin_manage_inline_keyboard()
        )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_choice, F.data == "cmd_start")
async def admin_edit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    adm = is_admin(call.from_user.id)
    private = is_private_chat(call.message.chat.type)
    try:
        await call.message.edit_text(
            "Отменено.", reply_markup=get_main_inline_keyboard(adm, private)
        )
    except Exception:
        await call.message.answer(
            "Отменено.", reply_markup=get_main_inline_keyboard(adm, private)
        )
    await call.answer()


@dp.message(AdminState.waiting_for_edit_desc)
async def admin_edit_desc_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    data = await state.get_data()
    db.update_homework(data["edit_id"], description=message.text)
    await log_action(
        bot,
        f"Чувачок изменил описание admin={message.from_user.id} hw_id={data['edit_id']}",
    )
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer(
        "✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard()
    )


@dp.message(AdminState.waiting_for_edit_subject)
async def admin_edit_subject_manual(message: Message, state: FSMContext):
    """Если админ выбрал «ввести предмет вручную»."""
    if not is_allowed_thread(message):
        return

    data = await state.get_data()
    db.update_homework(data["edit_id"], subject=message.text)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer(
        "✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard()
    )


@dp.callback_query(AdminState.waiting_for_edit_subject, F.data.startswith("subj_"))
async def admin_edit_subject_selected(call: CallbackQuery, state: FSMContext):
    sub_id = call.data.replace("subj_", "")
    if sub_id == "manual":
        await call.message.answer("✍️ Введите название предмета:")
        await call.answer()
        return

    data = await state.get_data()
    subjects = data.get("subjects_list", get_all_subjects_from_schedule())

    try:
        idx = int(sub_id)
        subject_name = subjects[idx]
    except (ValueError, IndexError):
        await call.answer("⚠️ Ошибка выбора предмета", show_alert=True)
        return

    db.update_homework(data["edit_id"], subject=subject_name)
    await log_action(
        bot,
        f"Хуила поменял предмет admin={call.from_user.id} "
        f"hw_id={data['edit_id']} subject='{subject_name}'",
    )
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer(
        f"✅ Предмет обновлён: {escape_html_text(subject_name)}",
        parse_mode="HTML",
        reply_markup=get_edit_choice_inline_keyboard(),
    )
    await call.answer()


@dp.message(AdminState.waiting_for_edit_date)
async def admin_edit_date_process(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    if message.text and message.text.startswith("❌"):
        await state.set_state(AdminState.waiting_for_edit_choice)
        await message.answer(
            "Выберите поле:", reply_markup=get_edit_choice_inline_keyboard()
        )
        return

    try:
        dt = parse_date(message.text)
        date_str = format_date(dt)
    except ValueError:
        await message.answer(
            "Ошибка формата!", reply_markup=get_cancel_inline_keyboard()
        )
        return

    data = await state.get_data()
    db.update_homework(data["edit_id"], deadline=date_str)
    await log_action(
        bot,
        f"Чертулай поменял дату admin={call.from_user.id} "
        f"hw_id={data['edit_id']} deadline={date_str}",
    )
    await state.set_state(AdminState.waiting_for_edit_choice)
    await message.answer(
        "✅ Обновлено!", reply_markup=get_edit_choice_inline_keyboard()
    )


@dp.callback_query(AdminState.waiting_for_edit_date, F.data.startswith("date_"))
async def admin_edit_date_selected(call: CallbackQuery, state: FSMContext):
    payload = call.data.replace("date_", "")

    if payload == "manual":
        await call.message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ:")
        await call.answer()
        return

    parts = payload.split("_", 1)
    if len(parts) < 2:
        await call.answer("⚠️ Ошибка даты", show_alert=True)
        return

    _, date_raw = parts
    try:
        date_str = f"{date_raw[:2]}.{date_raw[2:4]}.{date_raw[4:8]}"
        dt = parse_date(date_str)
        date_str = format_date(dt)
    except Exception:
        await call.answer("⚠️ Ошибка даты", show_alert=True)
        return

    data = await state.get_data()
    db.update_homework(data["edit_id"], deadline=date_str)
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer(
        f"✅ Дата обновлена: {date_str}", reply_markup=get_edit_choice_inline_keyboard()
    )
    await call.answer()


@dp.callback_query(AdminState.waiting_for_edit_files, F.data == "files_done")
async def admin_edit_files_done(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    data = await state.get_data()
    files = data.get("edit_files", [])
    if not files:
        await call.answer("Добавьте файлы!", show_alert=True)
        return

    db.update_homework(data["edit_id"], files_list=files)
    await log_action(
        bot,
        f"че за уебан поменял файлы admin={call.from_user.id} "
        f"hw_id={data['edit_id']} files={len(files)}",
    )
    await state.set_state(AdminState.waiting_for_edit_choice)
    await call.message.answer(
        "✅ Файлы обновлены!", reply_markup=get_edit_choice_inline_keyboard()
    )
    await call.answer()


@dp.message(AdminState.waiting_for_edit_files)
async def admin_edit_file_upload(message: Message, state: FSMContext):
    if not is_allowed_thread(message):
        return

    if message.text and message.text.startswith("❌"):
        await state.set_state(AdminState.waiting_for_edit_choice)
        await message.answer(
            "Отмена.", reply_markup=get_edit_choice_inline_keyboard()
        )
        return

    data = await state.get_data()
    files = data.get("edit_files", [])

    if message.photo:
        files.append({"file_id": message.photo[-1].file_id, "file_type": "photo"})
    elif message.document:
        files.append({"file_id": message.document.file_id, "file_type": "document"})
    else:
        return

    await state.update_data(edit_files=files)
    await message.answer(
        f"Файл добавлен ({len(files)})",
        reply_markup=get_files_collection_inline_keyboard(),
    )


# ================= ПРОСМОТР ДЗ =================
@dp.callback_query(F.data.startswith("view_hw_"))
async def user_view_homework_item(call: CallbackQuery, state: FSMContext):
    """
    Пользователь нажал на конкретное задание в каталоге.
    Показываем только это ДЗ (с файлами).
    """
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    hw_id_str = call.data.replace("view_hw_", "")
    try:
        hw_id = int(hw_id_str)
    except ValueError:
        await call.answer("⚠️ Некорректный ID", show_alert=True)
        return

    hw = db.get_homework_by_id(hw_id)
    if not hw:
        await call.answer("Задание не найдено", show_alert=True)
        return

    await log_action(
        bot,
        f"Какой то ебалай смотрит дз user={call.from_user.id} "
        f"@{call.from_user.username or 'no_username'} "
        f"hw_id={hw_id} subject='{hw['subject']}' deadline={hw['deadline']}",
    )

    data = await state.get_data()
    view_type = data.get("view_type", "active")
    show_status = view_type != "tomorrow"

    # показываем одно конкретное задание
    await send_homework_grouped(call.message, [dict(hw)], show_status=show_status)
    await call.answer()


@dp.callback_query(F.data.in_(["view_tomorrow", "view_active", "view_archive"]))
async def view_handler(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    action = call.data.split("_", 1)[1]



    today = datetime.now()
    today_str = format_date(today)
    tomorrow = today + timedelta(days=1)
    tomorrow_str = format_date(tomorrow)

    hw_list = []
    title = ""

    if action == "tomorrow":
        hw_list = db.get_homework_by_date(tomorrow_str)
        title = f"📅 ДЗ на завтра ({tomorrow_str})"

    elif action == "active":
        all_hw = db.get_all_homework()
        today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        for hw in all_hw:
            try:
                deadline_date = parse_date(hw["deadline"])
                if deadline_date >= today_date:
                    hw_list.append(hw)
            except Exception:
                pass
        title = "🔥 Активное ДЗ"

    elif action == "archive":
        all_hw = db.get_all_homework()
        today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        for hw in all_hw:
            try:
                deadline_date = parse_date(hw["deadline"])
                if deadline_date < today_date:
                    hw_list.append(hw)
            except Exception:
                hw_list.append(hw)
        title = "🗄 Архив"

    if not hw_list:
        adm = is_admin(call.from_user.id)
        private = is_private_chat(call.message.chat.type)
        try:
            await call.message.edit_text(
                f"{title}\nНичего не найдено.",
                reply_markup=get_main_inline_keyboard(adm, private),
            )
        except Exception:
            await call.message.answer(
                f"{title}\nНичего не найдено.",
                reply_markup=get_main_inline_keyboard(adm, private),
            )
        await call.answer()
        return

    subjects = sorted(list({hw["subject"] for hw in hw_list}))
    await state.update_data(
        view_type=action,
        homework_list=[dict(hw) for hw in hw_list],
        subjects=subjects,
    )
    await state.set_state(UserState.viewing_subject_catalog)

    try:
        await call.message.edit_text(
            f"{title}\nВыберите предмет:",
            reply_markup=get_subject_catalog_inline_keyboard(subjects, action),
        )
    except Exception:
        await call.message.answer(
            f"{title}\nВыберите предмет:",
            reply_markup=get_subject_catalog_inline_keyboard(subjects, action),
        )
    await call.answer()


@dp.callback_query(UserState.viewing_subject_catalog, F.data.startswith("all_"))
async def show_all_subjects(call: CallbackQuery, state: FSMContext):
    if not is_allowed_thread(call.message):
        await call.answer("❌ Не та тема", show_alert=True)
        return

    data = await state.get_data()
    hw_list = data.get("homework_list", [])
    view_type = data.get("view_type", "active")

    await state.clear()
    adm = is_admin(call.from_user.id)
    private = is_private_chat(call.message.chat.type)

    try:
        await call.message.edit_text(
            f"📂 Все задания ({len(hw_list)}):",
            reply_markup=get_main_inline_keyboard(adm, private),
        )
    except Exception:
        await call.message.answer(
            f"📂 Все задания ({len(hw_list)}):",
            reply_markup=get_main_inline_keyboard(adm, private),
        )
    await call.answer()

    await send_homework_grouped(
        call.message, hw_list, show_status=(view_type != "tomorrow")
    )


@dp.callback_query(UserState.viewing_subject_catalog, F.data.startswith("sub_"))
async def show_subject_homework(call: CallbackQuery, state: FSMContext):
    """
    Вместо мгновенного показа всех ДЗ по предмету
    показываем каталог-кнопки: дата + начало описания.
    По нажатию на кнопку открывается конкретное ДЗ.
    """
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
    subjects = data.get("subjects", [])
    hw_list = data.get("homework_list", [])

    try:
        idx = int(parts[1])
        if 0 <= idx < len(subjects):
            selected_subject = subjects[idx]
        else:
            selected_subject = subject_safe
    except Exception:
        selected_subject = subject_safe

    filtered_hw = [hw for hw in hw_list if hw["subject"] == selected_subject]
    if not filtered_hw:
        await call.answer("Заданий не найдено.", show_alert=True)
        return

    # Строим каталог-кнопки: для каждого ДЗ — отдельная кнопка
    kb = InlineKeyboardBuilder()

    # Можно отсортировать по дате дедлайна
    filtered_sorted = sorted(filtered_hw, key=lambda h: h["deadline"])
    for hw in filtered_sorted:
        desc = (hw.get("description") or "").replace("\n", " ")
        short_desc = desc[:40] + "…" if len(desc) > 40 else desc
        btn_text = f"{hw['deadline']} | {short_desc}"
        if len(btn_text) > 64:
            btn_text = btn_text[:61] + "…"

        kb.button(
            text=btn_text,
            callback_data=f"view_hw_{hw['id']}",  # обработаем отдельным хендлером
        )

    kb.adjust(1)
    kb.button(text="🔙 В меню", callback_data="cmd_start")

    try:
        await call.message.edit_text(
            f"📖 {selected_subject}\nВыберите задание:",
            reply_markup=kb.as_markup(),
        )
    except Exception:
        await call.message.answer(
            f"📖 {selected_subject}\nВыберите задание:",
            reply_markup=kb.as_markup(),
        )

    await call.answer()


# --- ОТПРАВКА ГРУПП ---

async def send_homework_grouped(
    message: Message,
    homework_list,
    show_status: bool = False,
    subject_filter: str | None = None,
):
    if not homework_list:
        return

    adm = is_admin(message.from_user.id) if hasattr(message, "from_user") else False
    private = (
        is_private_chat(message.chat.type) if hasattr(message, "chat") else True
    )
    reply_kb = get_main_reply_keyboard(adm, private)

    for hw in homework_list:
        text, files = format_homework_message(
            hw, show_status, include_subject=(subject_filter is None)
        )

        if not files:
            await message.answer(text, parse_mode="HTML", reply_markup=reply_kb)
            continue

        file_groups = [files[i : i + 10] for i in range(0, len(files), 10)]
        for file_group in file_groups:
            media_items = []
            for f in file_group:
                if f["file_type"] == "photo":
                    media_items.append(InputMediaPhoto(media=f["file_id"]))
                else:
                    media_items.append(InputMediaDocument(media=f["file_id"]))

            if media_items:
                try:
                    media_items[0].caption = text
                    media_items[0].parse_mode = "HTML"
                    await message.answer_media_group(media=media_items)
                    await message.answer("━━━━━━━━━━━━━━━━━━", reply_markup=reply_kb)
                except Exception as e:
                    logging.error("Ошибка медиа: %s", e)
                    for i, f in enumerate(file_group):
                        cap = text if i == 0 else ""
                        if f["file_type"] == "photo":
                            await message.answer_photo(
                                f["file_id"], caption=cap, parse_mode="HTML"
                            )
                        else:
                            await message.answer_document(
                                f["file_id"], caption=cap, parse_mode="HTML"
                            )
                    await message.answer("━━━━━━━━━━━━━━━━━━", reply_markup=reply_kb)

            await asyncio.sleep(0.5)


def format_homework_message(
    hw_row,
    show_status: bool = False,
    include_subject: bool = True,
) -> tuple[str, list]:
    subject = hw_row["subject"]
    desc = hw_row["description"]
    files_json = hw_row["files_json"]
    deadline = hw_row["deadline"]

    try:
        files = json.loads(files_json) if files_json else []
    except Exception:
        files = []

    subject = escape_html_text(subject)
    desc = escape_html_text(desc)

    status_icon = ""
    today_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        deadline_date = parse_date(deadline)
        if show_status:
            if deadline_date < today_date:
                status_icon = "🔴 (Просрочено)"
            else:
                status_icon = "🟢 (Активно)"
    except Exception as e:
        logging.error("Ошибка сравнения дат: %s", e)
        if show_status:
            status_icon = "⚪ (Ошибка даты)"

    text_parts = []
    if include_subject:
        text_parts.append(f"📚 <b>{subject}</b>")
    text_parts.append(f"📝 {desc}")
    text_parts.append(f"📅 До: {deadline}")
    if files:
        text_parts.append(f"📎 Файлов: {len(files)}")
    if show_status:
        text_parts.append(status_icon)
        try:
            if deadline_date >= today_date:
                text_parts.append(f"⏳ {get_time_remaining(deadline)}")
        except Exception:
            pass

    text = "\n".join(text_parts) + "\n"
    return text, files
# ================ЛОГИ СООБЩЕНИЙ ИЗ ЛС ПИДОРА===========

@dp.message()
async def log_private_messages(message: Message, state: FSMContext):
    """
    Логирует ЛЮБОЕ личное сообщение боту в лог-чат.
    Ничего не отвечает пользователю и не мешает другим хендлерам.
    """
    # Интересуют только личные чаты
    if message.chat.type != "private":
        return

    # Можно пропустить чисто служебные/медийные сообщения, если не нужны
    text_preview = ""
    if message.text:
        # обрежем, чтобы лог не раздувать
        t = message.text.replace("\n", " ")
        text_preview = t[:100] + "…" if len(t) > 100 else t
    elif message.caption:
        t = message.caption.replace("\n", " ")
        text_preview = t[:100] + "…" if len(t) > 100 else t
    else:
        text_preview = "<non-text message>"

    await log_action(
        bot,
        f"Этот парень пишет: from={message.from_user.id} "
        f"@{message.from_user.username or 'no_username'} "
        f"text=\"{text_preview}\"",
    )

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
        logging.error("Ошибка: %s", e)
        raise