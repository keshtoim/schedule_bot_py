FROM python:3.12-slim

# tzdata — чтобы TZ и системное время в контейнере были московскими
# (код и так считает по МСК через zoneinfo, это для логов и общей ясности).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Moscow \
    DATA_DIR=/data

WORKDIR /app

# Зависимости — отдельным слоем: переустанавливаются только при смене requirements.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
RUN pip install --no-deps .

# users.json, кеш книг, состояние дайджестов — переживают пересборку образа
VOLUME /data

CMD ["python", "-m", "schedule_bot"]
