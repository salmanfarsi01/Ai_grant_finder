
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
# Email — Postmark transactional API (no IMAP mailbox, no Sent-folder copy)
# ---------------------------------------------------------------------------
# Postmark sends via HTTP API only.  There is no SMTP connection and no
# mailbox involved, so the system never retains a second copy of the email.
#
# To use:
#   1. Sign up at https://postmarkapp.com and create a Server.
#   2. Copy the Server API Token into .env as POSTMARK_API_KEY.
#   3. Set DEFAULT_FROM_EMAIL to a Sender Signature you have verified in
#      Postmark (e.g. kontakt@stipendieportalen.se).
#   4. In your Postmark dashboard → Servers → <your server> → Settings,
#      make sure "Store sent emails" is OFF (it is off by default).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'anymail.backends.postmark.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'kontakt@stipendieportalen.se')
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL  # kept so existing send_mail() calls still work

ANYMAIL = {
    'POSTMARK_SERVER_TOKEN': os.environ.get('POSTMARK_API_KEY', ''),
    # Send via the standard outbound transactional stream.
    # Change to a custom broadcast stream only if you need marketing emails.
    'POSTMARK_MESSAGE_STREAM': 'outbound',
    # Disable Anymail status tracking webhooks — not needed here.
    'IGNORE_RECIPIENT_STATUS': True,
}

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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'STEPO_BACKEND.urls'

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




