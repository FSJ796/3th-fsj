# 企业员工管理系统 HRMS

基于 Django 5.2 + MySQL 的企业员工管理系统课程设计项目，包含部门、员工、考勤、薪资、公告、任务、RBAC 权限、ECharts 数据统计，以及接入大模型（SiliconFlow）的 AI 智能助手与全站浮窗。

- 仓库地址：https://github.com/FSJ796/3th-fsj
- 详细设计文档：[PROJECT.md](./PROJECT.md)

---

## 一、技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Python 3.10 · Django 5.2.7 |
| 数据库 | MySQL 8.x（默认）/ SQLite（`DB_ENGINE=sqlite` 切换） |
| 数据库驱动 | PyMySQL 1.1.1 · cryptography |
| 前端 | Bootstrap 3 · jQuery 3.6 · ECharts 5 |
| 图像 | Pillow 10.4（图片验证码、员工头像） |
| 大模型 | OpenAI 兼容 SDK · SiliconFlow · `Qwen/Qwen2.5-7B-Instruct` |
| 权限 | 自研 RBAC（User → Role → Permission） |
| 认证 | Django auth + 图片验证码 + Session |

---

## 二、功能清单

### 基础业务模块

| 模块 | 主要功能 |
|------|---------|
| 登录认证 | 用户名密码登录、4 位图形验证码、会话保持、未登录拦截 |
| 部门管理 | 列表、新增、编辑、删除（部门下有员工时禁止删除） |
| 员工管理 | 列表、搜索、分页、新增、编辑、删除、头像上传 |
| 考勤管理 | 打卡记录增删改查，状态按上下班时间自动判定（按时/迟到/早退/缺勤） |
| 薪资管理 | 按月录入基本工资、奖金、扣款，实发工资自动计算 |
| 公告管理 | 发布公告、置顶切换、列表展示 |
| 任务管理 | AJAX 异步新增与删除，紧急/重要/普通三档级别 |
| 用户与角色 | 用户分配角色、角色分配权限、按钮级权限控制 |
| 数据统计 | ECharts 部门人数分布、各月薪资趋势，AJAX 取数 |

### 大模型必做任务（T1–T4）

| 编号 | 要求 | 实现 |
|------|------|------|
| T1 | 大模型接入封装 | `app01/utils/ai.py` 的 `LLMClient.chat()`，从环境变量读取 Key/地址/模型，30 秒超时 |
| T2 | 招聘 JD 生成 | 输入岗位名称，AJAX 调用模型返回岗位职责、任职要求、薪资范围等结构化内容 |
| T3 | 知识库问答 | 新增 `Knowledge` 模型，SQL 关键词检索后注入提示词；无资料直接回答“不知道” |
| T4 | 数据智能点评 | 读取员工某月考勤与薪资数据，生成一句中文点评，遵守数据权限 |

### 智能体浮窗

全站右下角固定入口，登录且具有 `ai_view` 权限的用户可见。支持制度问答、参考资料展示、回车发送与加载中状态，模板位于 `app01/templates/ai/widget.html`，通过 `base.html` 的 `{% include %}` 注入所有页面。

---

## 三、目录结构

```
qiyeguanlixitong/
├── app01/
│   ├── management/commands/   # init_data 初始化权限角色 / demo_data 演示数据
│   ├── middleware/            # auth.py 登录拦截
│   ├── migrations/            # 0001_initial、0002_knowledge
│   ├── static/                # Bootstrap / jQuery / ECharts / hrms.css
│   ├── templates/             # 24 个页面模板（含 ai/index.html、ai/widget.html）
│   ├── templatetags/rbac.py   # 模板内权限判断标签
│   ├── utils/                 # ai / prompts / captcha / pagination / scope
│   ├── views/                 # 12 个视图模块
│   ├── admin.py               # Django 后台注册
│   ├── forms.py               # ModelForm 表单与校验
│   ├── models.py              # 9 个业务模型
│   └── urls.py                # 37 条路由
├── hrms/
│   ├── settings.py            # 数据库、时区、静态资源、大模型环境变量
│   └── urls.py
├── manage.py
├── requirements.txt
├── PROJECT.md                 # 详细设计文档
└── README.md                  # 本文件
```

---

## 四、数据模型

共 9 个模型，定义于 `app01/models.py`：

| 模型 | 说明 |
|------|------|
| `Department` | 部门，名称唯一；被员工以 `PROTECT` 引用 |
| `Permission` | 权限项，`code` 唯一，如 `employee_add` |
| `Role` | 角色，与权限多对多 |
| `User` | 继承 `AbstractUser`，扩展手机号、所属部门、角色 |
| `Employee` | 员工档案，手机号唯一，可一对一关联登录账号 |
| `Attendance` | 考勤，同一员工同一天唯一，`save()` 自动计算状态 |
| `Salary` | 薪资，同一员工同一月唯一，`save()` 自动计算实发 |
| `Notice` | 公告，支持置顶 |
| `Task` | 任务，三档级别，AJAX 新增 |
| `Knowledge` | 企业制度知识库，供 AI 问答检索 |

