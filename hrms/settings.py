"""Django 项目配置：企业员工管理系统（HRMS）。"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

# 项目根目录，数据库、媒体文件等路径均基于该目录拼接
BASE_DIR = Path(__file__).resolve().parent.parent

# 加密密钥优先从环境变量读取，缺省值为课程设计专用占位值
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-hrms-course-design-2026-9f3a1c7b5e8d2f4a6c0b',
)

# 课程设计阶段默认开启 DEBUG，部署时通过环境变量关闭。
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# 允许访问的域名列表，默认仅本机，可用逗号分隔配置多个
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost'
).split(',')

# 注册应用：Django 内置的认证、会话、消息等组件，加上业务应用 app01
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app01',
]

# 中间件按请求顺序依次执行：
# 安全->会话->通用->CSRF->认证->消息->点击劫持防护，最后是自定义登录拦截
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 自定义登录拦截中间件，必须放在 AuthenticationMiddleware 之后
    'app01.middleware.auth.AuthMiddleware',
]

ROOT_URLCONF = 'hrms.urls'

# 模板引擎：开启 APP_DIRS 后自动在各应用的 templates 目录下查找模板
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        # 上下文处理器：向所有模板注入 request、当前用户与 messages
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hrms.wsgi.application'

# ---------------------------------------------------------------------------
# 数据库：默认 MySQL 8.x；设置 DB_ENGINE=sqlite 可切换为本地 SQLite 便于调试。
# 连接参数全部支持环境变量覆盖，便于在不同机器上运行。
# ---------------------------------------------------------------------------
if os.environ.get('DB_ENGINE') == 'sqlite':
    # SQLite 分支：数据库文件直接生成在项目根目录
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # MySQL 分支：utf8mb4 支持中文与 emoji，STRICT_TRANS_TABLES 开启严格模式
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'hrms'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'Root@123456'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

# 自定义用户模型，替代 Django 默认 User；必须在首次迁移前指定且不可随意更改
AUTH_USER_MODEL = 'app01.User'

# 密码强度校验：与用户信息过于相似、长度不足、常见密码、纯数字密码都会被拒绝
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 国际化：简体中文界面 + 中国标准时间；USE_TZ=False 让数据库按本地时间存储，避免模板显示偏移
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = False

# 静态资源（CSS/JS/图片）的访问前缀；媒体文件（如上传的头像）的访问前缀与存储目录
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 未登录用户访问受保护页面时跳转的登录地址
LOGIN_URL = '/login/'

# 模型主键默认使用大整数自增，避免数据量增长后主键溢出
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 将 messages 的级别映射为 Bootstrap 3 的提示样式
MESSAGE_TAGS = {
    message_constants.DEBUG: 'alert-info',
    message_constants.INFO: 'alert-info',
    message_constants.SUCCESS: 'alert-success',
    message_constants.WARNING: 'alert-warning',
    message_constants.ERROR: 'alert-danger',
}

# 大模型配置（T1）：一律从环境变量读取，禁止把 API Key 硬编码进代码或提交 Git。
# 方式 A（PowerShell 当前窗口临时设置，重启终端失效）：
#   $env:AI_API_KEY  = "你的_Key"
#   $env:AI_BASE_URL = "https://api.siliconflow.cn/v1"
#   $env:AI_MODEL    = "Qwen/Qwen2.5-7B-Instruct"
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.siliconflow.cn/v1')
AI_MODEL = os.environ.get('AI_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
