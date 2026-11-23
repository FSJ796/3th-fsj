"""app01 应用配置。"""
from django.apps import AppConfig


# 应用配置类，Django 启动时据此注册 app01；verbose_name 为后台展示的中文名称
class App01Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app01'
    verbose_name = '企业员工管理'
