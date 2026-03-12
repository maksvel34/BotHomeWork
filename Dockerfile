# Базовый образ с Python
FROM python:3.11-slim

# Переменные окружения для Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Рабочая директория внутри контейнера
WORKDIR /app

# Установим системные пакеты, которые могут потребоваться (по минимуму)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Скопировать файлы зависимостей и установить зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать весь проект в контейнер
COPY . .

# По желанию: указать, какой файл БД использовать (будет создаваться внутри контейнера)
# ENV DB_FILE=school_bot.db

# Команда запуска бота
CMD ["python", "bot.py"]
