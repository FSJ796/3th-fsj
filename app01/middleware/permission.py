"""接口级权限校验装饰器（RBAC 第二层）。"""
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render


# 入参为权限编码，返回视图装饰器；装饰器先校验登录，再校验 RBAC 权限，
# 未登录跳登录页，无权限时 AJAX 返回 403 JSON、普通请求渲染 403 页面。
def perm_required(code):
    """要求登录且拥有指定权限编码，否则跳转登录或返回 403。"""

    # 包装原视图：登录与权限任一不满足即中断，全部通过后原样调用视图函数
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{settings.LOGIN_URL}?next={quote(request.path_info)}')
            if not request.user.has_code(code):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': '无权限执行该操作'}, status=403)
                return render(request, '403.html', {'required_code': code}, status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
