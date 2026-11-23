"""薪资管理视图（T7）。"""
import re

from django.contrib import messages
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app01.forms import SalaryForm
from app01.middleware.permission import perm_required
from app01.models import Salary
from app01.utils.pagination import paginate
from app01.utils.scope import scope_employees, scope_salary

MONTH_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


# 辅助函数：在当前用户数据范围内取薪资记录，越权访问返回 404
def _get_scoped_salary(user, pk):
    record = scope_salary(user).select_related('employee').filter(pk=pk).first()
    if record is None:
        raise Http404('薪资记录不存在或无权访问')
    return record


# 请求方式：GET
# 权限要求：需拥有 salary_view 权限
# 核心流程：在权限范围内按月份、员工筛选，统计实发合计后再分页
# 返回内容：薪资列表模板，含分页对象、筛选条件、合计金额与员工下拉选项
@perm_required('salary_view')
def salary_list(request):
    """薪资列表：按月份/员工筛选，并统计筛选结果的实发总额。"""
    # select_related 预取员工及部门，减少列表渲染时的数据库查询次数
    queryset = scope_salary(request.user).select_related('employee', 'employee__depart')
    month = request.GET.get('month', '').strip()
    employee_id = request.GET.get('employee', '').strip()
    # 月份必须符合 YYYY-MM 格式才参与过滤
    if MONTH_RE.match(month):
        queryset = queryset.filter(month=month)
    # 只有数字型的员工 ID 才参与过滤，避免非法参数
    if employee_id.isdigit():
        queryset = queryset.filter(employee_id=int(employee_id))

    # 合计在分页之前对完整筛选结果聚合，避免只统计当前页
    total = queryset.aggregate(sum_total=Sum('total'))['sum_total'] or 0
    page = paginate(request, queryset, 10)
    context = {
        'page': page,
        'month': month,
        'employee_id': employee_id,
        'employees': scope_employees(request.user),
        'total': total,
        'filtered_count': queryset.count(),
    }
    return render(request, 'salary/list.html', context)


# 请求方式：GET 渲染表单，POST 提交新增
# 权限要求：需拥有 salary_add 权限
# 核心流程：SalaryForm 校验（月份格式、金额非负、同月唯一）→ 计算实发工资 → 保存
# 返回内容：录入薪资表单页或保存后重定向到列表页
@perm_required('salary_add')
def salary_add(request):
    """新增薪资；使用 commit=False 计算实发工资后再保存。"""
    form = SalaryForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        # 实发 = 基本工资 + 奖金 - 扣款，由模型方法统一计算后落库
        record.total = record.calc_total()
        record.save()
        messages.success(request, f'薪资已录入，实发工资 ￥{record.total}')
        return redirect('salary_list')
    return render(request, 'salary/form.html', {'form': form, 'title': '录入薪资'})


# 请求方式：GET 渲染表单，POST 提交修改
# 权限要求：需拥有 salary_edit 权限
# 核心流程：按数据范围取出记录 → 表单校验 → 重新计算实发工资 → 保存
# 返回内容：编辑薪资表单页或保存后重定向到列表页
@perm_required('salary_edit')
def salary_edit(request, pk):
    """编辑薪资，重新计算实发工资。"""
    record = _get_scoped_salary(request.user, pk)
    form = SalaryForm(request.POST or None, instance=record, user=request.user)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        # 基本工资、奖金或扣款任一变动后都需重算实发金额
        record.total = record.calc_total()
        record.save()
        messages.success(request, f'薪资已更新，实发工资 ￥{record.total}')
        return redirect('salary_list')
    return render(request, 'salary/form.html', {
        'form': form, 'title': f'编辑薪资 - {record.employee.name}', 'record': record,
    })


# 请求方式：POST（require_POST 限制）
# 权限要求：需拥有 salary_delete 权限
# 核心流程：按数据范围取出薪资记录并删除
# 返回内容：重定向到薪资列表页
@perm_required('salary_delete')
@require_POST
def salary_delete(request, pk):
    """删除薪资记录。"""
    record = _get_scoped_salary(request.user, pk)
    record.delete()
    messages.success(request, '薪资记录已删除')
    return redirect('salary_list')
