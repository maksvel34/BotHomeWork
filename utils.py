import logging
from datetime import datetime, timedelta

from config import ADMIN_IDS, ALLOWED_THREAD_ID, LOG_CHAT_ID

logger = logging.getLogger(__name__)

DATE_FMT = "%d.%m.%Y"


def escape_html_text(text: str | None) -> str:
    """Экранирует HTML спецсимволы для безопасного отображения."""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, DATE_FMT)


def format_date(date: datetime) -> str:
    return date.strftime(DATE_FMT)


def get_time_remaining(deadline_str: str) -> str:
    """Возвращает оставшееся время до конца дня дедлайна."""
    try:
        dl = parse_date(deadline_str).replace(hour=23, minute=59, second=59)
        now = datetime.now()
        diff = dl - now
        if diff.total_seconds() < 0:
            return "Истекло"
        d = diff.days
        h, rem = divmod(diff.seconds, 3600)
        m, _ = divmod(rem, 60)
        return f"{d} дн. {h} ч. {m} мин."
    except Exception as e:
        logger.error(f"Ошибка расчёта времени: {e}")
        return "Ошибка даты"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_private_chat(chat_type: str) -> bool:
    return chat_type == "private"


def is_allowed_thread(message) -> bool:
    """Проверяет, в той ли теме написано сообщение / коллбек."""
    chat = getattr(message, "chat", None)
    chat_type = getattr(chat, "type", None)

    logger.debug(
        "🔍 Проверка темы: chat.type=%s, thread_id=%s",
        chat_type,
        getattr(message, "message_thread_id", None),
    )

    if chat_type == "private":
        logger.debug("   ✅ Личный чат — пропускаем")
        return True

    if ALLOWED_THREAD_ID is None:
        logger.debug("   ✅ ALLOWED_THREAD_ID=None — пропускаем")
        return True

    current_thread = getattr(message, "message_thread_id", None) or 1
    if current_thread != ALLOWED_THREAD_ID:
        logger.warning("   ⛔ Тема %s не совпадает с %s", current_thread, ALLOWED_THREAD_ID)
        return False

    logger.debug("   ✅ Тема %s разрешена", current_thread)
    return True

async def log_action(bot, text: str):
    """
    Отправляет служебное сообщение в лог-чат.
    Если LOG_CHAT_ID = 0 или не задан, ничего не делает.
    """
    if not LOG_CHAT_ID:
        return
    try:
        await bot.send_message(LOG_CHAT_ID, text)
    except Exception as e:
        logger.error("Не удалось отправить лог-сообщение: %s", e)