---

## 五、RBAC 权限设计

```
用户 User ──多对多──> 角色 Role ──多对多──> 权限 Permission(code)
```

- `User.permission_codes()` 返回当前用户权限编码集合，超级管理员取全量；结果缓存在实例上，同一请求不重复查库。
- `@perm_required('employee_add')` 装饰器拦截无权限请求。
- `templatetags/rbac.py` 在模板中控制按钮显隐。
- 数据范围：`utils/scope.py` 让普通员工只能看到自己的考勤与薪资。

内置角色：

| 角色 | 权限数量 | 说明 |
|------|---------|------|
| 超级管理员 | 24 | 全部权限 |
| 部门管理员 | 16 | 本部门员工、考勤、薪资等业务权限 |
| 普通员工 | 5 | 只读查看本人数据与 AI 助手 |

---

## 六、AI 智能助手实现

### 配置方式 A：PowerShell 临时环境变量

API Key 不写入代码、不提交 Git，仅在当前窗口生效：

```powershell
$env:AI_API_KEY  = "你的_Key"
$env:AI_BASE_URL = "https://api.siliconflow.cn/v1"
$env:AI_MODEL    = "Qwen/Qwen2.5-7B-Instruct"

.\.venv\Scripts\python.exe manage.py runserver
```

`settings.py` 读取方式：

```python
AI_API_KEY  = os.environ.get('AI_API_KEY', '')
AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.siliconflow.cn/v1')
AI_MODEL    = os.environ.get('AI_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
```

### 知识库问答流程

1. 问题去标点后生成 2–4 字 n-gram 关键词，过滤“怎么/什么/如何”等停用词。
2. 先整句模糊匹配 `Knowledge` 标题与正文；无命中再按关键词 OR 查询，按命中数量排序取前 5 条。
3. 命中结果拼成上下文，注入 `QA_SYSTEM` 提示词，要求“只能根据资料回答”。
4. 无检索结果时**不调用模型**，直接返回“不知道”。
5. 模型欠费、超时或网络异常时，降级为直接返回最相关制度的原文，避免已知问题也提示失败。

### 相关文件

| 文件 | 作用 |
|------|------|
| `app01/utils/ai.py` | `LLMClient` 封装，懒加载客户端、30 秒超时 |
| `app01/utils/prompts.py` | JD、问答、薪资点评三类提示词 |
| `app01/views/ai.py` | 检索、问答、JD、点评、浮窗聊天接口 |
| `app01/templates/ai/index.html` | AI 助手主页（三个 Tab） |
| `app01/templates/ai/widget.html` | 全站右下角智能体浮窗 |

---

## 七、快速开始

### 1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置数据库

默认连接 MySQL（库名 `hrms`），可用环境变量覆盖：

```powershell
$env:DB_NAME     = "hrms"
$env:DB_USER     = "root"
$env:DB_PASSWORD = "你的密码"
$env:DB_HOST     = "127.0.0.1"
$env:DB_PORT     = "3306"
```

无需 MySQL 时可切换 SQLite：

```powershell
$env:DB_ENGINE = "sqlite"
```

### 3. 迁移与初始化

```powershell
python manage.py migrate
python manage.py init_data    # 权限、角色、超级管理员
python manage.py demo_data    # 演示数据（可重复执行）
```

### 4. 启动

```powershell
python manage.py runserver
```

访问 http://127.0.0.1:8000/ 。

---

## 八、演示账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `fsj` | `fsj123` | 超级管理员 |
| `manager` | `manager123` | 部门管理员（技术部） |
| `emp001` | `emp123` | 普通员工（绑定员工张伟） |

---

## 九、演示数据

执行 `python manage.py demo_data` 后默认包含：

- 6 个部门、15 名员工
- 近 10 个工作日考勤 225 条
- 近 6 个月薪资 90 条
- 7 条公告、6 条任务
- 8 条企业制度知识库（考勤、请假、报销、加班、薪资、入职、差旅、保密）

知识库内容维护在 `app01/management/commands/demo_data.py` 的 `knowledge_rows`，实际数据存于数据库表 `app01_knowledge`。

---

## 十、主要接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/login/` | GET/POST | 登录 |
| `/captcha/` | GET | 图形验证码 |
| `/stats/department-data/` | GET | 部门人数统计 JSON |
| `/stats/salary-data/` | GET | 薪资趋势 JSON |
| `/ai/` | GET | AI 助手页面 |
| `/ai/jd/` | POST | 生成招聘 JD |
| `/ai/qa/` | POST | 制度知识库问答 |
| `/ai/comment/` | POST | 薪资考勤智能点评 |
| `/ai/chat/` | POST | 智能体浮窗聊天 |

---

## 十一、注意事项

- 请勿把 API Key 写入代码或提交到仓库，统一使用环境变量方式 A。
- 若 SiliconFlow 返回 `402 - account balance is insufficient`，表示账户余额不足，需要充值或更换有额度的 Key。
- `Knowledge` 暂未注册到 Django 后台，如需网页维护可先注册 `admin.py`。
