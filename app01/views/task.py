"""任务管理视图（T9）：AJAX 异步提交并返回 JSON。"""
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from app01.forms import TaskForm
from app01.middleware.permission import perm_required
from app01.models import Task, User
from app01.utils.pagination import paginate


# 辅助函数：任务可见范围，超管看全部、部门管理员看本部门及本人、普通员工只看本人
def _task_queryset(user):
    """按数据范围返回任务：管理员全部，部门管理员看本部门，其他看自己。"""
    if user.is_superuser:
        return Task.objects.all()
    if user.roles.filter(name='部门管理员').exists() and user.depart_id:
        return Task.objects.filter(
            Q(leader__depart_id=user.depart_id) | Q(leader=user)
        )
    return Task.objects.filter(leader=user)


# 辅助函数：新增任务时负责人下拉框的可选范围，同样按角色收敛
def _leader_queryset(user):
    """新增任务时可选的负责人范围。"""
    if user.is_superuser:
        return User.objects.filter(is_active=True)
    if user.depart_id:
        return User.objects.filter(
            Q(depart_id=user.depart_id) | Q(pk=user.pk), is_active=True
        )
    return User.objects.filter(pk=user.pk)


# 请求方式：GET
# 权限要求：需拥有 task_view 权限
# 核心流程：先按数据范围取任务，再按任务级别筛选，最后分页
# 返回内容：任务列表模板，携带分页对象、级别筛选值与级别选项
@perm_required('task_view')
def task_list(request):
    """任务列表，支持按级别筛选与分页。"""
    queryset = _task_queryset(request.user).select_related('leader')
    level = request.GET.get('level', '').strip()
    # 级别必须是模型定义的有效值才参与过滤
    if level in dict(Task.LEVEL_CHOICES):
        queryset = queryset.filter(level=level)
    page = paginate(request, queryset, 10)
    return render(request, 'task/list.html', {
        'page': page, 'level': level, 'level_choices': Task.LEVEL_CHOICES,
    })


# 请求方式：POST（仅接受 AJAX 异步提交）
# 权限要求：需拥有 task_add 权限
# 核心流程：先替换负责人可选范围防止越权指派，再校验表单
# 返回内容：成功返回任务 JSON；失败返回字段级错误与 400 状态码
@perm_required('task_add')
@require_POST
def task_add(request):
    """AJAX 新增任务，校验失败返回字段级错误信息。"""
    form = TaskForm(request.POST)
    # 在校验前收紧负责人 queryset，避免前端提交超出权限的负责人 ID
    form.fields['leader'].queryset = _leader_queryset(request.user)
    if form.is_valid():
        task = form.save()
        return JsonResponse({
            'status': 'ok',
            'message': '任务创建成功',
            'task': {
                'id': task.pk,
                'level': task.level,
                'title': task.title,
                'detail': task.detail,
                'leader': task.leader.username,
                'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            },
        })
    # 把表单错误整理为 {字段名: [错误信息]}，前端可直接定位到对应输入框
    errors = {field: [str(msg) for msg in messages] for field, messages in form.errors.items()}
    return JsonResponse({'status': 'error', 'errors': errors}, status=400)
