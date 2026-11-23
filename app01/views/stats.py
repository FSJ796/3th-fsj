"""数据统计可视化视图（T10）：ORM 聚合 + JSON 接口供 ECharts 渲染。"""
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render

from app01.middleware.permission import perm_required
from app01.models import Department
from app01.utils.scope import is_dept_admin, scope_salary, scope_employees


# 请求方式：GET
# 权限要求：需拥有 stats_view 权限
# 核心流程：仅渲染统计页面，图表数据由下方两个 JSON 接口异步获取
# 返回内容：统计页面 stats/index.html
@perm_required('stats_view')
def stats_index(request):
    """统计页面。"""
    return render(request, 'stats/index.html')


# 请求方式：GET
# 权限要求：需拥有 stats_view 权限
# 核心流程：按角色收敛部门范围后，用 Count 聚合各部门员工数
# 返回内容：JSON，names 为部门名称、values 为对应人数，供 ECharts 渲染
@perm_required('stats_view')
def department_chart_data(request):
    """部门人数分布：按部门聚合员工数量。"""
    queryset = Department.objects.all()
    # 非超管仅能看到本部门；普通员工无部门管理视角，返回空集
    if not request.user.is_superuser:
        if is_dept_admin(request.user) and request.user.depart_id:
            queryset = queryset.filter(pk=request.user.depart_id)
        else:
            queryset = queryset.none()
    rows = queryset.annotate(value=Count('employees')).values('name', 'value').order_by('id')
    # 将查询结果拆成两个平行数组，便于前端直接塞进 ECharts 的 xAxis 与 series
    return JsonResponse({
        'names': [row['name'] for row in rows],
        'values': [row['value'] for row in rows],
    })


# 请求方式：GET
# 权限要求：需拥有 stats_view 权限
# 核心流程：在权限范围内按月份聚合实发工资总额，并统计员工人数
# 返回内容：JSON，months 为月份、totals 为实发合计、employee_count 为人数
@perm_required('stats_view')
def salary_trend_data(request):
    """各月薪资趋势：按月份聚合实发工资总额。"""
    rows = (
        # scope_salary 已按数据范围过滤，聚合结果不会泄露其他部门薪资
        scope_salary(request.user).values('month')
        .annotate(total=Sum('total'))
        .order_by('month')
    )
    return JsonResponse({
        # Decimal 需转为 float 才能被 JSON 序列化
        'months': [row['month'] for row in rows],
        'totals': [float(row['total'] or 0) for row in rows],
        'employee_count': scope_employees(request.user).count(),
    })
