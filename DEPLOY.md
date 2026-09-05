# Деплой

## Быстрый старт (Docker)

Нужен Docker с плагином Compose (`docker compose version`).

```bash
git clone https://github.com/keshtoim/schedule_bot_py.git
cd schedule_bot_py

cp .env.example .env
nano .env                 # вписать BOT_TOKEN и COLLEGE_PAGE_URL

docker compose up -d --build
docker compose logs -f    # смотрим, что поднялось
```

Всё. `restart: unless-stopped` поднимет контейнер после краша и ребута сервера.

## Переменные окружения (`.env`)

| Переменная | Обязательна | Что это |
|---|---|---|
| `BOT_TOKEN` | **да** | токен от @BotFather |
| `COLLEGE_PAGE_URL` | **да**\* | страница колледжа со ссылками на .xlsx |
| `SCHEDULE_SOURCE`, `ZAMENY_SOURCE` | \* | вместо `COLLEGE_PAGE_URL` — прямые ссылки/пути к файлам (режим отладки) |
| `TELEGRAM_PROXY` | нет | прокси к Telegram, если сервер его не видит. Для зарубежного сервера не нужен |
| `CACHE_TTL_MINUTES` | нет | кеш данных, по умолчанию 15 |
| `NOTIFY_START_TIME`, `NOTIFY_INTERVAL_HOURS` | нет | расписание проверок замен, по умолчанию 12:25 и раз в 3 ч |
| `LOG_LEVEL` | нет | `DEBUG`/`INFO`/`WARNING`/`ERROR`, по умолчанию `INFO` |

\* Нужен либо `COLLEGE_PAGE_URL`, либо пара `SCHEDULE_SOURCE` + `ZAMENY_SOURCE`.

`.env` в `.gitignore` — не коммить. Держи копию `BOT_TOKEN` в менеджере паролей
(потеря = перевыпуск у @BotFather, все `file_id` картинок при этом протухнут).

## Часовой пояс

Настраивать не надо. Бот всегда считает «сегодня/завтра», чётность недели и
время проверок замен по **Москве** (`Europe/Moscow`), где бы ни стоял сервер.
В Docker-образе системный TZ тоже выставлен в московский — для логов.

## Данные

Всё состояние — в волюме `bot-data` (внутри контейнера `/data`):

| Файл | Что |
|---|---|
| `users.json` | кто в какой группе — **единственный незаменимый файл** |
| `cache/` | скачанные книги расписания и замен (регенерируется) |
| `zameny-group-digests.json` | что уже разослано по группам (регенерируется, но сброс → лишняя рассылка) |
| `zameny-anomalies-notified.json` | какие опечатки в группах уже показывали |
| `last-restart-notify` | когда последний раз слали «бот обновлён» (не чаще раза в 12 ч) |

Волюм переживает `docker compose down` и пересборку образа. Пропадает только
при `docker compose down -v` или удалении волюма руками.

**Бэкап** (хотя бы `users.json`):
```bash
docker compose cp bot:/data ./data-backup       # весь каталог
# или разово в cron:
docker run --rm -v schedule_bot_py_bot-data:/d -v "$PWD":/out alpine \
  cp /d/users.json /out/users.json.$(date +%F)
```

## Обновление

```bash
git pull
docker compose up -d --build
```

Compose остановит старый контейнер и поднимет новый — второго инстанса не будет.

## Один инстанс

Telegram отдаёт `getUpdates` только одному процессу. Если запустить бота
дважды (локально при живом сервере, два контейнера) — оба получат
`Conflict: terminated by other getUpdates` и будут молотить вхолостую.
Бот пишет об этом понятным сообщением при старте. Для локальной разработки
заведи **отдельного тестового бота** у @BotFather с другим токеном.

## Перенос локального проекта на сервер

Проект переносится как есть. Если уже пользовался локально и не хочешь
терять пользователей — скопируй `data/users.json` в волюм:

```bash
scp data/users.json server:/tmp/users.json
ssh server 'docker compose -f /path/schedule_bot_py/compose.yml up -d'
ssh server 'docker cp /tmp/users.json schedule-bot:/data/users.json && docker restart schedule-bot'
```

## Логи

```bash
docker compose logs -f bot          # хвост
docker compose logs --since 1h bot  # за час
```

Ротация настроена в `compose.yml` (`max-size: 10m`, `max-file: 3`) — диск не забьётся.

## Без Docker (systemd)

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && pip install --no-deps .
cp .env.example .env && nano .env
```

`/etc/systemd/system/schedule-bot.service`:

```ini
[Unit]
Description=schedule-bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/schedule_bot_py
EnvironmentFile=/opt/schedule_bot_py/.env
Environment=DATA_DIR=/var/lib/schedule-bot
ExecStart=/opt/schedule_bot_py/.venv/bin/python -m schedule_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/lib/schedule-bot
sudo systemctl enable --now schedule-bot
journalctl -u schedule-bot -f
```
