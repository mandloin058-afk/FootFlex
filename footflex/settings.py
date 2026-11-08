
"""FootFlex settings — Django + TiDB Cloud MySQL."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------- Security ----------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,.vercel.app"
    ).split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://*.vercel.app"
    ).split(",")
    if origin.strip()
]

# ---------- Applications ----------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store",
]

# ---------- Middleware ----------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "footflex.urls"

# ---------- Templates ----------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.shop",
            ],
        },
    },
]

WSGI_APPLICATION = "footflex.wsgi.application"

# ---------- Database: MySQL / TiDB Cloud ----------
import pymysql

pymysql.version_info = (2, 2, 7, "final", 0)
pymysql.install_as_MySQLdb()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "footflex"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "ssl": {},
        },
        "CONN_MAX_AGE": 0,
    }
}

# ---------- Authentication ----------
AUTH_USER_MODEL = "store.User"
AUTHENTICATION_BACKENDS = ["store.backends.EmailBackend"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]

# ---------- Language and Time ----------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = False
USE_TZ = True

# ---------- Static and Media ----------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------- Defaults ----------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------- Business Rules ----------
FREE_SHIP_ABOVE = 2999
SHIPPING_FEE = 99

# ---------- Vercel HTTPS ----------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
