from pathlib import Path

from the_scenario_engine.helpers import get_env


BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = get_env('SECRET_KEY')
DEBUG = get_env('DEBUG', cast=bool)

ALLOWED_HOSTS = [
    '.localhost',
    '127.0.0.1',
    '[::1]',
]

AUTH_USER_MODEL = 'core.User'

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
LOCAL_APPS = [
    'core',
    'frontend',
    'oauth',
]
THIRD_PARTY_APPS = [
    'rest_framework',
]
INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

DJANGO_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
LOCAL_MIDDLEWARE = []
THIRD_PARTY_MIDDLEWARE = []
MIDDLEWARE = DJANGO_MIDDLEWARE + LOCAL_MIDDLEWARE + THIRD_PARTY_MIDDLEWARE

ROOT_URLCONF = 'the_scenario_engine.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'the_scenario_engine.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'

# Rest framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

APPEND_SLASH = False

# env
GOOGLE_OAUTH_CLIENT_ID = get_env('GOOGLE_OAUTH_CLIENT_ID', required=True)
GOOGLE_OAUTH_CLIENT_SECRET = get_env('GOOGLE_OAUTH_CLIENT_SECRET', required=True)
GOOGLE_OAUTH_REDIRECT_URI = get_env('GOOGLE_OAUTH_REDIRECT_URI', required=True)
