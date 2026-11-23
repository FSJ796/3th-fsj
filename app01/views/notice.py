"""公告管理视图（T8）：发布、列表、置顶、搜索、分页。"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app01.forms import NoticeForm
from app01.middleware.permission import perm_required
from app01.models import Notice
from app01.utils.pagination import paginate


# 请求方式：GET
# 权限要求：需拥有 notice_view 权限
# 核心流程：预取发布人，按标题或内容关键字模糊搜索，再分页
# 返回内容：公告列表模板，置顶公告按模型排序规则优先展示
@perm_required('notice_view')
def notice_list(request):
    """公告列表，支持关键字搜索与分页，置顶公告优先排序。"""
    keyword = request.GET.get('q', '').strip()
    queryset = Notice.objects.select_related('publisher')
    if keyword:
        # Q 对象实现“标题或内容任一命中”的 OR 模糊搜索
        from django.db.models import Q
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
    page = paginate(request, queryset, 10)
    return render(request, 'notice/list.html', {'page': page, 'keyword': keyword})


# 请求方式：GET 渲染表单，POST 提交发布
# 权限要求：需拥有 notice_add 权限
# 核心流程：NoticeForm 校验标题与内容后保存，发布人取当前登录用户
# 返回内容：发布公告表单页或发布后重定向到列表页
@perm_required('notice_add')
def notice_add(request):
    """发布公告，发布人与发布时间自动记录。"""
    form = NoticeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        notice = form.save(commit=False)
        # 发布人由服务端写入，避免前端伪造；发布时间由模型 auto_now_add 生成
        notice.publisher = request.user
        notice.save()
        messages.success(request, '公告发布成功')
        return redirect('notice_list')
    return render(request, 'notice/form.html', {'form': form, 'title': '发布公告'})


# 请求方式：POST（require_POST 限制）
# 权限要求：需拥有 notice_top 权限
# 核心流程：读取公告并取反置顶状态，仅更新 is_top 单个字段
# 返回内容：重定向回公告列表页
@perm_required('notice_top')
@require_POST
def notice_toggle_top(request, pk):
    """切换公告置顶状态。"""
    notice = get_object_or_404(Notice, pk=pk)
    notice.is_top = not notice.is_top
    # update_fields 限定只写回置顶字段，减少不必要的数据库写入
    notice.save(update_fields=['is_top'])
    messages.success(request, '已置顶该公告' if notice.is_top else '已取消置顶')
    return redirect('notice_list')
