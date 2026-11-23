"""员工管理视图（T3）：CRUD、搜索、部门筛选、分页、头像上传。"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app01.forms import EmployeeForm
from app01.middleware.permission import perm_required
from app01.models import Department, Employee
from app01.utils.pagination import paginate
from app01.utils.scope import scope_employees


# 辅助函数：返回筛选下拉框可用的部门集合，按角色限定范围
def _visible_departments(user):
    """当前用户可选的部门列表，用于筛选下拉框。"""
    if user.is_superuser:
        return Department.objects.all()
    if user.depart_id:
        return Department.objects.filter(pk=user.depart_id)
    return Department.objects.none()


# 辅助函数：在当前用户数据范围内取员工，越权时统一抛出 404 隐藏资源存在性
def _get_scoped_employee(user, pk):
    """按数据范围获取员工，越权访问返回 404。"""
    employee = scope_employees(user).filter(pk=pk).first()
    if employee is None:
        raise Http404('员工不存在或无权访问')
    return employee


# 请求方式：GET
# 权限要求：需拥有 employee_view 权限
# 核心流程：在权限范围内按姓名模糊搜索、按部门筛选，最后分页
# 返回内容：员工列表模板，含分页对象、筛选条件与可选部门
@perm_required('employee_view')
def employee_list(request):
    """员工列表：按姓名模糊搜索、按部门筛选、分页。"""
    # 先用 scope_employees 收敛数据范围，再 select_related 减少部门查询次数
    queryset = scope_employees(request.user).select_related('depart')
    keyword = request.GET.get('q', '').strip()
    depart_id = request.GET.get('depart', '').strip()
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    # 只有合法的数字部门 ID 才参与过滤，避免非法参数报错
    if depart_id.isdigit():
        queryset = queryset.filter(depart_id=int(depart_id))
    page = paginate(request, queryset, 10)
    context = {
        'page': page,
        'keyword': keyword,
        'depart_id': depart_id,
        'departments': _visible_departments(request.user),
        'is_employee_role': not request.user.is_superuser
        and not request.user.roles.filter(name='部门管理员').exists(),
    }
    return render(request, 'employee/list.html', context)


# 请求方式：GET 渲染表单，POST 提交新增
# 权限要求：需拥有 employee_add 权限
# 核心流程：EmployeeForm 校验姓名/年龄/手机号等字段后保存
# 返回内容：新增员工表单页或保存后重定向到列表页
@perm_required('employee_add')
def employee_add(request):
    """新增员工，ModelForm 完成全部字段校验。"""
    form = EmployeeForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        employee = form.save(commit=False)
        # 非超管不能自选部门，强制归属到本人所在部门，防止越权录入
        if not request.user.is_superuser:
            employee.depart = request.user.depart
        employee.save()
        messages.success(request, f'员工 {employee.name} 创建成功')
        return redirect('employee_list')
    return render(request, 'employee/form.html', {'form': form, 'title': '新增员工'})


# 请求方式：GET 渲染表单，POST 提交修改
# 权限要求：需拥有 employee_edit 权限
# 核心流程：按数据范围取出员工 → 表单校验（手机号唯一性排除自身）→ 保存
# 返回内容：编辑表单页或保存后重定向到列表页
@perm_required('employee_edit')
def employee_edit(request, pk):
    """编辑员工，手机号唯一性校验排除自身。"""
    employee = _get_scoped_employee(request.user, pk)
    form = EmployeeForm(
        request.POST or None, request.FILES or None,
        instance=employee, user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        employee = form.save(commit=False)
        # 非超管修改时仍强制归属本人部门，防止通过篡改参数跨部门调整
        if not request.user.is_superuser:
            employee.depart = request.user.depart
        employee.save()
        messages.success(request, f'员工 {employee.name} 修改成功')
        return redirect('employee_list')
    return render(request, 'employee/form.html', {
        'form': form, 'title': f'编辑员工 - {employee.name}', 'employee': employee,
    })


# 请求方式：POST（require_POST 限制）
# 权限要求：需拥有 employee_delete 权限
# 核心流程：按数据范围取出员工并删除，关联考勤/薪资由模型级联清理
# 返回内容：重定向到员工列表页
@perm_required('employee_delete')
@require_POST
def employee_delete(request, pk):
    """删除员工（关联考勤、薪资记录一并级联删除）。"""
    employee = _get_scoped_employee(request.user, pk)
    # 先暂存姓名，删除后仍可用于提示信息
    name = employee.name
    employee.delete()
    messages.success(request, f'员工 {name} 已删除')
    return redirect('employee_list')
