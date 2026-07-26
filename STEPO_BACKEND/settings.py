
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
print("\n\nDEBUG REPORT DIR: ", BASE_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "ngrok-skip-browser-warning"
)

CSRF_TRUSTED_ORIGINS = [
    'https://b160-103-186-20-8.ngrok-free.app',
    'https://*.ngrok-free.app',
]
# ---------------------------------------------------------------------------
# Email configuration (Postmark). For local development the code will
# fall back to Django's console email backend so OTP testing works without
# requiring a verified Postmark sender signature or outbound approval.
# ---------------------------------------------------------------------------
def _get_email_backend_config(debug=False):
    postmark_token = (
        os.environ.get('POSTMARK_API_KEY')
        or os.environ.get('POSTMARK_SERVER_TOKEN')
        or os.environ.get('POSTMARK_TOKEN', '')
        or ''
    ).strip()

    use_console_email = (
        os.environ.get('USE_CONSOLE_EMAIL', '').strip().lower() in {'1', 'true', 'yes', 'on'}
        or bool(debug)
    )

    if postmark_token and not use_console_email:
        return (
            'anymail.backends.postmark.EmailBackend',
            {
                'POSTMARK_SERVER_TOKEN': postmark_token,
                'POSTMARK_MESSAGE_STREAM': 'outbound',
                'IGNORE_RECIPIENT_STATUS': True,
            },
        )

    return 'django.core.mail.backends.console.EmailBackend', {}


POSTMARK_TOKEN = (
    os.environ.get('POSTMARK_API_KEY')
    or os.environ.get('POSTMARK_SERVER_TOKEN')
    or os.environ.get('POSTMARK_TOKEN', '')
    or ''
).strip()
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'salmanf4545@gmail.com')
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL  # kept so existing send_mail() calls still work
EMAIL_BACKEND, ANYMAIL = _get_email_backend_config(DEBUG)

if EMAIL_BACKEND.endswith('console.EmailBackend'):
    print("WARNING: using console email backend for local development.")

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'anymail',
    'corsheaders',
    'django_cleanup.apps.CleanupConfig',
    'app',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# When frontend sends cookies/credentials, allow credentialed CORS responses
CORS_ALLOW_CREDENTIALS = True
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

ROOT_URLCONF = 'STEPO_BACKEND.urls'

WSGI_APPLICATION = 'STEPO_BACKEND.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

# Development fallback: use SQLite when no DB_NAME is provided.
# This makes it easier to run the app locally without configuring Postgres.
if not DATABASES['default'].get('NAME'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

REST_FRAMEWORK = {
    # YOUR SETTINGS
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'GrantFinder AI',
    'DESCRIPTION': 'Your project description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATASET_PATH = BASE_DIR/'scholarships.xlsx'
REPORT_DIR = 'reports'

MEDIA_URL = 'media/'
MEDIA_ROOT = 'reports'
WATERMARK_PATH = (BASE_DIR/'watermark.png').__str__()

# Check if the directory exists
if not os.path.exists(REPORT_DIR):
    # Create the directory
    os.makedirs(REPORT_DIR)
    print(f"Directory '{REPORT_DIR}' created.")
else:
    print(f"Directory '{REPORT_DIR}' already exists.")




