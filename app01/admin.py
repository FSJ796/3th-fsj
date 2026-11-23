"""Django Admin 后台注册。"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from app01.models import (
    Attendance, Department, Employee, Notice, Permission, Role, Salary, Task, User,
)


# 自定义用户后台：在 Django 默认字段分组后追加手机号、部门与角色，便于管理员直接维护。
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """自定义用户后台，追加部门与角色。"""

    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('phone', 'depart', 'roles')}),
    )


# 部门后台：列表展示 id、名称、描述与创建时间，支持按名称搜索。
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'desc', 'create_time')
    search_fields = ('name',)


# 权限项后台：展示编码、名称与所属模块，可按模块筛选。
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'module')
    list_filter = ('module',)


# 角色后台：权限采用横向穿梭框（filter_horizontal）多选，配置更直观。
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')
    filter_horizontal = ('permissions',)


# 员工后台：列表展示关键档案字段，可按部门、性别筛选，按姓名或手机号搜索。
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'phone', 'depart', 'create_time', 'account')
    list_filter = ('depart', 'gender')
    search_fields = ('name', 'phone')


# 考勤后台：展示打卡时间与自动计算的状态，可按状态、日期筛选。
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('status', 'date')


# 薪资后台：展示基本工资、奖金、扣款与实发合计，可按月份筛选。
@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'base_salary', 'bonus', 'deduction', 'total')
    list_filter = ('month',)


# 公告后台：展示标题、发布人、发布时间与置顶标记，可按置顶筛选。
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'publisher', 'create_time', 'is_top')
    list_filter = ('is_top',)


# 任务后台：展示标题、级别、负责人与创建时间，可按级别筛选。
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'leader', 'create_time')
    list_filter = ('level',)
