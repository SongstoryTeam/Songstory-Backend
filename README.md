# Songstery

Музичні рекомендації до книг і окремих розділів для україномовної аудиторії.

Користувач знаходить книгу, бачить пісні, які до неї радять інші читачі, збирає плейлисти та радить власні треки до всієї книги або до конкретного розділу. Якщо трек уже хтось додавав, його можна порадити в один клік.

## Можливості

- Каталог книг, пошук по каталогу та в інтернеті (Google Books, Open Library, Apple Books; лише українські видання), імпорт книги в один клік
- Рекомендації треків (YouTube, Spotify) до книги та до розділу, групування за треком із лічильником
- Автоматичне підтягування назви й виконавця за посиланням (oEmbed, без API-ключів)
- Плейлисти, зібрані з треків, які вже порадили до книги
- Коментарі з відповідями
- Верифікація авторів із приватним сховищем документів
- Багатокроковий майстер реєстрації, вхід через Google
- Світла та темна теми, сторінка налаштувань
- PWA (манифест і service worker формуються з налаштувань), sitemap, robots.txt

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py sync_site
python manage.py createsuperuser
python manage.py runserver
```

Мінімально потрібні `SECRET_KEY` та `DEBUG`. Порожні змінні в `.env` вважаються незаданими й замінюються значеннями за замовчуванням. Без `DATABASE_URL` використовується SQLite, без `REDIS_URL` кеш і ліміти запитів працюють у пам'яті процесу (для кількох воркерів задайте `REDIS_URL`).

## Пошук книг

Запит одночасно йде в усі джерела з `BOOK_SOURCES`. Результати зливаються, дублікати (однакова назва й автор або ISBN) об'єднуються, видача ранжується: точний збіг назви, потім початок назви, потім решта. Якщо джерело не відповіло, користувач бачить, яке саме.

- Google Books без `GOOGLE_BOOKS_API_KEY` пропускається, бо спільна квота швидко вичерпується.
- Open Library просить представлятися в `User-Agent` (`EXTERNAL_HTTP_USER_AGENT`).
- Apple Books не повертає мову, тож українські видання визначаються за літерами назви.
- Невдале джерело ставиться на паузу на `EXTERNAL_FAILURE_COOLDOWN` секунд, щоб не гальмувати кожен запит.
- При імпорті дані книги беруться з кешу видачі; якщо кеш порожній (інший воркер, перезапуск), сервер повторює пошук за тим самим запитом.
- Апострофи (`'`, `’`, `ʼ`) і `ґ/г` у пошукових ключах зводяться до однієї форми, пунктуація ігнорується.

```bash
python manage.py check_book_sources "Шістка воронів"
python manage.py check_google_books "Кобзар"
python manage.py normalize_catalog
```

`check_book_sources` показує кожне джерело окремо (скільки знайшло й за який час) і підсумкову видачу. `check_google_books` пояснює, чому Google відмовляє (ключ, вимкнений API, квота). `normalize_catalog` перебудовує пошукові ключі та зливає дублікати авторів і книг у наявному каталозі.

## Тести та перевірки

```bash
python manage.py test
```

Тестовий раннер вимикає зовнішні джерела книг, тож тести не звертаються до мережі.

## Структура

```
core/
  models/      книги, музика, коментарі, профіль, верифікація
  services/    уся бізнес-логіка: каталог, джерела книг, посилання на треки, рекомендації
  views/       тонкі в'юхи за областями
  limits.py    довжини полів та інші числові межі
  text.py      нормалізація тексту й пошукові ключі
templates/pwa/ манифест і service worker
tests/         тести моделей, сервісів, в'юх і налаштувань
```

Налаштовувані значення (ліміти, таймаути, адреси зовнішніх сервісів, розміри сторінок, кольори PWA) зібрані в `songstery/settings.py`. Підтримувані музичні платформи описані в одному місці: `core/services/music_links.py`.

## Конфігурація

| Змінна | Призначення |
| --- | --- |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | базові налаштування Django |
| `SITE_NAME`, `SITE_DOMAIN`, `SITE_URL`, `SITE_CONTACT_EMAIL` | назва, адреса й контакт сайту |
| `DATABASE_URL`, `DB_CONN_MAX_AGE` | база даних і час життя з'єднань (Postgres) |
| `REDIS_URL`, `REDIS_CONNECT_TIMEOUT`, `REDIS_SOCKET_TIMEOUT`, `REDIS_COOLDOWN` | кеш; при недоступному Redis сайт переходить на кеш у пам'яті й повертається за `REDIS_COOLDOWN` секунд |
| `TRUSTED_PROXY_COUNT` | скільки reverse-proxy стоїть перед застосунком (Render або Nginx: 1); за замовчуванням 0 у режимі налагодження й 1 у проді, використовується для визначення IP клієнта в лімітах запитів |
| `BOOK_SOURCES` | джерела пошуку книг через кому: `google,openlibrary,apple` |
| `GOOGLE_BOOKS_API_KEY`, `GOOGLE_BOOKS_API_URL` | ключ і адреса Google Books; без ключа це джерело пропускається |
| `OPEN_LIBRARY_API_URL`, `APPLE_BOOKS_API_URL`, `EXTERNAL_HTTP_USER_AGENT` | адреси інших джерел і User-Agent для запитів |
| `PRIVATE_MEDIA_ROOT` | каталог для документів верифікації; у проді має бути постійним і недоступним ззовні |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | вхід через Google (якщо не задано, кнопка не показується) |
| `GOOGLE_SITE_VERIFICATION`, `GOOGLE_SITE_VERIFICATION_FILE` | підтвердження сайту в Google Search Console (мета-тег і назва файлу) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `ADMIN_EMAIL` | пошта для сповіщень про верифікацію |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | захист HTTPS у проді |
| `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `PLAUSIBLE_DOMAIN`, `DJANGO_LOG_LEVEL` | моніторинг, аналітика, журнал |
| `WEB_CONCURRENCY`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT` | параметри gunicorn (`gunicorn.conf.py`) |

## Статика

У проді використовується `core.storage.TolerantManifestStaticFilesStorage`: якщо файла немає в маніфесті, замість помилки віддається URL без хешу й пишеться попередження.

## Розгортання

`build.sh` встановлює залежності, збирає статику, застосовує міграції, синхронізує `Site` та створює суперкористувача зі змінних `DJANGO_SUPERUSER_*`.
