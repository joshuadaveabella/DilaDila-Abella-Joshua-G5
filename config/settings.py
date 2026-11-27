"""
Django settings for Dila-Dila.

Secrets (SECRET_KEY, DATABASE_URL) are read from a .env file that is NOT
committed to GitHub. See .env.example for the variables you need.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# DEBUG is controlled from .env and is OFF unless .env says DEBUG=True.
DEBUG = os.environ.get("DEBUG", "False") == "True"

# The secret key must come from .env; there is no built-in fallback key.
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY or SECRET_KEY.startswith("change-me"):
    raise ImproperlyConfigured("SECRET_KEY is not set. Put a long random value in your .env file.")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Security headers and cookies
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
# Set SECURE_COOKIES=True in .env when the site is served over HTTPS
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "False") == "True"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_FAILURE_VIEW = "accounts.views.csrf_failure"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "library",
    "phrasebook",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"



USE_LOCAL_TEST_DB = os.environ.get("USE_LOCAL_TEST_DB", "False") == "True"

if USE_LOCAL_TEST_DB:
    DATABASE_URL = os.environ.get("LOCAL_TEST_DATABASE_URL", "").strip().strip("\"'")
else:
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip().strip("\"'")

if not DATABASE_URL:
    raise ImproperlyConfigured(
        "Database URL is not set. Check your .env configuration."
    )

if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured(
        "DATABASE_URL must start with postgresql://"
    )

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=False if USE_LOCAL_TEST_DB else (
            os.environ.get("DB_SSL_REQUIRE", "False") == "True"
        ),
    )
}



AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Email (password reset). By default the email is printed in the terminal; set EMAIL_BACKEND and the
# EMAIL_* variables in .env to send real email.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Dila-Dila <noreply@dila-dila.local>")
PASSWORD_RESET_TIMEOUT = 60 * 60  # reset links last 1 hour

# Uploaded files (phrase audio, profile photos)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Reject oversized request bodies early (audio limit is 5 MB; leave room for the form fields)
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
