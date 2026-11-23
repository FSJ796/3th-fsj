"""演示数据命令：部门、员工、考勤、薪资、公告、任务与测试账号。

用法：python manage.py demo_data
"""
import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from app01.models import (
    Attendance, Department, Employee, Knowledge, Notice, Role, Salary, Task, User,
)
from app01.utils.scope import ROLE_DEPT_ADMIN, ROLE_EMPLOYEE


def month_offset(base, offset):
    """返回 base 往前 offset 个月的 YYYY-MM 字符串。"""
    year, month = base.year, base.month - offset
    while month <= 0:
        month += 12
        year -= 1
    return f'{year:04d}-{month:02d}'


# 演示部门：6 个部门覆盖研发、人事、财务、市场、行政与运营各业务线
DEPARTMENTS = [
    ('技术部', '负责产品研发、系统运维与技术支持'),
    ('人事部', '负责招聘、培训、绩效与员工关系'),
    ('财务部', '负责财务核算、报销审核与资金管理'),
    ('市场部', '负责市场推广、品牌运营与客户拓展'),
    ('行政部', '负责办公环境、固定资产与后勤保障'),
    ('运营部', '负责业务运营、数据分析与客户服务'),
]

# 演示员工：每行为（姓名, 年龄, 性别, 手机号, 所属部门, 入职日期, 账户余额）
# 15 人分布于上述 6 个部门，手机号作为唯一键用于重复执行时避免重复插入
EMPLOYEES = [
    ('张伟', 28, '男', '13800000001', '技术部', '2023-03-01', Decimal('1200.00')),
    ('李娜', 26, '女', '13800000002', '技术部', '2023-07-10', Decimal('800.00')),
    ('王强', 32, '男', '13800000003', '技术部', '2021-05-20', Decimal('2500.00')),
    ('刘敏', 30, '女', '13800000004', '人事部', '2022-09-01', Decimal('1600.00')),
    ('陈晨', 27, '女', '13800000005', '人事部', '2024-02-18', Decimal('600.00')),
    ('赵磊', 35, '男', '13800000006', '财务部', '2020-06-15', Decimal('3200.00')),
    ('周静', 31, '女', '13800000007', '财务部', '2021-11-08', Decimal('1800.00')),
    ('吴昊', 29, '男', '13800000008', '市场部', '2023-12-01', Decimal('900.00')),
    ('许晴', 24, '女', '13800000009', '技术部', '2025-04-07', Decimal('300.00')),
    ('孙悦', 25, '女', '13800000010', '行政部', '2024-08-12', Decimal('500.00')),
    ('郑凯', 34, '男', '13800000011', '行政部', '2021-02-22', Decimal('2100.00')),
    ('冯雪', 28, '女', '13800000012', '运营部', '2023-05-15', Decimal('1100.00')),
    ('何军', 33, '男', '13800000013', '运营部', '2022-01-10', Decimal('2400.00')),
    ('马超', 31, '男', '13800000014', '市场部', '2020-10-26', Decimal('2900.00')),
    ('林芳', 29, '女', '13800000015', '财务部', '2022-12-05', Decimal('1500.00')),
]

# 演示公告：每行为（标题, 正文, 是否置顶），标题作为唯一键判重
NOTICES = [
    ('关于 11 月考勤打卡规范的通知', '全体员工请于每日 09:00 前完成上班打卡，18:00 后完成下班打卡。因公外出需提前在部门负责人处报备。', True),
    ('11 月薪资发放安排', '本月薪资将于 11 月 15 日发放至员工账户，如有疑问请联系财务部。', True),
    ('年度免费体检预约通知', '公司年度体检已开放预约，请各位同事于本月底前登录人事系统选择体检机构与时间。', False),
    ('技术部周例会时间调整', '原定周一上午的技术部周例会调整为每周二 10:00，会议地点不变。', False),
    ('关于开展消防应急演练的通知', '本周五下午 15:00 组织全员消防应急演练，请各部门提前安排好工作，听到警报后按指定路线有序疏散。', False),
    ('新员工入职培训安排', '本月新入职员工培训定于 11 月 20 日 14:00 在三楼会议室举行，请相关同事准时参加。', False),
    ('公司年会节目征集通知', '2027 年公司年会节目现开始征集，各部门请于 12 月 10 日前提交节目名称与参演人员名单。', False),
]


