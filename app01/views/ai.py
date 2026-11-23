"""AI 智能助手视图：招聘 JD 生成（T2）、制度知识库问答（T3）、数据智能点评（T4）与浮窗入口。

三个必做模块统一复用 LLMClient.chat()；所有 POST 接口均返回 JSON，
失败时返回友好错误信息，不让页面崩溃。
"""
import re
from datetime import date

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from app01.middleware.permission import perm_required
from app01.models import Attendance, Knowledge
from app01.utils.ai import LLMClient
from app01.utils.prompts import (
    COMMENT_SYSTEM,
    JD_SYSTEM,
    QA_SYSTEM,
    build_jd_prompt,
    build_qa_prompt,
    build_salary_comment_prompt,
)
from app01.utils.scope import scope_employees, scope_salary


# 请求方式：GET
# 权限要求：ai_view
# 核心流程：准备 AI 页面所需的员工下拉、近 6 个月份与 API Key 配置状态
@perm_required('ai_view')
def ai_index(request):
    """AI 助手主页：集中展示 JD 生成、制度问答、数据点评三个模块。"""
    today = date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(6):
        months.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return render(request, 'ai/index.html', {
        # 员工下拉同样按数据范围过滤，普通员工只能点评自己
        'employees': scope_employees(request.user).select_related('depart'),
        'months': months,
        'ai_configured': LLMClient.is_configured(),
    })


@csrf_exempt
@perm_required('ai_view')
@require_POST
def generate_jd(request):
    """模块 A（T2）：输入岗位名称，AJAX 返回结构化招聘 JD。"""
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'status': False, 'error': '岗位名称不能为空'})
    if len(title) > 50:
        return JsonResponse({'status': False, 'error': '岗位名称过长（最多 50 字）'})

    try:
        text = LLMClient.chat(build_jd_prompt(title), system=JD_SYSTEM)
        return JsonResponse({'status': True, 'data': text})
    except Exception as exc:  # 调用失败兜底，避免页面崩溃
        return JsonResponse({'status': False, 'error': f'生成失败：{exc}'})


# 分词时剔除的常见疑问词/虚词，避免“怎么”“什么”等词造成误命中
STOP_PARTS = (
    '怎么', '怎样', '如何', '什么', '吗', '呢', '请问', '一下', '可以', '需要',
    '我们', '公司', '员工', '的', '了', '是否', '有没有', '知道', '告诉', '多少',
    '为什', '哪些', '我是', '我想', '我要',
)


def _extract_keywords(question):
    """把问题去标点后切成 2-4 字候选关键词，供 SQL 模糊检索使用。"""
    text = re.sub(r'[\s，。！？、,.!?；;：:"“”\'‘’（）()【】\[\]<>《》]', '', question)
    keywords = set()
    for size in (4, 3, 2):
        for i in range(0, max(len(text) - size + 1, 0)):
            word = text[i:i + size]
            # 含疑问词/虚词的片段直接跳过，减少无关命中
            if any(stop in word for stop in STOP_PARTS):
                continue
            keywords.add(word)
    # 长词优先，限制候选数量，避免拼接出超大 SQL
    return sorted(keywords, key=len, reverse=True)[:40]


def search_knowledge(question, limit=5):
    """T3 的“简化版 RAG”检索：SQL 关键词模糊匹配知识库，返回最相关的条目。"""
    # 1) 优先整句匹配标题或内容（问题恰好是制度原文片段时最精确）
    items = list(Knowledge.objects.filter(
        Q(title__icontains=question) | Q(content__icontains=question)
    )[:limit])
    if items:
        return items

    # 2) 整句无命中时，拆出关键词做 OR 模糊查询，再按命中词数排序
    keywords = _extract_keywords(question)
    if not keywords:
        return []
    query = Q()
    for word in keywords:
        query |= Q(title__icontains=word) | Q(content__icontains=word)
    matched = list(Knowledge.objects.filter(query))

    def score(item):
        text = item.title + item.content
        return sum(1 for word in keywords if word in text)

    matched = [item for item in matched if score(item) > 0]
    matched.sort(key=score, reverse=True)
    return matched[:limit]


