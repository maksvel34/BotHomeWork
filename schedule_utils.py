from datetime import datetime, timedelta, time
from functools import lru_cache

from config import SCHEDULE


def get_week_type(date: datetime | None = None) -> str:
    """Определяет тип недели (even/odd) для даты."""
    if date is None:
        date = datetime.now()
    week_number = date.isocalendar()[1]
    return "even" if week_number % 2 == 0 else "odd"


@lru_cache(maxsize=1)
def get_all_subjects_from_schedule() -> list[str]:
    """Извлекает все уникальные предметы из расписания."""
    subjects: set[str] = set()
    for week_type in SCHEDULE.values():
        for day_lessons in week_type.values():
            for lesson in day_lessons:
                name = lesson["name"]

                for prefix in [
                    "ЛК ",
                    "ПЗ ",
                    "ЛР ",
                    "1 подгруппа - ",
                    "2 подгруппа - ",
                    "нет пары | ",
                    " | 2 подгруппа - нет пары",
                ]:
                    name = name.replace(prefix, "")

                if " - " in name:
                    name = name.split(" - ")[0].strip()

                if name and name != "нет пары":
                    subjects.add(name.strip())

    return sorted(subjects)


def get_subject_dates(subject: str, count: int = 5) -> list[str]:
    """Находит ближайшие даты, когда есть предмет по расписанию (ДД.ММ.ГГГГ)."""
    dates: list[str] = []
    today = datetime.now().date()

    for i in range(28):  # смотрим на 4 недели вперёд
        if len(dates) >= count:
            break

        check_date = today + timedelta(days=i)
        week_type = get_week_type(datetime.combine(check_date, time(0, 0)))
        day_name = check_date.strftime("%A")

        if day_name in SCHEDULE.get(week_type, {}):
            for lesson in SCHEDULE[week_type][day_name]:
                lesson_name = lesson["name"]
                if subject in lesson_name and "нет пары" not in lesson_name:
                    dates.append(check_date.strftime("%d.%m.%Y"))
                    break

    return dates