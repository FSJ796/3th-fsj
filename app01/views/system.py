"""系统管理视图（T5）：用户角色分配、角色权限分配。"""
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from app01.middleware.permission import perm_required
from app01.models import Permission, Role, User
from app01.utils.pagination import paginate


# 请求方式：GET
# 权限要求：需拥有 system_manage 权限
# 核心流程：预取角色与部门，按用户名模糊搜索后分页
# 返回内容：用户列表模板，展示每个用户的角色与所属部门
@perm_required('system_manage')
def user_list(request):
    """用户列表，展示角色与所属部门。"""
    keyword = request.GET.get('q', '').strip()
    # prefetch_related 解决角色多对多查询，select_related 解决部门外键查询
    queryset = User.objects.prefetch_related('roles').select_related('depart')
    if keyword:
        queryset = queryset.filter(username__icontains=keyword)
    page = paginate(request, queryset, 10)
    return render(request, 'system/user_list.html', {'page': page, 'keyword': keyword})


# 请求方式：GET 展示角色分配页，POST 提交角色 ID 列表
# 权限要求：需拥有 system_manage 权限
# 核心流程：GET 回显当前角色；POST 用 set() 覆盖式更新用户角色
# 返回内容：角色分配页或保存后重定向到用户列表
@perm_required('system_manage')
def user_roles(request, pk):
    """为指定用户分配角色。"""
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        role_ids = request.POST.getlist('roles')
        # set() 为覆盖式替换：未勾选的角色会被移除，而非追加
        user_obj.roles.set(Role.objects.filter(pk__in=role_ids))
        messages.success(request, f'用户 {user_obj.username} 的角色已更新')
        return redirect('system_user_list')
    return render(request, 'system/user_roles.html', {
        'user_obj': user_obj,
        'roles': Role.objects.prefetch_related('permissions'),
        'selected_ids': list(user_obj.roles.values_list('pk', flat=True)),
    })


# 请求方式：GET
# 权限要求：需拥有 system_manage 权限
# 核心流程：预取权限并用 Count 聚合，得到每个角色的权限数量
# 返回内容：角色列表模板
@perm_required('system_manage')
def role_list(request):
    """角色列表，展示每个角色的权限数量。"""
    roles = Role.objects.prefetch_related('permissions').annotate(
        # 聚合字段 perm_count 供模板直接展示权限数
        perm_count=Count('permissions')
    )
    return render(request, 'system/role_list.html', {'roles': roles})


# 请求方式：GET 展示权限分配页，POST 提交权限 ID 列表
# 权限要求：需拥有 system_manage 权限
# 核心流程：GET 按模块分组权限并回显；POST 用 set() 覆盖式更新角色权限
# 返回内容：权限分配页或保存后重定向到角色列表
@perm_required('system_manage')
def role_permissions(request, pk):
    """为指定角色分配权限。"""
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        perm_ids = request.POST.getlist('permissions')
        # set() 为覆盖式替换：勾选结果即最终权限集合
        role.permissions.set(Permission.objects.filter(pk__in=perm_ids))
        messages.success(request, f'角色 {role.name} 的权限已更新')
        return redirect('system_role_list')
    permissions = Permission.objects.all()
    modules = {}
    # 按 module 字段分组，未标注模块的权限归入“其他”，方便页面分区勾选
    for perm in permissions:
        modules.setdefault(perm.module or '其他', []).append(perm)
    selected_ids = list(role.permissions.values_list('pk', flat=True))
    return render(request, 'system/role_permissions.html', {
        'role': role,
        'modules': modules,
        'selected_ids': selected_ids,
    })
