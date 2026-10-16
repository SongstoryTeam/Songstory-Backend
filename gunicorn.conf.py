"""Налаштування gunicorn. Він сам підхоплює цей файл із кореня проєкту, тож команда запуску на Render не змінюється:
gunicorn songstery.wsgi:application

Потоки потрібні, бо пошук ходить до зовнішніх сервісів (до кількох секунд). З одним синхронним воркером
така відповідь блокувала б увесь сайт, а з потоками інші запити обробляються паралельно."""

import os

# WEB_CONCURRENCY gunicorn читає й сам; тут лише значення за замовчуванням.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"

# Пошук із повторами до Google може тривати до ~7 с, тож 30 с із запасом.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

# Не накопичуємо пам'ять: воркер перезапускається після ~1000 запитів (із розкидом, щоб не всі одразу).
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
