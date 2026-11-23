"""表单层：负责数据校验与 Bootstrap 样式注入。"""
import re
from datetime import date

from django import forms

from app01.models import (
    Attendance, Department, Employee, Notice, Salary, Task,
)

# 正则常量：手机号要求 1 开头、第二位 3-9、共 11 位；月份要求 YYYY-MM 且月份 01-12
PHONE_RE = re.compile(r'^1[3-9]\d{9}$')
MONTH_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


# 入参为表单实例；遍历全部字段，为非复选框控件追加 form-control 样式（已有则跳过），无返回值。
def _apply_bootstrap_style(form):
    """为所有非复选框控件添加 form-control 样式。"""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            continue
        css = widget.attrs.get('class', '')
        if 'form-control' not in css:
            widget.attrs['class'] = f'{css} form-control'.strip()


# 登录表单：三个字段均为必填，captcha 只做格式校验，正确性由登录视图比对 session 中的验证码。
class LoginForm(forms.Form):
    """登录表单：用户名、密码、图片验证码。"""

    username = forms.CharField(
        label='用户名', max_length=30,
        widget=forms.TextInput(attrs={'placeholder': '请输入用户名', 'autofocus': True}),
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'placeholder': '请输入密码'}),
    )
    captcha = forms.CharField(
        label='验证码', max_length=6,
        widget=forms.TextInput(attrs={'placeholder': '请输入图中字符'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)

    # 校验验证码长度必须为 4 位（去除首尾空格后）；返回清洗后的字符串，格式不符时抛出 ValidationError。
    # 验证码正确性由登录视图与 session 中的值比对，本方法只负责格式。
    def clean_captcha(self):
        """验证码由视图中与 session 比对，这里只做长度校验。"""
        value = self.cleaned_data['captcha'].strip()
        # 长度不符直接判为非法输入，避免无意义地查 session
        if len(value) != 4:
            raise forms.ValidationError('请输入 4 位验证码')
        return value


# 部门表单：仅提交名称与描述，创建时间由模型自动填充；名称做长度与唯一性校验。
class DepartmentForm(forms.ModelForm):
    """部门表单。"""

    class Meta:
        model = Department
        fields = ['name', 'desc']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '例如：技术部'}),
            'desc': forms.TextInput(attrs={'placeholder': '部门职责简述（可选）'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)

    # 校验部门名称：去掉首尾空格后长度需在 2-50 之间，且不能与其他部门重名；
    # 编辑场景（instance 已有主键）排除自身后再查重，返回清洗后的名称。
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not 2 <= len(name) <= 50:
            raise forms.ValidationError('部门名称长度应在 2-50 个字符之间')
        qs = Department.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('该部门名称已存在')
        return name


# 员工表单：姓名、年龄、手机号、入职时间均做业务校验；手机号唯一性单独处理。
# depart 的可选项受数据范围限制：超级管理员可选全部部门，部门管理员只能选本部门。
class EmployeeForm(forms.ModelForm):
    """员工表单，含姓名长度、年龄范围、手机号正则与唯一性校验。"""

    create_time = forms.DateField(
        label='入职时间',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
    )

    class Meta:
        model = Employee
        fields = ['name', 'age', 'gender', 'account', 'create_time', 'phone', 'depart', 'avatar']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '2-20 个字符'}),
            'age': forms.NumberInput(attrs={'min': 18, 'max': 65}),
            'account': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
            'phone': forms.TextInput(attrs={'placeholder': '11 位手机号', 'maxlength': 11}),
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    # 入参额外支持 user（当前登录用户），用于限定部门下拉范围；
    # 非超级管理员只能选择自己所属部门，无所属部门时下拉为空，防止越权。
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)
        if user and not user.is_superuser:
            # 部门管理员只能选择、只能操作本部门
            if user.depart_id:
                self.fields['depart'].queryset = Department.objects.filter(pk=user.depart_id)
                self.fields['depart'].initial = user.depart
            else:
                self.fields['depart'].queryset = Department.objects.none()

    # 姓名去空格后长度需为 2-20 个字符，返回清洗值
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not 2 <= len(name) <= 20:
            raise forms.ValidationError('姓名长度应在 2-20 个字符之间')
        return name

    # 年龄限定在 18-65 岁的在职区间，超出范围视为非法输入
    def clean_age(self):
        age = self.cleaned_data['age']
        if not 18 <= age <= 65:
            raise forms.ValidationError('年龄必须在 18-65 岁之间')
        return age

    # 手机号先做 11 位正则校验，再查重；编辑时排除当前员工自身，返回清洗后的手机号
    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not PHONE_RE.match(phone):
            raise forms.ValidationError('手机号格式不正确（应为 1 开头的 11 位数字）')
        qs = Employee.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('该手机号已被其他员工使用')
        return phone

    # 入职时间不能是未来日期，与今天相等视为合法
    def clean_create_time(self):
        value = self.cleaned_data['create_time']
        if value > date.today():
            raise forms.ValidationError('入职时间不能晚于今天')
        return value


