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

Базовий префікс: `/api/v1/`

| Розділ | Ендпоінти |
|---|---|
| Книги | `GET/POST /books/`, `GET/PATCH /books/{slug}/`, `chapters/`, `playlists/`, `music/`, `save/`, `rate/` |
| Розділи | `GET /chapters/{id}/`, `POST /chapters/{id}/music/` |
| Музика | `POST /music/{id}/like/`, `DELETE /music/{id}/` |
| Плейлісти | `GET /playlists/{slug}/`, `like/`, `tracks/` |
| Автори | `GET /authors/{slug}/`, `follow/` |
| Пошук | `GET /search/music/?q=`, `GET /search/books/?q=` |
| Коментарі | `POST /comments/`, `DELETE /comments/{id}/` |
| Верифікація | `POST /author-verification/` |
| Авторизація | `POST /auth/register/`, `login/`, `refresh/`, `logout/` |
| Профіль | `GET/PATCH /profile/me/`, `saved/`, `playlists/`, `recommendations/`, `notifications/` |

Авторизація через JWT: `Authorization: Bearer <access_token>`.
Мова відповіді: `?lang=uk` або `?lang=en`.

## Поточний статус розробки

- Каталог книг, розділи, музичні рекомендації, плейлісти
- Авторизація, профілі, верифікація авторів
- Система коментарів, лайків, нотифікацій
- REST API з JWT, фільтрацією, cursor-пагінацією
- Інтеграція з Spotify та Open Library

## Автор

Songstery Project Team
