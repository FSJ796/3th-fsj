"""首页看板。"""
from datetime import date

from django.db.models import Sum
from django.shortcuts import render

from app01.models import Department, Notice
from app01.utils.scope import (
    is_dept_admin, scope_attendance, scope_employees, scope_salary,
)


# 请求方式：GET
# 权限要求：需登录（未登录由全局中间件跳转登录页）
# 核心流程：按数据范围统计员工数、部门数、本月薪资总额、今日出勤人数，并取最新公告
# 返回内容：渲染首页看板 index.html
def index(request):
    """首页：按当前用户的数据范围展示关键指标与最新公告。"""
    today = date.today()
    month = today.strftime('%Y-%m')
    # 员工、薪资、考勤均使用数据范围工具过滤：超管全部、部门管理员本部门、员工本人
    employees = scope_employees(request.user)

    # 部门数量按角色范围统计：超管为全部部门，部门管理员固定为 1，普通员工为 0
    if request.user.is_superuser:
        department_count = Department.objects.count()
    elif is_dept_admin(request.user) and request.user.depart_id:
        department_count = 1
    else:
        department_count = 0

    # 本月实发工资总额，仅统计当前用户权限范围内的薪资记录
    salary_total = (
        scope_salary(request.user).filter(month=month)
        .aggregate(total=Sum('total'))['total'] or 0
    )
    # 今日出勤人数：排除“缺勤”状态后的记录数
    attendance_today = (
        scope_attendance(request.user).filter(date=today)
        .exclude(status='缺勤').count()
    )

    context = {
        'employee_count': employees.count(),
        'department_count': department_count,
        'salary_total': salary_total,
        'attendance_today': attendance_today,
        'current_month': month,
        'recent_notices': Notice.objects.all()[:5],
        'is_employee_role': not request.user.is_superuser and not is_dept_admin(request.user),
    }
    return render(request, 'index.html', context)