# 考勤表单：status 不在可提交字段中，由模型根据打卡时间自动推导；
# employee 下拉按当前用户的数据范围过滤，避免跨部门录入。
class AttendanceForm(forms.ModelForm):
    """考勤表单，状态不开放手工选择，由时间自动计算。"""

    check_in = forms.TimeField(
        label='上班时间', required=False,
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        input_formats=['%H:%M', '%H:%M:%S'],
    )
    check_out = forms.TimeField(
        label='下班时间', required=False,
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        input_formats=['%H:%M', '%H:%M:%S'],
    )

    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    # 入参额外支持 user：非超级管理员时，员工下拉只保留其数据范围内的员工
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)
        if user and not user.is_superuser:
            from app01.utils.scope import scope_employees
            self.fields['employee'].queryset = scope_employees(user)

    # 跨字段校验：下班时间不得早于上班时间；同一员工同一天不能重复录入考勤
    def clean(self):
        cleaned = super().clean()
        employee, day = cleaned.get('employee'), cleaned.get('date')
        check_in, check_out = cleaned.get('check_in'), cleaned.get('check_out')
        if check_in and check_out and check_out < check_in:
            self.add_error('check_out', '下班时间不能早于上班时间')
        if employee and day:
            qs = Attendance.objects.filter(employee=employee, date=day)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('date', '该员工当天已存在考勤记录')
        return cleaned


# 薪资表单：total 为计算字段不参与输入，由模型 save() 自动计算；
# employee 下拉同样按当前用户数据范围过滤，月份与金额做格式和范围校验。
class SalaryForm(forms.ModelForm):
    """薪资表单，实发工资由视图/模型计算，不接收用户输入。"""

    class Meta:
        model = Salary
        fields = ['employee', 'month', 'base_salary', 'bonus', 'deduction']
        widgets = {
            'month': forms.TextInput(attrs={'placeholder': '例如：2026-11', 'maxlength': 7}),
            'base_salary': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
            'bonus': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
            'deduction': forms.NumberInput(attrs={'step': '0.01', 'min': 0}),
        }

    # 入参额外支持 user：非超级管理员时，员工下拉只保留其数据范围内的员工
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)
        if user and not user.is_superuser:
            from app01.utils.scope import scope_employees
            self.fields['employee'].queryset = scope_employees(user)

    # 月份必须为 YYYY-MM 且月份在 01-12 之间，返回去除首尾空格后的字符串
    def clean_month(self):
        month = self.cleaned_data['month'].strip()
        if not MONTH_RE.match(month):
            raise forms.ValidationError('月份格式应为 YYYY-MM（例如 2026-11）')
        return month

    # 跨字段校验：同一员工同一月份只能录入一次薪资；三项金额均不得为负数
    def clean(self):
        cleaned = super().clean()
        employee, month = cleaned.get('employee'), cleaned.get('month')
        if employee and month:
            qs = Salary.objects.filter(employee=employee, month=month)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('month', '该员工此月份的薪资已录入')
        for key in ('base_salary', 'bonus', 'deduction'):
            value = cleaned.get(key)
            if value is not None and value < 0:
                self.add_error(key, '金额不能为负数')
        return cleaned


# 公告表单：只接收标题、内容与是否置顶，发布人取当前登录用户、发布时间自动生成。
class NoticeForm(forms.ModelForm):
    """公告表单，发布人与发布时间自动生成。"""

    class Meta:
        model = Notice
        fields = ['title', 'content', 'is_top']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '请输入公告标题'}),
            'content': forms.Textarea(attrs={'rows': 6, 'placeholder': '请输入公告内容'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)

    # 标题去空格后长度需在 2-100 之间，返回清洗值
    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if not 2 <= len(title) <= 100:
            raise forms.ValidationError('标题长度应在 2-100 个字符之间')
        return title

    # 公告正文去空格后至少 5 个字符，防止发布无意义内容
    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if len(content) < 5:
            raise forms.ValidationError('公告内容至少 5 个字符')
        return content


# 任务表单：新增任务由前端 AJAX 提交，字段与模型保持一致；负责人为空时显示占位提示。
class TaskForm(forms.ModelForm):
    """任务表单，供 AJAX 提交复用。"""

    class Meta:
        model = Task
        fields = ['level', 'title', 'detail', 'leader']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '请输入任务标题', 'maxlength': 50}),
            'detail': forms.Textarea(attrs={'rows': 4, 'placeholder': '请输入任务详情'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_style(self)
        self.fields['leader'].empty_label = '请选择负责人'

    # 任务标题去空格后长度需在 2-50 之间（与模型 max_length 对齐）
    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if not 2 <= len(title) <= 50:
            raise forms.ValidationError('任务标题长度应在 2-50 个字符之间')
        return title

    # 任务详情去空格后至少 5 个字符，避免只填标题不填内容
    def clean_detail(self):
        detail = self.cleaned_data['detail'].strip()
        if len(detail) < 5:
            raise forms.ValidationError('任务详情至少 5 个字符')
        return detail
