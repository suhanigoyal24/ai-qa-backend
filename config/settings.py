import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# Core Django settings
SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-in-production",
)

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    host.strip()
    for host in config("ALLOWED_HOSTS", default="*").split(",")
    if host.strip()
]


# Applications
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",
    "api",
]


# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# SQLite is used as a safe fallback during Docker build when Space secrets
# are not yet available. At runtime, Hugging Face supplies DATABASE_URL.
DATABASE_URL = config(
    "DATABASE_URL",
    default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
)

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
    )
}

# Add the TiDB CA certificate only when using a MySQL-compatible database.
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {
        "ssl": {
            "ca": "/app/certs/ca-cert.pem",
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# Uploaded media
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:3000",
    ).split(",")
    if origin.strip()
]

CORS_ALLOW_ALL_ORIGINS = False


# External services
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GOOGLE_API_KEY = config("GOOGLE_API_KEY", default=GEMINI_API_KEY)
OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default="")


# FAISS storage
FAISS_INDEX_PATH = BASE_DIR / "faiss_indexes"


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}


# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}