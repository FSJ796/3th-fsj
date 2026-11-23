"""认证相关视图：登录、注销、图片验证码。"""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from app01.forms import LoginForm
from app01.utils.captcha import create_captcha_image, generate_code


# 请求方式：GET 展示登录页，POST 提交登录表单
# 权限要求：无需登录；已登录用户直接重定向到首页
# 核心流程：比对 session 中的图片验证码 → authenticate 认证 → 登录并处理 next 跳转
# 返回内容：登录页模板，或成功后重定向到首页/安全的 next 地址
def login_view(request):
    """登录：校验用户名、密码与图片验证码，成功后维持会话。"""
    if request.user.is_authenticated:
        return redirect('index')

    next_url = request.GET.get('next') or request.POST.get('next') or ''
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # 验证码一次性使用：取出后立即从 session 移除，防止同一验证码重复提交
        session_code = request.session.pop('captcha_code', '')
        input_code = form.cleaned_data['captcha'].upper()
        if not session_code or input_code != session_code.upper():
            form.add_error('captcha', '验证码错误或已失效，请重新输入')
        else:
            # 验证码通过后才交由 Django 认证后端校验用户名与密码
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None and user.is_active:
                login(request, user)
                messages.success(request, f'欢迎回来，{user.username}！')
                # 仅允许跳转到本站同源地址，避免开放重定向漏洞
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)
                return redirect('index')
            form.add_error(None, '用户名或密码错误')

    return render(request, 'login.html', {'form': form, 'next': next_url})


# 请求方式：GET/POST 均可
# 权限要求：已登录用户
# 核心流程：调用 logout 清除会话数据，并写入退出成功提示
# 返回内容：重定向到登录页
def logout_view(request):
    """退出登录并回到登录页。"""
    logout(request)
    messages.info(request, '您已安全退出登录')
    return redirect('login')


# 请求方式：GET
# 权限要求：无需登录（登录页需要先加载验证码图片）
# 核心流程：生成验证码文本写入 session → 绘制并返回 PNG 图片
# 返回内容：image/png 图片流，并设置禁止缓存的响应头
def captcha_view(request):
    """生成图片验证码，验证码文本保存在 session 中。"""
    code = generate_code()
    request.session['captcha_code'] = code
    image_bytes = create_captcha_image(code)
    response = HttpResponse(image_bytes, content_type='image/png')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response
