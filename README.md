# Songstery — Вебсайт для пошуку музичних рекомендацій до книг

## Опис проєкту

Songstery — це вебплатформа, що поєднує літературу та музику. Користувачі можуть шукати книги за назвою, автором чи обкладинкою, переглядати розділи без тексту, а також знаходити або додавати музичні композиції, які асоціюються з певними розділами.

## Використані технології

### Backend
- **Django 5.2.8** — веб-фреймворк
- **Django REST Framework** — REST API (`/api/v1/`)
- **SimpleJWT** — авторизація через JWT (access 15 хв / refresh 30 днів)
- **django-cors-headers** — CORS для фронтенд-клієнтів (Next.js)
- **django-filter** — фільтрація та пошук у API
- **Redis** — кешування токенів Spotify, результатів пошуку, rate limiting
- **SQLite / MySQL** — база даних

### Інтеграції
- **Spotify Web API** — Client Credentials flow, пошук треків
- **Open Library API** — пошук книг, обкладинки, ISBN

## Структура проєкту

```
songstery/
├── api/                        # REST API (DRF)
│   └── v1/
│       ├── filters/            # django-filter FilterSet'и
│       ├── pagination.py       # Cursor-based пагінація
│       ├── permissions.py      # Кастомні permission-класи
│       ├── serializers/        # Серіалайзери (по домену)
│       ├── services/           # Зовнішні інтеграції (Spotify, Open Library)
│       ├── views/               # API views (по домену)
│       └── urls.py
├── core/                       # Основний застосунок (server-rendered)
│   ├── migrations/
│   ├── models/                 # Моделі (по домену)
│   ├── static/core/
│   ├── templates/core/
│   ├── views/
│   ├── forms.py
│   ├── admin.py
│   └── urls.py
├── templates/                  # Загальні шаблони
├── songstery/                  # Налаштування проєкту
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
└── requirements.txt
```

## Інструкція запуску

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # і заповнити значення

python manage.py migrate
python manage.py createsuperuser  # опціонально
python manage.py runserver
```

Сайт: http://127.0.0.1:8000/
Адмінка: http://127.0.0.1:8000/admin/
API: http://127.0.0.1:8000/api/v1/

## API (Етап 3)

Базовий префікс: `/api/`

| Розділ | Ендпоінти |
|---|---|
| Авторизація | `POST /auth/register/`, `POST /auth/token/` (login), `POST /auth/token/refresh/`, `POST /auth/logout/`, `GET /auth/me/` |
| Книги | `GET /books/`, `POST /books/create/`, `GET /books/{slug}/`, `PATCH /books/{slug}/edit/`, `GET /books/{pk}/chapters/`, `playlists/`, `top-music/`, `POST save/`, `rate/` |
| Розділи | `GET /books/{book_id}/chapters/{num}/`, `GET/POST /chapters/{id}/music/`, `POST /books/{id}/chapters/bulk/` |
| Музика | `POST /music/{id}/like/`, `DELETE /music/{id}/` |
| Плейлісти | `POST /playlists/`, `GET /playlists/{slug}/`, `POST like/`, `tracks/` |
| Автори | `GET /authors/{slug}/`, `POST follow/` |
| Пошук | `GET /search/music/?q=` (Spotify), `GET /search/books/?q=` (Open Library) |
| Коментарі | `POST /comments/add/`, `DELETE /comments/{id}/delete/` |
| Верифікація | `POST /author-verification/` |
| Профіль | `GET/PATCH /profile/me/`, `GET /saved/`, `playlists/`, `recommendations/`, `notifications/`, `POST notifications/read/` |

Авторизація через JWT: `Authorization: Bearer <access_token>`.
Мова відповіді: `?lang=uk` або `?lang=en`.

> Точні шляхи й імена — в `api/urls.py`, це джерело правди.

## Поточний статус розробки

- Каталог книг, розділи, музичні рекомендації, плейлісти
- Модерація книг/розділів (Етап 0), rate limiting, валідація cover_url
- Переклади для Book/Chapter/Genre/Author (BookTranslation/ChapterTranslation/…)
- Авторизація (JWT + Google OAuth через allauth), профілі, верифікація авторів
- Система коментарів, лайків, нотифікацій
- REST API з JWT, фільтрацією, cursor-пагінацією — **весь список вище реально підключений і покритий тестами** (`core/tests.py`)
- Інтеграція з Spotify та Open Library

### Відомий технічний борг (не зроблено в цьому проході)

- **camelCase vs snake_case**: серіалайзери `books.py`/`music.py` віддають camelCase (`coverUrl`, `chaptersCount`), а `author.py`/`profile.py`/`notification.py` — snake_case. Треба вибрати одну конвенцію і привести все до неї.
- **Рік-фільтр книг** (`year_from`/`year_to` через django-filter) був у покинутому `BookViewSet`, але не перенесений у живий `BookListView` — зараз фільтрації по року немає.
- **i18n URL-префікси** (`/uk/`, `/en/`, `LocaleMiddleware`, `i18n_patterns`) — модель `Language` є, префіксів немає.
- **Cloudinary** для аватарів/медіа не підключено — досі локальний `ImageField`.
- `core/static/core/css/components/extras.css` — порожній файл, можна видалити.

## Автор

Songstery Project Team