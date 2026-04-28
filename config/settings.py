import os  # <-- TRÈS IMPORTANT : Ne pas oublier cet import pour ALLOWED_HOSTS
from pathlib import Path
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# En production, Render injecte cette variable. Si vide, on garde une clé par défaut.
SECRET_KEY = config('SECRET_KEY', default="django-insecure-9xk$random-string-change-me-123456")

DEBUG = config('DEBUG', default=True, cast=bool)

# Configuration des hôtes autorisés pour Render
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_host:
    ALLOWED_HOSTS.append(render_host)

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Recommandé pour tester les statiques en local
    'django.contrib.staticfiles',

    # Librairies
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_yasg',

    # Nos apps
    'users',
    'lots',
    'transferts',
    'blockchain',
    'verification',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Doit être juste après SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# BASE DE DONNÉES : Dynamique pour Render et Local
# On utilise la DATABASE_URL fournie par Render (ou Neon), sinon SQLite en local
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f"sqlite:///{BASE_DIR}/db.sqlite3"),
        conn_max_age=600
    )
}

# Cloudinary
import cloudinary
cloudinary.config(
    cloud_name=config("CLOUDINARY_CLOUD_NAME"),
    api_key=config("CLOUDINARY_API_KEY"),
    api_secret=config("CLOUDINARY_API_SECRET"),
    secure=True
)

# Modèle User personnalisé
AUTH_USER_MODEL = 'users.User'

# DRF + JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Configuration Blockchain
BLOCKCHAIN_RPC_URL = config('BLOCKCHAIN_RPC_URL')
PRIVATE_KEY = config('PRIVATE_KEY')
WALLET_ADDRESS = config('WALLET_ADDRESS')
CONTRACT_ADDRESS = config('CONTRACT_ADDRESS')
CHAIN_ID = config('CHAIN_ID', cast=int)

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# Internationalisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# Fichiers statiques (CRITIQUE pour Render)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

