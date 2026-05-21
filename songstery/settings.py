import os
from pathlib import Path
import environ

env = environ.Env(
    DEBUG=(bool, False)
)

SITE_NAME = 'Songstory'

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'songstery.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site',
            ],
        },
    },
]

WSGI_APPLICATION = 'songstery.wsgi.application'

# ---------------------------------------------------------------------------
# Database
# Defaults to SQLite for local dev. Set DATABASE_URL in .env for MySQL/Postgres.
#
# MySQL example:
#   DATABASE_URL=mysql://user:password@localhost:3306/songstory
#
# Requires mysqlclient:
#   pip install mysqlclient==2.2.4
# ---------------------------------------------------------------------------
_db_default = f'sqlite:///{BASE_DIR / "db.sqlite3"}'
DATABASES = {
    'default': env.db('DATABASE_URL', default=_db_default)
}

# MySQL-specific options injected when the engine is MySQL
if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['charset'] = 'utf8mb4'
    DATABASES['default']['OPTIONS']['init_command'] = (
        "SET sql_mode='STRICT_TRANS_TABLES'"
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'
LOGIN_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
