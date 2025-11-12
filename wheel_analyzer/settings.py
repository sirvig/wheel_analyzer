from pathlib import Path

import dj_database_url
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(str(BASE_DIR / ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG", default=False)

# Environment configuration (LOCAL, TESTING, PRODUCTION)
ENVIRONMENT = env("ENVIRONMENT", default="PRODUCTION")

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="*,").split(",")
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" if not host.startswith(("http://", "https://")) else host
    for host in ALLOWED_HOSTS
]

if "localhost" in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.append("http://localhost")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # external apps
    "django_extensions",
    "debug_toolbar",
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_filters",
    "django_htmx",
    "csp",
    # project apps
    "tracker",
    "scanner",
]

# htmx support for debug toolbar
DEBUG_TOOLBAR_CONFIG = {"ROOT_TAG_EXTRA_ATTRS": "hx-preserve"}

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "csp.middleware.CSPMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

ROOT_URLCONF = "wheel_analyzer.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "wheel_analyzer.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Cache TTL (time-to-live) constants
CACHE_TTL_ALPHAVANTAGE = 7 * 24 * 60 * 60  # 7 days in seconds (604,800)
CACHE_TTL_OPTIONS = 45 * 60  # 45 minutes in seconds (2,700)

# Django cache backend using Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "TIMEOUT": CACHE_TTL_OPTIONS,  # Default timeout for cache operations
        "KEY_PREFIX": "wheel_analyzer",  # Namespace all cache keys
        "VERSION": 1,  # Cache version for invalidation
    }
}

# Cache key prefixes for different data types
CACHE_KEY_PREFIX_ALPHAVANTAGE = "alphavantage"
CACHE_KEY_PREFIX_SCANNER = "scanner"


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "tracker.User"


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "US/Eastern"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

AUTH_USER_MODEL = "tracker.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "index"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{levelname} {asctime} {pathname} - line {lineno}: {message}",
            "style": "{",
        },
        "json": {
            "()": "wheel_analyzer.logs.JSONFormatter",  # Define the JSON formatter
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",  # Use the JSON formatter
        },
    },
    "loggers": {
        "django": {
            "level": "ERROR",
            "handlers": ["stdout"],
            "propagate": False,
        },
        "": {
            "level": "INFO",
            "handlers": ["stdout"],
            "propagate": False,
        },
    },
}

# =============================================================================
# CONTENT SECURITY POLICY (CSP) CONFIGURATION
# =============================================================================

# Django-CSP 4.0+ uses dictionary-based configuration
# See: https://django-csp.readthedocs.io/en/latest/migration-guide.html
from csp.constants import NONE, SELF

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [
            SELF,
            "https://cdn.jsdelivr.net",  # Chart.js, Flowbite
            "https://cdn.tailwindcss.com",  # Tailwind CDN
            "'unsafe-inline'",  # Temporarily allow inline scripts (HTMX, Chart.js init, Tailwind config)
        ],
        "style-src": [
            SELF,
            "https://cdn.jsdelivr.net",  # DaisyUI, Flowbite CSS
            "https://cdn.tailwindcss.com",  # Tailwind CDN styles
            "'unsafe-inline'",  # Allow inline styles (Tailwind)
        ],
        "img-src": [
            SELF,
            "data:",  # Allow data URIs for images
        ],
        "font-src": [SELF],
        "connect-src": [SELF],
        "frame-ancestors": [NONE],  # Prevent clickjacking
        "base-uri": [SELF],
        "form-action": [SELF],
    },
}

# CSP reporting (optional - enable in production)
# CONTENT_SECURITY_POLICY["REPORT_URI"] = "/csp-report/"
# To test without blocking, use CONTENT_SECURITY_POLICY_REPORT_ONLY instead

# =============================================================================
# SECURITY HEADERS CONFIGURATION (VULN-007)
# =============================================================================

# HTTP Strict Transport Security (HSTS)
# Forces browsers to use HTTPS for all future requests
# Disabled because we are using this in a docker container and HTTPS is terminated at the load balancer
# if ENVIRONMENT == "PRODUCTION":
#     SECURE_HSTS_SECONDS = 31536000  # 1 year
#     SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#     SECURE_HSTS_PRELOAD = True
#     SECURE_SSL_REDIRECT = True
#     SESSION_COOKIE_SECURE = True
#     CSRF_COOKIE_SECURE = True
# else:
    # Development/Testing - no HTTPS enforcement
SECURE_HSTS_SECONDS = 0
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Prevent MIME-sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-Frame-Options - already set via middleware, but explicit here
X_FRAME_OPTIONS = "DENY"

# Browser XSS filter
SECURE_BROWSER_XSS_FILTER = True

# Referrer Policy
SECURE_REFERRER_POLICY = "same-origin"
