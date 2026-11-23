"""一次性初始化命令：创建权限、角色与超级管理员账号。

用法：python manage.py init_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from app01.models import Permission, Role, User
from app01.utils.scope import ROLE_DEPT_ADMIN, ROLE_EMPLOYEE, ROLE_SUPER_ADMIN

# 全部权限项：每项为（权限编码, 权限名称, 所属模块）
# 编码是视图层 has_code 校验的唯一标识，模块仅用于后台列表分组展示
PERMISSIONS = [
    ('department_view', '查看部门', '部门管理'),
    ('department_add', '新增部门', '部门管理'),
    ('department_edit', '编辑部门', '部门管理'),
    ('department_delete', '删除部门', '部门管理'),
    ('employee_view', '查看员工', '员工管理'),
    ('employee_add', '新增员工', '员工管理'),
    ('employee_edit', '编辑员工', '员工管理'),
    ('employee_delete', '删除员工', '员工管理'),
    ('attendance_view', '查看考勤', '考勤管理'),
    ('attendance_add', '新增考勤', '考勤管理'),
    ('attendance_edit', '编辑考勤', '考勤管理'),
    ('attendance_delete', '删除考勤', '考勤管理'),
    ('salary_view', '查看薪资', '薪资管理'),
    ('salary_add', '录入薪资', '薪资管理'),
    ('salary_edit', '编辑薪资', '薪资管理'),
    ('salary_delete', '删除薪资', '薪资管理'),
    ('notice_view', '查看公告', '公告管理'),
    ('notice_add', '发布公告', '公告管理'),
    ('notice_top', '公告置顶', '公告管理'),
    ('task_view', '查看任务', '任务管理'),
    ('task_add', '新增任务', '任务管理'),
    ('stats_view', '数据统计', '数据统计'),
    ('ai_view', 'AI 助手', 'AI 助手'),
    ('system_manage', '系统管理', '系统管理'),
]

# 三级 RBAC 中的“角色-权限”关系：角色名 -> 权限编码列表
# 超级管理员取全部权限；部门管理员负责本部门业务但无删除与系统管理；普通员工只读
ROLE_PERMISSIONS = {
    ROLE_SUPER_ADMIN: [code for code, _, _ in PERMISSIONS],
    ROLE_DEPT_ADMIN: [
        'department_view',
        'employee_view', 'employee_add', 'employee_edit',
        'attendance_view', 'attendance_add', 'attendance_edit',
        'salary_view', 'salary_add', 'salary_edit',
        'notice_view', 'notice_add',
        'task_view', 'task_add',
        'stats_view', 'ai_view',
    ],
    ROLE_EMPLOYEE: [
        'employee_view', 'attendance_view', 'salary_view', 'notice_view', 'ai_view',
    ],
}

# 角色描述，写入 Role.desc，用于系统管理页面展示各角色职责
ROLE_DESCRIPTIONS = {
    ROLE_SUPER_ADMIN: '拥有全部权限，可管理用户、角色与权限分配',
    ROLE_DEPT_ADMIN: '管理本部门员工、考勤与薪资录入',
    ROLE_EMPLOYEE: '仅可查看自己的档案、考勤与薪资（只读）',
}


class Command(BaseCommand):
    help = '初始化权限、角色与管理员账号（可重复执行）'

    @transaction.atomic
    def handle(self, *args, **options):
        # 第一步：写入权限项。update_or_create 保证重复执行时只更新名称与模块，不会产生重复数据
        for code, name, module in PERMISSIONS:
            permission, created = Permission.objects.update_or_create(
                code=code, defaults={'name': name, 'module': module}
            )
            if created:
                self.stdout.write(f'创建权限：{permission.name}（{code}）')

        # 第二步：建立“角色-权限”关系，先缓存权限对象，再按映射批量 set
        permission_map = {item.code: item for item in Permission.objects.all()}
        for role_name, codes in ROLE_PERMISSIONS.items():
            role, created = Role.objects.update_or_create(
                name=role_name, defaults={'desc': ROLE_DESCRIPTIONS[role_name]}
            )
            role.permissions.set([permission_map[code] for code in codes])
            self.stdout.write(('创建' if created else '更新') + f'角色：{role_name}（{len(codes)} 项权限）')

        # 第三步：创建超级管理员 fsj，仅在首次创建时设置初始密码，已存在则跳过以免覆盖
        admin, created = User.objects.get_or_create(
            username='fsj',
            defaults={'is_staff': True, 'is_superuser': True, 'email': 'fsj@hrms.local'},
        )
        if created:
            admin.set_password('fsj123')
            admin.save()
            self.stdout.write('创建超级管理员：fsj / fsj123')
        else:
            self.stdout.write('超级管理员 fsj 已存在，跳过创建')

        # 三级 RBAC 的最后一环：给用户绑定角色（用户 -> 角色 -> 权限）
        admin.roles.set([Role.objects.get(name=ROLE_SUPER_ADMIN)])
        self.stdout.write(self.style.SUCCESS('init_data 初始化完成'))
