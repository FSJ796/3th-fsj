"""app01 路由配置。"""
from django.urls import path

from app01.views import (
    ai as ai_views,
    attendance as attendance_views,
    auth as auth_views,
    department as department_views,
    employee as employee_views,
    home as home_views,
    notice as notice_views,
    salary as salary_views,
    stats as stats_views,
    system as system_views,
    task as task_views,
)

urlpatterns = [
    # 首页与认证
    path('', home_views.index, name='index'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    # 图形验证码图片，登录页通过 <img> 请求该地址
    path('captcha/', auth_views.captcha_view, name='captcha'),

    # 部门管理：列表、新增、按主键编辑与删除
    path('department/', department_views.department_list, name='department_list'),
    path('department/add/', department_views.department_add, name='department_add'),
    path('department/edit/<int:pk>/', department_views.department_edit, name='department_edit'),
    path('department/delete/<int:pk>/', department_views.department_delete, name='department_delete'),

    # 员工管理：员工档案的增删改查，列表按当前用户数据范围过滤
    path('employee/', employee_views.employee_list, name='employee_list'),
    path('employee/add/', employee_views.employee_add, name='employee_add'),
    path('employee/edit/<int:pk>/', employee_views.employee_edit, name='employee_edit'),
    path('employee/delete/<int:pk>/', employee_views.employee_delete, name='employee_delete'),

    # 考勤管理：打卡记录的增删改查
    path('attendance/', attendance_views.attendance_list, name='attendance_list'),
    path('attendance/add/', attendance_views.attendance_add, name='attendance_add'),
    path('attendance/edit/<int:pk>/', attendance_views.attendance_edit, name='attendance_edit'),
    path('attendance/delete/<int:pk>/', attendance_views.attendance_delete, name='attendance_delete'),

    # 薪资管理：按月薪资记录的增删改查
    path('salary/', salary_views.salary_list, name='salary_list'),
    path('salary/add/', salary_views.salary_add, name='salary_add'),
    path('salary/edit/<int:pk>/', salary_views.salary_edit, name='salary_edit'),
    path('salary/delete/<int:pk>/', salary_views.salary_delete, name='salary_delete'),

    # 公告管理：列表、发布以及切换置顶状态
    path('notice/', notice_views.notice_list, name='notice_list'),
    path('notice/add/', notice_views.notice_add, name='notice_add'),
    path('notice/top/<int:pk>/', notice_views.notice_toggle_top, name='notice_toggle_top'),

    # 任务管理（AJAX）：列表与新增均以 JSON 交互，供前端局部刷新
    path('task/', task_views.task_list, name='task_list'),
    path('task/add/', task_views.task_add, name='task_add'),

    # 数据统计可视化：页面本身与两个图表数据接口
    path('stats/', stats_views.stats_index, name='stats_index'),
    path('stats/department-data/', stats_views.department_chart_data, name='stats_department'),
    path('stats/salary-data/', stats_views.salary_trend_data, name='stats_salary'),

    # AI 智能助手：主页、招聘 JD 生成、制度知识库问答、数据点评与浮窗聊天入口
    path('ai/', ai_views.ai_index, name='ai_index'),
    path('ai/jd/', ai_views.generate_jd, name='ai_jd'),
    path('ai/qa/', ai_views.knowledge_qa, name='ai_qa'),
    path('ai/comment/', ai_views.salary_comment, name='ai_comment'),
    path('ai/chat/', ai_views.assistant_chat, name='ai_chat'),

    # 用户与角色权限管理：用户列表、用户分配角色、角色列表、角色分配权限
    path('system/user/', system_views.user_list, name='system_user_list'),
    path('system/user/<int:pk>/roles/', system_views.user_roles, name='system_user_roles'),
    path('system/role/', system_views.role_list, name='system_role_list'),
    path('system/role/<int:pk>/permissions/', system_views.role_permissions, name='system_role_permissions'),
]
