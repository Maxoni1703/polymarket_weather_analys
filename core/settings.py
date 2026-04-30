import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback-do-not-use-in-prod')
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = []

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
