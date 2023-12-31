from datetime import timedelta
from pathlib import Path
import json, os
from django.core.exceptions import ImproperlyConfigured

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

BASE_DIR = Path(__file__).resolve().parent.parent

secret_file = BASE_DIR / 'secrets.json'  

with open(secret_file) as file:
    secrets = json.loads(file.read())

def get_secret(setting,secrets_dict = secrets):
    try:
        return secrets_dict[setting]
    except KeyError:
        error_msg = f'Set the {setting} environment variable'
        raise ImproperlyConfigured(error_msg)

SECRET_KEY = get_secret('SECRET_KEY')
KAKAO_REST_API_KEY = get_secret('KAKAO_REST_API_KEY')


AUTH_USER_MODEL = 'accounts.User'
DEBUG = True

SOCIALACCOUNT_LOGIN_ON_GET = True # 중간 창 없이 카카오 로그인 페이지로 넘어가게 하는 설정

ACCOUNT_LOGOUT_ON_GET = True  # 로그아웃 요청시 즉시 로그아웃 하는 설정

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # my app
    'accounts',
    'transaction',
    'foreignstocks',
    'koreanstocks',
    'news',

    # third party app
    'corsheaders',
    'drf_yasg',

    # django rest framework
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'dj_rest_auth',
    'dj_rest_auth.registration',
]

REST_AUTH = {
    'USE_JWT': True,
}

SITE_ID = 1

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

ROOT_URLCONF = 'config.urls'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/image/'

MEDIA_ROOT = os.path.join(BASE_DIR,'image')

CORS_ALLOWED_ORIGINS = [
    'https://inhastalk.pages.dev',
    'http://localhost:3000',
    'http://127.0.0.1:8000',
    'https://stalksound.store',
]

CORS_ALLOW_METHODS  =  [ 
    'DELETE' , 
    'GET' , 
    'OPTIONS' , 
    'PATCH' , 
    'POST' , 
    'PUT' , 
]

CORS_ALLOW_HEADERS  =  [ 
    'accept' , 
    'accept-encoding' , 
    'authorization' , 
    'content-type' , 
    'dnt' , 
    'origin' , 
    'user-agent' , 
    'x-csrftoken' , 
    'x-requested-with' , 
]

CORS_ALLOW_CREDENTIALS = True # True여야 쿠키가 cross-site HTTP 요청에 포함될 수 있다

CSRF_COOKIE_SECURE = True # True일 시 프론트가 https로 요청을 보내야함

SESSION_COOKIE_SECURE = True # True일 시 프론트가 https로 요청을 보내야함

CSRF_COOKIE_SAMESITE = 'None'

SESSION_COOKIE_SAMESITE = 'None'

CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_HTTPONLY = True

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'scheme' : 'https',
    },
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

ACCOUNT_EMAIL_VERIFICATION = "none" # 이메일 확인을 끔
ACCOUNT_EMAIL_REQUIRED = False # email 필드 사용 o
ACCOUNT_USERNAME_REQUIRED = True # username 필드 사용 o
ACCOUNT_AUTHENTICATION_METHOD = 'username' 

REST_USE_JWT = True

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN':True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    "TOKEN_OBTAIN_SERIALIZER": "config.serializers.MyTokenObtainPairSerializer",

    'USER_ID_FIELD': 'username',
    'USER_ID_CLAIM': 'username',

    'TOKEN_USER_CLASS': 'accounts.User',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),

}



