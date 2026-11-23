"""分页工具。"""
from django.core.paginator import Paginator


# 入参：request（读取 page 查询参数）、queryset、per_page（每页条数，默认 10）；
# 返回 Page 对象；页码非法（非数字/越界）时 get_page 自动回落到第一页或最后一页，不抛异常。
def paginate(request, queryset, per_page=10):
    """按 page 查询参数分页，非法页码回落到有效页。"""
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))
