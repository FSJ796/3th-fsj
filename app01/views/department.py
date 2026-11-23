"""部门管理视图（T2）。"""
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app01.forms import DepartmentForm
from app01.middleware.permission import perm_required
from app01.models import Department
from app01.utils.pagination import paginate


# 请求方式：GET
# 权限要求：需登录且拥有 department_view 权限（perm_required 装饰器校验）
# 核心流程：读取关键字做名称模糊搜索，再按每页 10 条分页
# 返回内容：部门列表模板，携带分页对象与搜索关键字
@perm_required('department_view')
def department_list(request):
    """部门列表，支持名称搜索与分页。"""
    keyword = request.GET.get('q', '').strip()
    queryset = Department.objects.all()
    # 使用 icontains 实现不区分大小写的模糊匹配
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    page = paginate(request, queryset, 10)
    return render(request, 'department/list.html', {'page': page, 'keyword': keyword})


# 请求方式：GET 渲染表单，POST 提交新增
# 权限要求：需拥有 department_add 权限
# 核心流程：DepartmentForm 校验（名称长度与重名校验）通过后保存
# 返回内容：新增表单页或保存后重定向到列表页
@perm_required('department_add')
def department_add(request):
    """新增部门。"""
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # 表单校验通过后直接落库（字段校验逻辑封装在 DepartmentForm 中）
        form.save()
        messages.success(request, '部门创建成功')
        return redirect('department_list')
    return render(request, 'department/form.html', {'form': form, 'title': '新增部门'})


# 请求方式：GET 渲染表单，POST 提交修改
# 权限要求：需拥有 department_edit 权限
# 核心流程：按主键取出部门作为表单实例，校验通过后保存
# 返回内容：编辑表单页或保存后重定向到列表页
@perm_required('department_edit')
def department_edit(request, pk):
    """编辑部门。"""
    # 不存在的部门直接返回 404
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '部门修改成功')
        return redirect('department_list')
    return render(request, 'department/form.html', {'form': form, 'title': '编辑部门'})


# 请求方式：POST（require_POST 限制，防止通过 GET 误删）
# 权限要求：需拥有 department_delete 权限
# 核心流程：按主键删除部门；外键为 PROTECT 时捕获 ProtectedError 并提示
# 返回内容：无论成功与否都重定向回部门列表
@perm_required('department_delete')
@require_POST
def department_delete(request, pk):
    """删除部门；存在员工时禁止删除。"""
    department = get_object_or_404(Department, pk=pk)
    try:
        # 部门下仍有员工时数据库会抛出 ProtectedError，此处转为友好提示
        department.delete()
        messages.success(request, '部门删除成功')
    except ProtectedError:
        messages.error(request, '该部门下仍有员工，无法删除，请先调整员工所属部门')
    return redirect('department_list')
