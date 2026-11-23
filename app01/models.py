"""业务模型：部门、用户、角色、权限、员工、考勤、薪资、公告、任务。"""
from datetime import time
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


# 部门主数据：既是员工的组织归属，也是部门管理员数据范围的划分依据。
# name 唯一；Employee.depart 使用 PROTECT，部门下仍有员工时不允许删除。
class Department(models.Model):
    """部门。"""

    name = models.CharField('部门名称', max_length=50, unique=True)
    desc = models.CharField('部门描述', max_length=200, blank=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门'
        ordering = ['id']

    def __str__(self):
        return self.name


# RBAC 权限项：code 是代码中判断权限的唯一标识（如 employee:add），
# module 仅用于后台与角色配置页的分组展示。
class Permission(models.Model):
    """RBAC 权限项，以 code 标识一个可访问操作。"""

    code = models.CharField('权限编码', max_length=50, unique=True)
    name = models.CharField('权限名称', max_length=50)
    module = models.CharField('所属模块', max_length=20, blank=True)

    class Meta:
        verbose_name = '权限'
        verbose_name_plural = '权限'
        ordering = ['module', 'id']

    def __str__(self):
        return f'{self.name}({self.code})'


# 角色是权限的集合：与 Permission 多对多，一个角色可授权多个操作；
# 角色只做聚合，不直接保存用户，用户通过 User.roles 多对多关联。
class Role(models.Model):
    """角色，一个角色拥有若干权限。"""

    name = models.CharField('角色名称', max_length=50, unique=True)
    desc = models.CharField('角色描述', max_length=200, blank=True)
    permissions = models.ManyToManyField(
        Permission, verbose_name='权限', blank=True, related_name='roles'
    )

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['id']

    def __str__(self):
        return self.name


# 自定义用户：继承 AbstractUser 复用内置认证字段（username/password/is_superuser 等），
# 额外增加手机号、所属部门（SET_NULL，部门删除后账号保留）与多对多角色。
class User(AbstractUser):
    """自定义用户：在 Django 内置用户基础上增加手机号、所属部门与角色。"""

    phone = models.CharField('手机号', max_length=11, blank=True)
    depart = models.ForeignKey(
        Department, verbose_name='所属部门', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users'
    )
    roles = models.ManyToManyField(
        Role, verbose_name='角色', blank=True, related_name='users'
    )

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['id']

    # 返回权限编码集合（set）；超级管理员直接取权限表全集，普通用户按「用户-角色-权限」链路查询。
    # 结果缓存在实例属性 _perm_cache 上，同一请求内多次调用不会重复查库。
    def permission_codes(self):
        """返回当前用户拥有的权限编码集合（超级管理员拥有全部权限）。"""
        if not hasattr(self, '_perm_cache'):
            # 超级管理员视为拥有系统全部权限
            if self.is_superuser:
                self._perm_cache = set(Permission.objects.values_list('code', flat=True))
            else:
                self._perm_cache = set(
                    Permission.objects.filter(roles__users=self)
                    .values_list('code', flat=True)
                )
        return self._perm_cache

    # 权限判断入口：入参为权限编码，返回布尔值；超级管理员无条件放行，其余按编码精确匹配。
    def has_code(self, code):
        """判断用户是否拥有指定权限编码。"""
        return self.is_superuser or code in self.permission_codes()

    # 返回用于列表展示的角色名，多个角色用顿号连接；未分配角色时返回“未分配”。
    def role_names(self):
        """角色名称，用于列表展示。"""
        return '、'.join(self.roles.values_list('name', flat=True)) or '未分配'


# 员工档案：phone 全局唯一，作为员工业务主键使用；depart 为 PROTECT 外键，被引用时部门不可删；
# user 与账号一对一（SET_NULL），员工离职可解除关联而不影响账号；avatar 按 年/月 目录存放。
# account 为账户余额（Decimal，保留两位小数），gender 为中文枚举。
class Employee(models.Model):
    """员工档案。"""

    GENDER_CHOICES = (
        ('男', '男'),
        ('女', '女'),
    )

    name = models.CharField('姓名', max_length=20)
    age = models.PositiveIntegerField('年龄')
    gender = models.CharField('性别', max_length=2, choices=GENDER_CHOICES, default='男')
    account = models.DecimalField('账户余额', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    create_time = models.DateField('入职时间')
    phone = models.CharField('手机号', max_length=11, unique=True)
    depart = models.ForeignKey(
        Department, verbose_name='所属部门', on_delete=models.PROTECT,
        related_name='employees'
    )
    avatar = models.ImageField('头像', upload_to='avatar/%Y/%m/', null=True, blank=True)
    user = models.OneToOneField(
        User, verbose_name='关联账号', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employee'
    )

    class Meta:
        verbose_name = '员工'
        verbose_name_plural = '员工'
        ordering = ['-id']

    def __str__(self):
        return f'{self.name}({self.depart.name})'


# 考勤记录：同一员工同一天只允许一条（unique_together）；
# status 不手工录入，由 save() 调用 calculate_status() 根据打卡时间自动推导。
class Attendance(models.Model):
    """考勤记录，状态由上下班时间自动计算。"""

    STATUS_CHOICES = (
        ('按时', '按时'),
        ('迟到', '迟到'),
        ('早退', '早退'),
        ('缺勤', '缺勤'),
    )
    # 标准上下班时间，作为迟到/早退的判定阈值
    WORK_START = time(9, 0)
    WORK_END = time(18, 0)

    employee = models.ForeignKey(
        Employee, verbose_name='员工', on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField('考勤日期')
    check_in = models.TimeField('上班时间', null=True, blank=True)
    check_out = models.TimeField('下班时间', null=True, blank=True)
    status = models.CharField('考勤状态', max_length=8, choices=STATUS_CHOICES, default='缺勤')

    class Meta:
        verbose_name = '考勤'
        verbose_name_plural = '考勤'
        ordering = ['-date', 'employee_id']
        unique_together = ('employee', 'date')

    def __str__(self):
        return f'{self.employee.name} {self.date} {self.status}'

    # 无入参，返回状态字符串；判定顺序：未打上班卡→缺勤，上班晚于 09:00→迟到，
    # 未打下班卡或早于 18:00→早退，其余为按时。
    def calculate_status(self):
        """按上下班时间计算考勤状态。

        规则：未打上班卡→缺勤；晚于 09:00→迟到；未打下班卡或早于 18:00→早退；否则按时。
        """
        if not self.check_in:
            return '缺勤'
        # 迟到判定优先于早退，一次打卡异常只落一个状态
        if self.check_in > self.WORK_START:
            return '迟到'
        if not self.check_out or self.check_out < self.WORK_END:
            return '早退'
        return '按时'

    # 保存前强制重算状态，防止通过后台或表单直接改写 status 字段
    def save(self, *args, **kwargs):
        self.status = self.calculate_status()
        super().save(*args, **kwargs)

    # 返回 Bootstrap 语义色名，供模板渲染不同颜色的状态标签
    def status_color(self):
        """状态对应的 Bootstrap 标签样式。"""
        return {
            '按时': 'success', '迟到': 'warning', '早退': 'warning', '缺勤': 'danger',
        }.get(self.status, 'default')


# 薪资记录：同一员工同一月份唯一（unique_together），月份格式 YYYY-MM；
# total 为计算字段（editable=False），不接受表单输入，由 save() 统一兜底重算。
class Salary(models.Model):
    """薪资记录，实发工资由公式自动计算。"""

    employee = models.ForeignKey(
        Employee, verbose_name='员工', on_delete=models.CASCADE,
        related_name='salaries'
    )
    month = models.CharField('月份', max_length=7, help_text='格式：YYYY-MM')
    base_salary = models.DecimalField('基本工资', max_digits=10, decimal_places=2)
    bonus = models.DecimalField('奖金', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deduction = models.DecimalField('扣款', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField('实发工资', max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False)

    class Meta:
        verbose_name = '薪资'
        verbose_name_plural = '薪资'
        ordering = ['-month', 'employee_id']
        unique_together = ('employee', 'month')

    def __str__(self):
        return f'{self.employee.name} {self.month} {self.total}'

    # 无入参，返回 Decimal 类型实发金额：基本工资 + 奖金 - 扣款
    def calc_total(self):
        """实发 = 基本工资 + 奖金 - 扣款。"""
        return self.base_salary + self.bonus - self.deduction

    def save(self, *args, **kwargs):
        # 模型层兜底计算，保证任何入口保存的数据都一致
        self.total = self.calc_total()
        super().save(*args, **kwargs)


# 公告：publisher 为 SET_NULL，发布人账号被删后公告仍保留；
# 默认排序先置顶、再按发布时间倒序。
class Notice(models.Model):
    """公告。"""

    title = models.CharField('标题', max_length=100)
    content = models.TextField('内容')
    publisher = models.ForeignKey(
        User, verbose_name='发布人', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='notices'
    )
    create_time = models.DateTimeField('发布时间', auto_now_add=True)
    is_top = models.BooleanField('是否置顶', default=False)

    class Meta:
        verbose_name = '公告'
        verbose_name_plural = '公告'
        ordering = ['-is_top', '-create_time']

    def __str__(self):
        return self.title


# 任务：leader 为 CASCADE 外键，负责人账号删除时其负责任务一并删除；
# level 为三档枚举（紧急/重要/普通），默认普通。
class Task(models.Model):
    """任务，新增通过 AJAX 异步提交。"""

    LEVEL_CHOICES = (
        ('紧急', '紧急'),
        ('重要', '重要'),
        ('普通', '普通'),
    )

    level = models.CharField('级别', max_length=4, choices=LEVEL_CHOICES, default='普通')
    title = models.CharField('标题', max_length=50)
    detail = models.TextField('详情')
    leader = models.ForeignKey(
        User, verbose_name='负责人', on_delete=models.CASCADE,
        related_name='tasks'
    )
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'
        ordering = ['-id']

    def __str__(self):
        return f'[{self.level}] {self.title}'

    # 返回任务级别对应的 Bootstrap 语义色名（紧急-红、重要-黄、普通-蓝）
    def level_color(self):
        """级别对应的 Bootstrap 标签样式。"""
        return {'紧急': 'danger', '重要': 'warning', '普通': 'info'}.get(self.level, 'info')


# 企业知识库（T3）：制度/手册条目，AI 问答时先做 SQL 关键词检索，
# 再把命中条目作为上下文注入提示词，让模型“照着资料回答”。
class Knowledge(models.Model):
    """企业知识库（制度/手册条目），供智能问答检索。"""

    title = models.CharField('标题', max_length=128)
    content = models.TextField('内容')

    class Meta:
        verbose_name = '知识库'
        verbose_name_plural = '知识库'
        ordering = ['id']

    def __str__(self):
        return self.title
