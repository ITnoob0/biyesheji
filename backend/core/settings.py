from pathlib import Path
from datetime import timedelta # 新增
import os # 新增

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-7-$&th6v+-7)(izuuoct_#y55ty=+_$01yx#028+t6fv601veo'
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*'] # 开发阶段允许所有主机

# 1. 注册第三方库和我们的业务 App
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 第三方库
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',  
    
    # 本地业务模块
    'users',
    'achievements',
    'evaluation_rules',
    'project_guides',
    'graph_engine',
    'ai_assistant',
]

# 2. 配置中间件 (CorsMiddleware 必须在前面)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.RequestIdMiddleware',
    'core.middleware.ApiExceptionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
CORS_ALLOW_ALL_ORIGINS = True # 允许跨域

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# 3. 替换为 MySQL 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'biyesheji',
        'USER': 'root',          
        'PASSWORD': 'liujianlei',  
        'HOST': 'localhost',  # <--- 将 127.0.0.1 改为 localhost
        'PORT': '3306',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'zh-hans' # 改为中文
TIME_ZONE = 'Asia/Shanghai' # 改为中国时区
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 4. 指定自定义的用户模型
AUTH_USER_MODEL = 'users.CustomUser'

# 5. DRF 全局配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'EXCEPTION_HANDLER': 'core.api_errors.custom_exception_handler',
}

# 6. JWT 配置
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
 
# 7. Neo4j 图数据库配置示例
ENABLE_NEO4J = os.environ.get('ENABLE_NEO4J', '0') == '1'
GRAPH_SIGNAL_SYNC_ENABLED = os.environ.get('GRAPH_SIGNAL_SYNC_ENABLED', '0') == '1'
NEO4J_URI = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'liujianlei')

# 8. Dify 助手配置
DIFY_BASE_URL = os.environ.get('DIFY_BASE_URL', '').strip()
DIFY_API_KEY = os.environ.get('DIFY_API_KEY', '').strip()
DIFY_REQUEST_TIMEOUT = int(os.environ.get('DIFY_REQUEST_TIMEOUT', '30'))
