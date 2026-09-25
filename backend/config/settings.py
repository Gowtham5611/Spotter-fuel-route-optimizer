"""
Django settings for spotter-fuel-route-optimizer backend.

Environment variables are loaded from .env file.
All secrets and external configuration are read from the environment.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Base directory ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from backend directory
load_dotenv(BASE_DIR / ".env")

# ── Security ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-key-replace-in-production",
)
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ── Application ───────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local
    "apps.routing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "apps.routing.exceptions.custom_exception_handler",
}

# ── CORS ──────────────────────────────────────────────────────────────────────
_cors_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = False

# ── External APIs ─────────────────────────────────────────────────────────────
ROUTING_API_BASE_URL = os.environ.get(
    "ROUTING_API_BASE_URL", "http://router.project-osrm.org"
)
GEOCODING_API_BASE_URL = os.environ.get(
    "GEOCODING_API_BASE_URL", "https://nominatim.openstreetmap.org"
)
EXTERNAL_API_TIMEOUT: int = int(os.environ.get("EXTERNAL_API_TIMEOUT", "30"))

# ── Fuel / route constants ─────────────────────────────────────────────────────
# These are business constants exposed via settings so they remain configurable.
FUEL_ROUTE_CORRIDOR_MILES: float = float(
    os.environ.get("FUEL_ROUTE_CORRIDOR_MILES", "15")
)
MAX_RANGE_MILES: float = float(os.environ.get("MAX_RANGE_MILES", "500"))
FUEL_EFFICIENCY_MPG: float = float(os.environ.get("FUEL_EFFICIENCY_MPG", "10"))

# ── Data paths ─────────────────────────────────────────────────────────────────
DATA_DIR = BASE_DIR.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DATA_DIR = DATA_DIR / "cache"
OUTPUTS_DATA_DIR = DATA_DIR / "outputs"

FUEL_PRICES_CSV = RAW_DATA_DIR / "fuel-prices-for-be-assessment.csv"
PROCESSED_STATIONS_CSV = PROCESSED_DATA_DIR / "fuel_stations_with_coordinates.csv"

# ── Logging ───────────────────────────────────────────────────────────────────
LOGS_DIR = BASE_DIR.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "backend.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "services": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