def _answer_question(question):
    """知识库问答：优先由 AI 整理答案，模型不可用时依据最相关制度原文兜底。"""
    items = search_knowledge(question)
    if not items:
        # 没检索到资料：直接兜底，不调用模型，保证“不知道”且节省 API 调用
        return {'status': True, 'data': '不知道', 'sources': []}

    # 把命中的资料拼成上下文，配合 QA_SYSTEM 限定“只根据资料回答”
    context = '\n'.join(f'《{item.title}》\n{item.content}' for item in items)
    try:
        text = LLMClient.chat(build_qa_prompt(context, question), system=QA_SYSTEM)
        return {
            'status': True,
            'data': text,
            'sources': [item.title for item in items],
        }
    except Exception:
        # API 欠费、超时或网络异常时，仍回答已检索到的制度，避免已知问题也返回“回答失败”。
        # 只采用得分最高的条目，且明确标注来源，不编造资料中没有的内容。
        item = items[0]
        return {
            'status': True,
            'data': f'根据《{item.title}》：{item.content}',
            'sources': [item.title],
            'fallback': True,
        }


@csrf_exempt
@perm_required('ai_view')
@require_POST
def knowledge_qa(request):
    """模块 B（T3）：制度知识库问答，AI 助手页面使用。"""
    question = request.POST.get('question', '').strip()
    if not question:
        return JsonResponse({'status': False, 'error': '问题不能为空'})
    if len(question) > 200:
        return JsonResponse({'status': False, 'error': '问题过长（最多 200 字）'})
    return JsonResponse(_answer_question(question))


@csrf_exempt
@perm_required('ai_view')
@require_POST
def assistant_chat(request):
    """智能体浮窗入口：与知识库问答共用检索与提示词逻辑，返回 JSON 聊天气泡内容。"""
    question = request.POST.get('question', '').strip()
    if not question:
        return JsonResponse({'status': False, 'error': '请输入问题'})
    if len(question) > 200:
        return JsonResponse({'status': False, 'error': '问题过长（最多 200 字）'})
    return JsonResponse(_answer_question(question))


@csrf_exempt
@perm_required('ai_view')
@require_POST
def salary_comment(request):
    """模块 C（T4）：读取某员工某月的考勤与薪资数据，转文本注入提示词生成点评。"""
    emp_name = request.POST.get('employee', '').strip()
    month = request.POST.get('month', '').strip()
    if not emp_name or not month:
        return JsonResponse({'status': False, 'error': '请选择员工和月份'})

    # 薪资查询走数据范围，越权查询他人数据时按“未找到”处理
    record = scope_salary(request.user).select_related('employee').filter(
        employee__name=emp_name, month=month,
    ).first()
    if not record:
        return JsonResponse({'status': False, 'error': '未找到该员工该月薪资记录'})

    # 读取当月考勤数据并汇总，与薪资一起转成可读文本
    attendances = Attendance.objects.filter(employee=record.employee, date__startswith=month)
    late = attendances.filter(status='迟到').count()
    early = attendances.filter(status='早退').count()
    absent = attendances.filter(status='缺勤').count()

    data_text = (
        f'员工{record.employee.name}（{record.employee.depart.name}），{month}月：'
        f'基本工资{record.base_salary}元，奖金{record.bonus}元，扣款{record.deduction}元，'
        f'实发{record.total}元。'
        f'当月考勤记录{attendances.count()}天，其中迟到{late}次、早退{early}次、缺勤{absent}次。'
    )

    try:
        text = LLMClient.chat(build_salary_comment_prompt(data_text), system=COMMENT_SYSTEM)
        return JsonResponse({'status': True, 'data': text, 'data_text': data_text})
    except Exception as exc:
        return JsonResponse({'status': False, 'error': f'生成失败：{exc}'})
