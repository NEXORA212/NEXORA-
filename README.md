# NEXORA

Бот-администратор для локального бизнеса: отвечает клиенту на сайте и в мессенджере,
записывает на услугу и присылает владельцу готовую заявку. Первая ниша — автосервисы.

Бизнес-план, оффер и скрипты продаж: [PLAN.md](PLAN.md).

## Запуск

Нужен только Python 3.10+, зависимостей нет.

```bash
python3 product/server.py                 # лендинг + виджет на http://localhost:8000
python3 product/server.py client.json     # с конфигом конкретного клиента
TG_TOKEN=... python3 product/telegram_bot.py client.json   # тот же бот в Telegram
cd product && python3 -m unittest         # тесты
```

Заявки пишутся в `leads.csv`. Уведомления владельцу включаются переменными окружения
`NOTIFY_TG_TOKEN` + `NOTIFY_TG_CHAT` и/или `NOTIFY_WEBHOOK` (любая CRM или мессенджер).

## Подключение клиента

1. Скопировать `product/config.example.json`, вписать услуги, цены, график, FAQ и ссылку на политику обработки данных.
2. Поднять `server.py` с этим конфигом на сервере в РФ.
3. Добавить на сайт клиента: `<script src="https://ВАШ-СЕРВЕР/widget.js"></script>`.

## Структура

- `product/engine.py` — диалог (не зависит от канала)
- `product/server.py` — веб-канал, API, сохранение и уведомления
- `product/telegram_bot.py` — Telegram-канал
- `site/` — лендинг и виджет
