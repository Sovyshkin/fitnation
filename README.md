# FITNATION Notification Service

Небольшой production-ready сервис на Python 3.12 и FastAPI. Он принимает от 1С заранее определённые события, валидирует данные, рендерит HTML-письмо и отправляет его через корпоративный SMTP Яндекс 360.

## Архитектура

```text
1С → HTTPS/Nginx → FastAPI → EventService → TemplateService → EmailService → SMTP Яндекс
```

HTTP-слой не содержит бизнес-логику. `EventService` сопоставляет событие с темой и шаблоном, `TemplateService` безопасно рендерит Jinja2-шаблоны, а `EmailService` отвечает только за одну SMTP-отправку. Это позволяет позднее заменить прямую отправку задачей Redis/Celery и добавить БД, Telegram или SMS без переписывания API.

## Требования

- Python 3.12;
- Linux/macOS для локального запуска (Windows также поддерживается Python, но команды ниже для POSIX shell);
- SMTP-пароль приложения Яндекс 360;
- на сервере: Ubuntu 24.04, Nginx и systemd.

## Локальный запуск

```bash
git clone <repository-url> fitnation
cd fitnation
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

Заполните `.env`, затем запустите:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ: `{"status":"healthy"}`. Интерактивная документация доступна по адресу `http://127.0.0.1:8000/docs` только при `APP_ENV=development`; в production Swagger, ReDoc и OpenAPI endpoint отключены.

## Переменные окружения

Создайте `.env` из `.env.example`. Реальный `.env` исключён из Git. Обязательно замените:

- `API_KEY` — случайная строка длиной не менее 16 символов;
- `SMTP_PASSWORD` — пароль приложения Яндекс, не обычный пароль аккаунта;
- `SUPPORT_URL` — ссылка на чат поддержки;

Также проверьте `SMTP_USER`, `SMTP_FROM` и `SMTP_REPLY_TO`. Для FITNATION они равны `hello@fitnation.ru`. В production задайте `APP_ENV=production`. `SUPPORT_URL` должен использовать HTTPS. Логотип хранится в репозитории и добавляется к письму как inline-вложение. Секреты нельзя добавлять в systemd unit, Git или команды shell history. Если значение в `.env` содержит пробелы или `#`, заключите его в двойные кавычки — файл одновременно читают systemd и приложение.

## API

Все служебные POST endpoints принимают ключ в заголовке `X-API-Key`.

Отправка события из 1С:

```bash
curl --request POST http://127.0.0.1:8000/api/v1/events \
  --header 'Content-Type: application/json' \
  --header 'X-API-Key: YOUR_API_KEY' \
  --data '{
    "event": "WELCOME_DAY1",
    "recipient": {"email": "client@example.com", "name": "Анна"},
    "data": {
      "club_name": "FITNATION",
      "support_url": "https://t.me/your_support_chat"
    }
  }'
```

Успешный ответ:

```json
{"status":"sent","event":"WELCOME_DAY1","recipient":"client@example.com"}
```

`POST /api/v1/test-email` работает только при `APP_ENV=development` и дополнительно защищён API-ключом:

```bash
curl --request POST http://127.0.0.1:8000/api/v1/test-email \
  --header 'Content-Type: application/json' \
  --header 'X-API-Key: YOUR_API_KEY' \
  --data '{"to":"test@example.com"}'
```

В production endpoint отвечает `404`. Отдельная проверка SMTP без запуска API:

```bash
python scripts/smtp_test.py test@example.com
```

## Поддерживаемые события

- `WELCOME_DAY1`, `BONUS_DAY15`;
- `SUBSCRIPTION_4DAYS_BEFORE`, `SUBSCRIPTION_1DAY_BEFORE`;
- `SUBSCRIPTION_OVERDUE_DAY1`, `SUBSCRIPTION_OVERDUE_NEXT_DAY`, `SUBSCRIPTION_OVERDUE_DAY5`, `SUBSCRIPTION_OVERDUE_DAY10`;
- `MEMBERSHIP_4DAYS_BEFORE`, `MEMBERSHIP_EXPIRED_DAY1`, `MEMBERSHIP_EXPIRED_DAY5`, `MEMBERSHIP_EXPIRED_DAY10`.

