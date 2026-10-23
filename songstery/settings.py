from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")


def env_value(name: str, default: str) -> str:
    return env.str(name, default="").strip() or default


SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SITE_NAME = env_value("SITE_NAME", "Songstery")
SITE_DOMAIN = env_value("SITE_DOMAIN", "localhost:8000")
SITE_URL = env_value("SITE_URL", "http://localhost:8000")
SITE_CONTACT_EMAIL = env("SITE_CONTACT_EMAIL", default="")
SITE_ID = 1

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "django_ratelimit",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "songstery.urls"
WSGI_APPLICATION = "songstery.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
            ],
        },
    },
]

DATABASES = {"default": env.db_url_config(env_value("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))}
_database = DATABASES["default"]
if _database["ENGINE"] == "django.db.backends.postgresql":
    _database["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
    _database["CONN_HEALTH_CHECKS"] = True
    _database["DISABLE_SERVER_SIDE_CURSORS"] = True
    _database.setdefault("OPTIONS", {})["prepare_threshold"] = None
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "core.cache.ResilientRedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "socket_connect_timeout": env.float("REDIS_CONNECT_TIMEOUT", default=1.0),
                "socket_timeout": env.float("REDIS_SOCKET_TIMEOUT", default=1.0),
                "health_check_interval": 30,
                "cooldown": env.float("REDIS_COOLDOWN", default=15.0),
            },
        }
    }
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.W001"]
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

TEST_RUNNER = "core.testing.IsolatedTestRunner"

RATELIMIT_USE_CACHE = "default"
TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=0 if DEBUG else 1)
RATELIMIT_IP_META_KEY = "core.ratelimits.client_ip"
RATE_LIMITS = {
    "signup": "5/h",
    "signup_check": "30/m",
    "search": "60/m",
    "search_suggest": "180/m",
    "import_book": "20/h",
    "create_book": "10/h",
    "book_check": "60/m",
    "recommend": "30/h",
    "comment": "10/m",
    "playlist": "20/h",
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

PRIVATE_MEDIA_ROOT = Path(env_value("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {"BACKEND": "core.storage.PrivateMediaStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "core.storage.TolerantManifestStaticFilesStorage"
        )
    },
}
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_ADAPTER = "core.adapters.SocialAccountAdapter"
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {"client_id": GOOGLE_CLIENT_ID, "secret": GOOGLE_CLIENT_SECRET},
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    }
}
GOOGLE_SITE_VERIFICATION = env("GOOGLE_SITE_VERIFICATION", default="")
GOOGLE_SITE_VERIFICATION_FILE = env_value("GOOGLE_SITE_VERIFICATION_FILE", "googlef9b06c02e8f2e7fc.html")

SITE_DESCRIPTION = "Музичні рекомендації до книг і окремих розділів"
PWA_THEME_COLOR = "#C4622D"
PWA_BACKGROUND_COLOR = "#F7F3EE"
PWA_CACHE_VERSION = "v2"
PWA_ICON_PATH = "icons/icon-{size}.png"
PWA_ICON_SIZES = (192, 512)
PWA_FAVICON_SIZE = 192

CATALOG_LANGUAGE = "uk"
CATALOG_LANGUAGE_ISO3 = "ukr"
HOME_SHELF_SIZE = 12
CATALOG_PAGE_SIZE = 24
CATALOG_PAGE_WINDOW = 1
SEARCH_PAGE_SIZE = 24
SEARCH_SUGGEST_LIMIT = 6
SEARCH_SUGGEST_MIN_LENGTH = 2
SEARCH_SUGGEST_DEBOUNCE_MS = 350
SEARCH_SUGGEST_EXTERNAL_MIN_LENGTH = 3
SEARCH_SUGGEST_EXTERNAL_LIMIT = 5
TRACK_SEARCH_LIMIT = 12
BULK_CHAPTERS_MAX = 100
PENDING_BOOKS_LIMIT = 5
COMMENT_MAX_LENGTH = 2000

EXTERNAL_HTTP_TIMEOUT = 5
EXTERNAL_SEARCH_LIMIT = 10
EXTERNAL_SEARCH_CACHE_TTL = 60 * 60 * 24
GOOGLE_BOOKS_API_URL = env_value("GOOGLE_BOOKS_API_URL", "https://www.googleapis.com/books/v1/volumes")
GOOGLE_BOOKS_API_KEY = env("GOOGLE_BOOKS_API_KEY", default="").strip().strip("\"'")

BOOK_SOURCES = [name for name in env.list("BOOK_SOURCES", default=[]) if name] or ["google", "openlibrary", "apple"]
OPEN_LIBRARY_API_URL = env_value("OPEN_LIBRARY_API_URL", "https://openlibrary.org/search.json")
APPLE_BOOKS_API_URL = env_value("APPLE_BOOKS_API_URL", "https://itunes.apple.com/search")
APPLE_BOOKS_COUNTRY = "ua"
EXTERNAL_HTTP_USER_AGENT = env_value("EXTERNAL_HTTP_USER_AGENT", f"{SITE_NAME}/1.0 ({SITE_URL})")
EXTERNAL_FAILURE_COOLDOWN = 60
EXTERNAL_BOOK_CACHE_TTL = 60 * 60 * 24

VERIFICATION_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
VERIFICATION_ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"]

EMAIL_BACKEND = env_value("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env_value("DEFAULT_FROM_EMAIL", f"noreply@{SITE_DOMAIN.split(':')[0]}")
ADMIN_EMAIL = env("ADMIN_EMAIL", default="")
ADMINS = [("Admin", ADMIN_EMAIL)] if ADMIN_EMAIL else []
MANAGERS = ADMINS

PLAUSIBLE_DOMAIN = env("PLAUSIBLE_DOMAIN", default="")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "root": {"handlers": ["console"], "level": env_value("DJANGO_LOG_LEVEL", "INFO")},
}

SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN and not DEBUG:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=env_value("SENTRY_ENVIRONMENT", "production"),
    )
