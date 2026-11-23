"""模板标签：RBAC 权限判断与分页查询串处理。"""
from django import template

register = template.Library()


# 模板过滤器：入参为 user 与权限编码，返回布尔值；未登录或超级管理员情形由 User.has_code 统一处理，
# 用于在前端按权限显示/隐藏按钮，仅作展示层控制，后端仍需 perm_required 兜底。
@register.filter
def has_perm(user, code):
    """判断用户是否拥有权限编码，用于前端按权限隐藏按钮。"""
    return bool(user and user.is_authenticated and user.has_code(code))


# 模板标签：入参为模板上下文与若干查询参数，返回新的查询串；
# 在当前请求的 GET 参数基础上覆盖同名参数，用于分页时保留搜索、筛选等条件。
@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """在当前查询参数基础上替换指定参数，用于分页跳转。"""
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
