"""数据范围工具：超级管理员看全部，部门管理员看本部门，普通员工看自己。"""
from app01.models import Attendance, Employee, Salary

# 角色名称常量：与数据库中的角色记录一一对应，是数据范围隔离的判定依据
ROLE_SUPER_ADMIN = '超级管理员'
ROLE_DEPT_ADMIN = '部门管理员'
ROLE_EMPLOYEE = '普通员工'


# 入参为当前用户，返回布尔值：用户已登录且拥有「部门管理员」角色时为真
def is_dept_admin(user):
    """是否为部门管理员。"""
    return user.is_authenticated and user.roles.filter(name=ROLE_DEPT_ADMIN).exists()


# 数据范围核心函数：返回当前用户有权查看的员工查询集。
# 优先级：超级管理员→全部；部门管理员→本部门（无部门则空集）；普通员工→仅本人档案；其余→空集。
def scope_employees(user):
    """返回当前用户有权查看的员工查询集。"""
    if user.is_superuser:
        return Employee.objects.all()
    # 部门管理员未绑定部门时返回空集，避免退化为可查看全部员工
    if is_dept_admin(user):
        if user.depart_id:
            return Employee.objects.filter(depart_id=user.depart_id)
        return Employee.objects.none()
    # 普通员工通过 OneToOne 反向属性 employee 取本人档案，未关联档案则空集
    employee = getattr(user, 'employee', None)
    if employee:
        return Employee.objects.filter(pk=employee.pk)
    return Employee.objects.none()


# 考勤范围：先取有权查看的员工集合，再按 employee 外键过滤，保证与员工范围一致
def scope_attendance(user):
    """返回当前用户有权查看的考勤查询集。"""
    return Attendance.objects.filter(employee__in=scope_employees(user))


# 薪资范围：同样以员工数据范围为基准过滤，不额外放开权限
def scope_salary(user):
    """返回当前用户有权查看的薪资查询集。"""
    return Salary.objects.filter(employee__in=scope_employees(user))
