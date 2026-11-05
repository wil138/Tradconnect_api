"""
Django settings for TradConnectpi project.
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
from .connection_settings import load_database_connections, load_local_connections
LOCAL_CONNECTIONS = load_local_connections(BASE_DIR)
DATABASE_CONNECTIONS = load_database_connections(os.environ, LOCAL_CONNECTIONS)

from .local_secret import secret_key
SECRET_KEY = secret_key(BASE_DIR)
DEBUG = True
ALLOWED_HOSTS = ['*']

# =========================================================
# APLICACIONES INSTALADAS
# =========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'drf_yasg',
    'corsheaders',

    # Local
    'TradConnect',          # tu app principal (con modelos de negocio)
    'Tradconnect_no_sql',
]

# =========================================================
# MIDDLEWARE
# =========================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'config.urls'   # tu archivo principal de rutas

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

# =========================================================
# BASE DE DATOS – SQL Server (default) + Data Warehouse
# =========================================================
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': DATABASE_CONNECTIONS['sql']['NAME'],
        'HOST': DATABASE_CONNECTIONS['sql']['HOST'],
        'PORT': DATABASE_CONNECTIONS['sql']['PORT'],
        # Sin USER, mssql-django usa la cuenta Windows del proceso.
        'USER': DATABASE_CONNECTIONS['sql']['USER'],
        'PASSWORD': DATABASE_CONNECTIONS['sql']['PASSWORD'],
        'OPTIONS': {
            'driver': DATABASE_CONNECTIONS['sql']['DRIVER'],
            'extra_params': DATABASE_CONNECTIONS['sql']['EXTRA_PARAMS'],
        },
    },

}

# =========================================================
# ROUTER PARA DIRIGIR MODELOS DEL DW A LA BD 'trad_dw'
# =========================================================
DATABASE_ROUTERS = []

# =========================================================
# MONGODB (PyMongo; separado de las bases SQL de Django)
# =========================================================
MONGODB_URI = DATABASE_CONNECTIONS['mongodb_uri']
MONGODB_DATABASE = DATABASE_CONNECTIONS['mongodb_database']
MARKETPLACE_CURRENCY_ID = int(os.environ.get('MARKETPLACE_CURRENCY_ID', '1'))

# =========================================================
# VALIDACIÓN DE CONTRASEÑAS
# =========================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-ni'
TIME_ZONE = 'America/Managua'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================================================
# DJANGO REST FRAMEWORK
# =========================================================
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'TradConnect.errors.api_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'TradConnect.authentication.UsuarioJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'TradConnect.authentication.IsUsuarioAutenticado',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
}

CORS_ALLOW_ALL_ORIGINS = True
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'config.schema.HybridAutoSchema',
    'DOC_EXPANSION': 'list',
    'SECURITY_DEFINITIONS': {
        'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'},
    },
}
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = ['accept', 'accept-encoding', 'authorization', 'content-type',
                      'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with']
