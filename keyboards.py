from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from schedule_utils import get_all_subjects_from_schedule, get_subject_dates


def get_main_reply_keyboard(is_admin: bool, is_private_chat: bool):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🤖 Вызов бота")
    if is_admin and is_private_chat:
        builder.button(text="🛠 Управление ДЗ")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_main_inline_keyboard(is_admin: bool, is_private_chat: bool):
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
    """Кнопки с предметами из расписания (короткие callback_data)."""
    builder = InlineKeyboardBuilder()
    subjects = get_all_subjects_from_schedule()

    for i, subject in enumerate(subjects):
        display = subject[:18] + "…" if len(subject) > 18 else subject
        callback_data = f"subj_{i}"
        builder.button(text=f"📖 {display}", callback_data=callback_data)

    builder.button(text="✍️ Ввести вручную", callback_data="subj_manual")
    builder.button(text="❌ Отмена", callback_data="cmd_start")
    builder.adjust(2)
    return builder.as_markup()


def get_dates_inline_keyboard(subject: str):
    """Кнопки с ближайшими датами по предмету."""
    builder = InlineKeyboardBuilder()
    dates = get_subject_dates(subject, count=6)

    for i, date_str in enumerate(dates):
        callback_data = f"date_{i}_{date_str.replace('.', '')}"
        if len(callback_data) > 64:
            callback_data = f"date_{i}"

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


def get_subject_catalog_inline_keyboard(subjects: list[str], view_type: str):
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


def get_edit_subject_catalog_inline_keyboard(subjects: list[str]):
    """
    Каталог предметов специально для режима редактирования.
    callback_data: edit_sub_{index}_{safe_name}
    """
    builder = InlineKeyboardBuilder()

    for i, subject in enumerate(subjects):
        safe_name = subject[:20].replace(" ", "_").replace(".", "")
        callback_data = f"edit_sub_{i}_{safe_name}"
        if len(callback_data) > 64:
            callback_data = callback_data[:64]
        display_name = subject[:18] + "…" if len(subject) > 18 else subject
        builder.button(text=f"📖 {display_name}", callback_data=callback_data)

    builder.adjust(2)
    builder.button(text="🔙 В меню", callback_data="cmd_start")
    return builder.as_markup()