class Command(BaseCommand):
    help = '写入演示数据与测试账号（可重复执行）'

    @transaction.atomic
    def handle(self, *args, **options):
        # 整体放在一个事务中；各步骤均用 get_or_create 或 exists 判重，保证命令可重复执行（幂等）
        # 1. 部门：以部门名称为唯一键，已存在则复用
        depart_map = {}
        for name, desc in DEPARTMENTS:
            department, _ = Department.objects.get_or_create(name=name, defaults={'desc': desc})
            depart_map[name] = department
        self.stdout.write(f'部门：{len(depart_map)} 个')

        # 2. 员工：以手机号判重，已存在则不覆盖；同时按姓名缓存以便后续关联账号
        employee_map = {}
        for name, age, gender, phone, dept_name, join_date, account in EMPLOYEES:
            employee, created = Employee.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'age': age,
                    'gender': gender,
                    'depart': depart_map[dept_name],
                    'create_time': date.fromisoformat(join_date),
                    'account': account,
                },
            )
            employee_map[name] = employee
        self.stdout.write(f'员工：{Employee.objects.count()} 人')

        # 3. 测试账号：部门管理员 manager（技术部）与普通员工 emp001
        # 密码仅在首次创建时设置；角色绑定每次执行都重新 set，避免角色被改动后残留
        manager, created = User.objects.get_or_create(
            username='manager',
            defaults={'depart': depart_map['技术部'], 'phone': '13900000001'},
        )
        if created:
            manager.set_password('manager123')
            manager.save()
        manager.roles.set([Role.objects.get(name=ROLE_DEPT_ADMIN)])

        employee_user, created = User.objects.get_or_create(
            username='emp001',
            defaults={'depart': depart_map['技术部'], 'phone': '13800000001'},
        )
        if created:
            employee_user.set_password('emp123')
            employee_user.save()
        employee_user.roles.set([Role.objects.get(name=ROLE_EMPLOYEE)])

        # 将员工“张伟”与 emp001 账号一对一绑定，使普通员工登录后只能看到自己的数据
        zhang_wei = employee_map['张伟']
        zhang_wei.user = employee_user
        zhang_wei.save(update_fields=['user'])
        self.stdout.write('账号：manager / manager123，emp001 / emp123')

        # 4. 近 10 个工作日考勤：从今天向前回溯，跳过周六周日，凑满 10 个工作日
        today = date.today()
        workdays = []
        cursor = today
        while len(workdays) < 10:
            if cursor.weekday() < 5:
                workdays.append(cursor)
            cursor -= timedelta(days=1)

        attendance_count = 0
        for employee in Employee.objects.all():
            for day in workdays:
                # 先判断该员工当天是否已有记录，避免重复执行时插入重复考勤
                if Attendance.objects.filter(employee=employee, date=day).exists():
                    continue
                # 按随机概率模拟缺卡、早到、正常、迟到、早退等不同出勤情况
                roll = random.random()
                if roll < 0.08:
                    check_in, check_out = None, None
                elif roll < 0.25:
                    check_in, check_out = time(8, 40 + random.randint(0, 15)), time(18, random.randint(5, 30))
                elif roll < 0.40:
                    check_in, check_out = time(9, random.randint(1, 20)), time(18, random.randint(5, 40))
                elif roll < 0.55:
                    check_in, check_out = time(8, 45 + random.randint(0, 10)), time(17, random.randint(20, 50))
                else:
                    check_in, check_out = time(8, 50 + random.randint(0, 9)), time(18, random.randint(0, 20))
                Attendance.objects.create(employee=employee, date=day, check_in=check_in, check_out=check_out)
                attendance_count += 1
        self.stdout.write(f'考勤：新增 {attendance_count} 条')

        # 5. 近 6 个月薪资：offset 从 5 递减到 0，即最早月份到当前月依次生成
        salary_count = 0
        for offset in (5, 4, 3, 2, 1, 0):
            month = month_offset(today, offset)
            for employee in Employee.objects.all():
                # 同一员工同月只保留一条薪资记录，已存在则跳过
                if Salary.objects.filter(employee=employee, month=month).exists():
                    continue
                # 底薪、奖金、扣款均随机取值，便于统计图表呈现差异
                base = Decimal(random.choice([6000, 7000, 8000, 9000, 10000]))
                bonus = Decimal(random.choice([0, 300, 500, 800, 1200]))
                deduction = Decimal(random.choice([0, 0, 100, 200, 350]))
                Salary.objects.create(
                    employee=employee, month=month, base_salary=base,
                    bonus=bonus, deduction=deduction,
                )
                salary_count += 1
        self.stdout.write(f'薪资：新增 {salary_count} 条')

        # 6. 公告：发布人为超级管理员 fsj（未初始化时为 None），按标题判重
        admin = User.objects.filter(username='fsj').first()
        notice_count = 0
        for title, content, is_top in NOTICES:
            _, created = Notice.objects.get_or_create(
                title=title, defaults={'content': content, 'is_top': is_top, 'publisher': admin},
            )
            notice_count += 1 if created else 0
        self.stdout.write(f'公告：新增 {notice_count} 条')

        # 7. 任务：每行为（优先级, 标题, 详情, 负责人），标题判重
        task_rows = [
            ('紧急', '修复薪资报表月份筛选异常', '部分历史月份筛选结果为空，需排查查询条件并补充回归测试。', admin),
            ('重要', '完成 11 月员工考勤汇总', '汇总技术部 11 月考勤数据，统计迟到、早退与缺勤人数。', manager),
            ('普通', '更新员工通讯录', '核对各部门员工手机号与所属部门信息，及时更新变更记录。', manager),
            ('紧急', '数据库备份策略整改', '现有备份仅保留 7 天，需调整为每日全量 + 归档 30 天，并验证恢复流程。', admin),
            ('重要', '组织第四季度绩效考核', '通知各部门负责人于 12 月 5 日前完成下属绩效评分并提交人事部汇总。', manager),
            ('普通', '员工档案电子化归档', '将 2025 年以前的纸质员工档案扫描归档，按部门建立电子目录。', manager),
        ]
        task_count = 0
        for level, title, detail, leader in task_rows:
            _, created = Task.objects.get_or_create(
                title=title, defaults={'level': level, 'detail': detail, 'leader': leader},
            )
            task_count += 1 if created else 0
        self.stdout.write(f'任务：新增 {task_count} 条')

        # 8. 制度知识库（T3）：供 AI 问答检索的预置条目，按标题判重，重复执行不会重复插入
        knowledge_rows = [
            ('考勤管理制度', '员工每个工作日需在 09:00 前完成上班打卡，18:00 后完成下班打卡。'
             '09:00 之后打卡记为迟到，18:00 之前下班记为早退，全天未打卡记为缺勤。'
             '因公外出或出差无法打卡的，需提前向部门负责人报备，由人事部补登记为按时。'),
            ('请假申请流程', '请假需提前在部门负责人处提交申请：事假 1 天以内由部门负责人审批，'
             '超过 1 天需人事部复核；病假需提供医院证明；年假按工龄每年 5-15 天，需提前一周申请。'
             '请假期间考勤由人事部标记，不计为缺勤。'),
            ('费用报销制度', '报销需在费用发生后 30 天内提交，附正规发票与费用明细。'
             '单笔 500 元以下由部门负责人审批，500 元以上需财务部复核。'
             '每月 25 日集中打款，报销款随当月工资或单独转账发放。'),
            ('加班与调休规定', '加班需提前申请并经部门负责人批准。工作日加班按 1.5 倍计酬或兑换调休，'
             '周末加班按 2 倍计酬或兑换调休，法定节假日按 3 倍计酬。调休有效期为加班后 6 个月内。'),
            ('薪资发放说明', '公司每月 15 日发放上月工资，遇节假日顺延至下一工作日。'
             '实发工资 = 基本工资 + 奖金 - 扣款，扣款包含迟到、早退及事假扣款。'
             '工资条由财务部通过系统下发，如有疑问请在 3 个工作日内联系财务部核对。'),
            ('新员工入职指引', '新员工入职当天需携带身份证、学历证明与银行卡，到人事部签订劳动合同并开通系统账号。'
             '试用期一般为 3 个月，入职第一周安排部门导师带教，入职培训每月集中组织一次。'),
            ('差旅与出差标准', '出差需提前提交出差申请。住宿标准：一线城市每人每晚不超过 400 元，'
             '其他城市不超过 300 元；城际交通优先选择高铁二等座；出差补贴每人每天 100 元，随报销一并发放。'),
            ('保密与信息安全规定', '员工不得向外部泄露公司客户资料、薪资数据与源代码。'
             '办公电脑须设置锁屏密码，离开工位及时锁屏；系统账号不得转借他人使用，离职当天由人事部统一停用账号。'),
        ]
        knowledge_count = 0
        for title, content in knowledge_rows:
            _, created = Knowledge.objects.get_or_create(
                title=title, defaults={'content': content},
            )
            knowledge_count += 1 if created else 0
        self.stdout.write(f'知识库：新增 {knowledge_count} 条')

        self.stdout.write(self.style.SUCCESS('demo_data 演示数据写入完成'))
