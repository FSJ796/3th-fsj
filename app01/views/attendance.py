"""考勤管理视图（T6）。"""
import re

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app01.forms import AttendanceForm
from app01.middleware.permission import perm_required
from app01.models import Attendance
from app01.utils.pagination import paginate
from app01.utils.scope import scope_attendance, scope_employees

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


# 辅助函数：在当前用户数据范围内取考勤记录，越权访问返回 404
def _get_scoped_attendance(user, pk):
    record = scope_attendance(user).filter(pk=pk).first()
    if record is None:
        raise Http404('考勤记录不存在或无权访问')
    return record


# 请求方式：GET
# 权限要求：需拥有 attendance_view 权限
# 核心流程：在权限范围内按日期、状态、员工姓名组合筛选，再分页
# 返回内容：考勤列表模板，含分页对象、筛选条件与状态下拉选项
@perm_required('attendance_view')
def attendance_list(request):
    """考勤列表：按日期、状态、员工姓名筛选并分页。"""
    # select_related 一次性取回员工及其部门，避免模板渲染时产生多余查询
    queryset = scope_attendance(request.user).select_related('employee', 'employee__depart')
    day = request.GET.get('date', '').strip()
    status = request.GET.get('status', '').strip()
    keyword = request.GET.get('q', '').strip()
    # 只有符合 YYYY-MM-DD 格式的日期才参与过滤，防止非法参数
    if DATE_RE.match(day):
        queryset = queryset.filter(date=day)
    # 状态必须是模型中定义的可选值，避免任意字符串进入查询
    if status in dict(Attendance.STATUS_CHOICES):
        queryset = queryset.filter(status=status)
    if keyword:
        queryset = queryset.filter(employee__name__icontains=keyword)
    page = paginate(request, queryset, 10)
    context = {
        'page': page, 'day': day, 'status': status, 'keyword': keyword,
        'status_choices': Attendance.STATUS_CHOICES,
    }
    return render(request, 'attendance/list.html', context)


# 请求方式：GET 渲染表单，POST 提交新增
# 权限要求：需拥有 attendance_add 权限
# 核心流程：AttendanceForm 校验（时间先后、员工当天唯一）后保存，保存时自动计算状态
# 返回内容：新增考勤表单页或保存后重定向到列表页
@perm_required('attendance_add')
def attendance_add(request):
    """新增考勤，状态由上下班时间自动计算。"""
    form = AttendanceForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        # 状态不在表单中手填，由模型的 save() 调用 calculate_status 自动判定
        record = form.save()
        messages.success(request, f'考勤记录已保存，状态：{record.status}')
        return redirect('attendance_list')
    return render(request, 'attendance/form.html', {'form': form, 'title': '新增考勤'})


# 请求方式：GET 渲染表单，POST 提交修改
# 权限要求：需拥有 attendance_edit 权限
# 核心流程：按数据范围取出记录 → 表单校验 → 保存时按新的上下班时间重算状态
# 返回内容：编辑考勤表单页或保存后重定向到列表页
@perm_required('attendance_edit')
def attendance_edit(request, pk):
    """编辑考勤，保存时重新计算状态。"""
    record = _get_scoped_attendance(request.user, pk)
    form = AttendanceForm(request.POST or None, instance=record, user=request.user)
    if request.method == 'POST' and form.is_valid():
        # 修改上下班时间后，模型 save() 会再次自动判定状态
        record = form.save()
        messages.success(request, f'考勤记录已更新，状态：{record.status}')
        return redirect('attendance_list')
    return render(request, 'attendance/form.html', {
        'form': form, 'title': f'编辑考勤 - {record.employee.name}', 'record': record,
    })


# 请求方式：POST（require_POST 限制）
# 权限要求：需拥有 attendance_delete 权限
# 核心流程：按数据范围取出考勤记录并删除
# 返回内容：重定向到考勤列表页
@perm_required('attendance_delete')
@require_POST
def attendance_delete(request, pk):
    """删除考勤记录。"""
    record = _get_scoped_attendance(request.user, pk)
    record.delete()
    messages.success(request, '考勤记录已删除')
    return redirect('attendance_list')
