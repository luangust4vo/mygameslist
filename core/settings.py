import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY", "django-insecure-%e*+uq4)2hpo_1&t*#7_++0g3+6gn8zxq8ilz^*q&uftb_@y!y"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "mygameslist-497823.rj.r.appspot.com").split(
        ","
    )
    if host.strip()
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # My Apps
    "games",
    # External Apps
    "crispy_forms",
    "crispy_bootstrap5",
]

# Crispy Forms Settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# My Urls
LOGIN_REDIRECT_URL = "games:home"
LOGOUT_REDIRECT_URL = "games:home"
LOGIN_URL = "games:login"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "games" / "templates" / "games"],
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

WSGI_APPLICATION = "core.wsgi.application"


def _load_secret_from_manager(secret_id):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv(
        "GOOGLE_CLOUD_PROJECT_ID"
    )
    if not project_id:
        return None

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def get_config_value(name, default=None, required_in_cloud=False):
    value = os.getenv(name)
    if value not in (None, ""):
        return value

    secret_value = _load_secret_from_manager(name)
    if secret_value not in (None, ""):
        return secret_value

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv(
        "GOOGLE_CLOUD_PROJECT_ID"
    )
    if required_in_cloud and project_id:
        raise ImproperlyConfigured(
            f"Missing {name} in the environment or Secret Manager."
        )

    return default


# External API Settings
API_KEY = get_config_value("API_KEY", required_in_cloud=True)

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
database_url = get_config_value("DATABASE_URL", required_in_cloud=True)

if database_url:
    tmpPostgres = urlparse(database_url)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": tmpPostgres.path.replace("/", ""),
            "USER": tmpPostgres.username,
            "PASSWORD": tmpPostgres.password,
            "HOST": tmpPostgres.hostname,
            "PORT": 5432,
            "OPTIONS": dict(parse_qsl(tmpPostgres.query)),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static_gcloud"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
