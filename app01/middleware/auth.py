"""登录拦截中间件：未登录访问受保护页面时跳转登录页。"""
from urllib.parse import quote

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect


# 登录拦截中间件（第一层）：未登录访问受保护页面时，页面请求重定向到登录页，AJAX 请求返回 401 JSON。
class AuthMiddleware:
    """统一处理未登录访问，AJAX 请求返回 JSON。"""

    # 白名单前缀：登录/登出/验证码、静态与媒体资源、admin 后台无需登录校验
    EXEMPT_PREFIXES = (
        '/login/', '/logout/', '/captcha/',
        '/static/', '/media/', '/admin/',
    )

    # Django 中间件初始化入口，get_response 为后续视图/中间件调用链
    def __init__(self, get_response):
        self.get_response = get_response

    # 请求入口：已登录或命中白名单直接放行；否则 AJAX 返回 401，普通请求带上 next 参数跳转登录页
    def __call__(self, request):
        if request.user.is_authenticated or self._is_exempt(request.path_info):
            return self.get_response(request)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': '登录已失效，请重新登录'}, status=401)
        # next 做 URL 编码，登录成功后可安全跳回原页面
        return redirect(f'{settings.LOGIN_URL}?next={quote(request.path_info)}')

    # 判断路径是否属于免登录白名单，入参为请求路径，返回布尔值
    def _is_exempt(self, path):
        return any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES)