Для напоминаний о подписке перед датой обязателен `next_payment_date`; для `MEMBERSHIP_4DAYS_BEFORE` и `MEMBERSHIP_EXPIRED_DAY1` — `membership_end_date`. Клиент не может передать произвольную тему или путь к шаблону.

## Тесты

```bash
pytest -q
```

SMTP во всех unit-тестах замокан: тесты не отправляют письма и не требуют доступа к сети.

## Развёртывание на Ubuntu 24.04

Первичная подготовка (команды с правами администратора):

```bash
sudo apt update
sudo apt install -y git nginx python3.12 python3.12-venv
sudo install -d -o fitnation -g fitnation /opt/fitnation
sudo -u fitnation git clone <repository-url> /opt/fitnation
sudo -u fitnation python3.12 -m venv /opt/fitnation/venv
sudo -u fitnation /opt/fitnation/venv/bin/pip install -r /opt/fitnation/requirements.txt
sudo -u fitnation cp /opt/fitnation/.env.example /opt/fitnation/.env
sudo chmod 600 /opt/fitnation/.env
sudo chown fitnation:fitnation /opt/fitnation/.env
```

Отредактируйте `/opt/fitnation/.env`, установите `APP_ENV=production` и реальные секреты.

### systemd

Путь в unit рассчитан на корень проекта `/opt/fitnation`; приложение импортируется как `app.main:app` из `WorkingDirectory=/opt/fitnation`.

```bash
sudo cp /opt/fitnation/systemd/fitnation.service.example /etc/systemd/system/fitnation.service
sudo systemctl daemon-reload
sudo systemctl enable --now fitnation.service
sudo systemctl status fitnation.service
journalctl -u fitnation.service -f
```

Используется один Uvicorn worker: это разумное значение для VPS с 1 vCPU и 1–2 GB RAM.

### Nginx

Пример `/etc/nginx/sites-available/fitnation`:

```nginx
limit_req_zone $binary_remote_addr zone=fitnation_api:10m rate=10r/s;

server {
    listen 80;
    server_name api.fitnation.ru;
    client_max_body_size 64k;
    limit_req zone=fitnation_api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 30s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fitnation /etc/nginx/sites-enabled/fitnation
sudo nginx -t
sudo systemctl reload nginx
```

После настройки DNS выпустите TLS-сертификат (например, Certbot) и принимайте события 1С только по HTTPS. Не публикуйте порт 8000 в UFW: наружу должны быть открыты только Nginx-порты 80/443 и административный SSH.

## Git workflow и обновление

Разработка ведётся локально в отдельной ветке, изменения проходят тесты и затем попадают в основную ветку:

```bash
git switch -c feature/notification-change
pytest -q
git add .
git commit -m "Describe notification change"
git push -u origin feature/notification-change
```

Ручное обновление сервера:

```bash
cd /opt/fitnation
git pull --ff-only
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart fitnation
sudo systemctl status fitnation
curl --fail http://127.0.0.1:8000/health
```

Альтернатива — явно запустить `/opt/fitnation/scripts/deploy.sh` от пользователя `fitnation`. Скрипт никогда не запускается автоматически и остановится, если в checkout есть изменения отслеживаемых Git-файлов. Пользователь `fitnation` должен иметь строго ограниченные sudo-разрешения только на `restart/status` данного сервиса. Не запускайте deploy-скрипт целиком через `sudo`: иначе Git может отклонить репозиторий из-за владельца (`safe.directory`), а файлы окружения получат неверного владельца.

## Логи и ошибки

Сервис пишет структурированные однострочные записи в stdout, которые собирает journald. Email маскируется, секреты и полный payload не логируются. Неверный ключ даёт `401`, неизвестное событие — `400`, ошибки валидации — `422`, а безопасно классифицированная ошибка SMTP — `502`. Внешнему клиенту не возвращаются ответы SMTP и stack trace.
