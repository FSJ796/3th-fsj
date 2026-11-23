"""项目总路由。"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django 自带后台管理入口
    path('admin/', admin.site.urls),
    # 业务路由全部交由 app01 处理，根路径 '' 即从其 urlpatterns 开始匹配
    path('', include('app01.urls')),
]

# 仅在 DEBUG 模式下由 Django 直接提供媒体文件（头像等），生产环境应交给 Nginx
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
