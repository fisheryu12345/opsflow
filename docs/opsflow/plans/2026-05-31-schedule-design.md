# OpsFlow 调度计划设计

## 背景

OpsFlow 目前仅支持手动执行流程：用户创建 FlowExecution → 点击 Start 立即执行。缺少"在指定的未来时间自动执行"和"按 cron 周期性自动执行"的能力。

需求：在正式执行流程之前，支持三种执行方式：
1. **立即执行** — 已有，手动创建 + start
2. **一次性定时执行** — 指定未来某个时间点自动触发
3. **周期性执行** — 按 cron 表达式自动循环触发

同时需要前端界面可查看调度任务状态、删除、调整。

## 设计方案

### 方案选择

使用 **SchedulePlan 独立模型 + APScheduler** 方案。调度和执行完全解耦，APScheduler 负责到时触发，每次触发自动创建 FlowExecution 并 start。

## 数据模型

### SchedulePlan

```python
class SchedulePlan(models.Model):
    class ScheduleType(models.TextChoices):
        ONE_TIME = 'one_time', '一次性'
        CRON = 'cron', '周期性'

    class Status(models.TextChoices):
        ACTIVE = 'active', '运行中'
        PAUSED = 'paused', '已暂停'
        COMPLETED = 'completed', '已完成'
        EXPIRED = 'expired', '已过期'

    template = ForeignKey(FlowTemplate, CASCADE, related_name='schedule_plans')
    name = CharField(128)                          # 调度名称
    schedule_type = CharField(16)                  # one_time / cron
    scheduled_at = DateTimeField(nullable)         # 一次性定时时间
    cron_expr = CharField(64, blank=True)          # cron 表达式
    cron_description = CharField(128, blank=True)  # cron 可读描述
    timezone = CharField(32, default='Asia/Shanghai')
    is_active = BooleanField(default=True)
    status = CharField(16, default='active')
    max_retries = IntegerField(default=0)           # 调度重试次数
    retry_delay = IntegerField(default=300)         # 重试间隔(秒)
    last_run_at = DateTimeField(nullable)
    next_run_at = DateTimeField(nullable)
    total_run_count = IntegerField(default=0)
    created_by = ForeignKey(User, null=True, PROTECT)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        db_table = 'opsflow_schedule_plan'
        ordering = ['-created_at']
```

**状态转换：**
- `active` ↔ `paused`（暂停/恢复）
- `active` → `completed`（一次性触发完成或手动完成）
- `created` → `expired`（一次性超时未触发）

**关键规则：**
- 每次触发时读取 `template.pipeline_tree` 最新版本
- 模板删除时 CASCADE 删除关联调度
- cron 任务 `max_instances=1`，`coalesce=True`，`misfire_grace_time=900`

## 调度服务

### OpsflowScheduler

复用 stock 模块已有的 APScheduler 模式（`BackgroundScheduler` + `DjangoJobStore`）。

```python
class OpsflowScheduler:
    def start(self):           # 初始化调度器，加载所有 active 计划
    def add_plan(self, plan):  # 添加 job
    def update_plan(self, plan):  # 更新 job
    def remove_plan(self, plan):  # 删除 job
    def pause_plan(self, plan):   # 暂停 job
    def resume_plan(self, plan):  # 恢复 job

    def _execute_plan(self, plan_id):
        """APScheduler 触发回调"""
```

**_execute_plan 逻辑：**
1. 读取 SchedulePlan + template（最新 pipeline_tree）
2. template 是草稿状态 → 跳过执行，记 OpsLog 警告
3. create FlowExecution(template=template, context={pipeline_tree}, created_by=系统)
4. engine = FlowEngine(execution) → engine.start()
5. 更新 plan.last_run_at, total_run_count++
6. 一次性且成功 → status=completed

**Job ID 格式：** `opsflow_schedule_plan_{plan_id}`

**启动方式：** `manage.py start_opsflow_scheduler` 独立进程；开发环境可通过 settings 开关随 `runserver` 启动。

### APScheduler 配置

```python
scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
scheduler.add_jobstore(DjangoJobStore(), 'default')
```

- Cron 任务：`add_job('cron', ... misfire_grace_time=900, coalesce=True, max_instances=1)`
- 一次性任务：`add_job('date', run_date=scheduled_at, ...)`
- Django 重启时扫描 DB 中所有 `is_active=True` 的 plan 恢复注册

## API 端点

### SchedulePlan CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/opsflow/schedule-plans/` | 列表（支持 template、status 筛选） |
| POST | `/api/opsflow/schedule-plans/` | 创建 |
| GET | `/api/opsflow/schedule-plans/{id}/` | 详情 |
| PUT | `/api/opsflow/schedule-plans/{id}/` | 全量更新 |
| PATCH | `/api/opsflow/schedule-plans/{id}/` | 部分更新 |
| DELETE | `/api/opsflow/schedule-plans/{id}/` | 删除 |
| POST | `.../{id}/pause/` | 暂停 |
| POST | `.../{id}/resume/` | 恢复 |
| POST | `.../{id}/trigger/` | 手动立即触发一次 |
| GET | `.../{id}/history/` | 该调度产生的所有 executions |

**输入校验：**
- `one_time` 必须传 `scheduled_at`（且不能是过去时间）
- `cron` 必须传 `cron_expr`
- 同一 template 下名称不重复

**ViewSet 钩子：**
- `perform_create` → `scheduler.add_plan(plan)`
- `perform_update` → `scheduler.update_plan(plan)`
- `perform_destroy` → `scheduler.remove_plan(plan)`
- `pause` action → `scheduler.pause_plan()` + `is_active=False`
- `resume` action → `scheduler.resume_plan()` + `is_active=True`

## 前端设计

### 入口

在模板管理页 (`opsflow-template/index.vue`) 增加 `调度计划` tab，右侧呈现调度表格。

### 组件结构

```
web/src/views/apps/opsflow-template/
├── index.vue                    # 主页面（已有，扩展 tab）
├── components/
│   ├── ScheduleManager.vue      # [新] 调度管理子页面
│   │   ├── ScheduleTable.vue    # [新] 调度计划表格
│   │   └── ScheduleForm.vue     # [新] 新建/编辑调度表单
```

### 调度表格列

名称 / 类型标签（一次性/周期性）/ 触发时间或 cron / 状态标签（带颜色点）/ 上次执行 / 下次执行 / 操作（编辑、暂停/恢复、删除、手动触发）

### 新建调度表单

- 名称（文本输入）
- 类型（radio: 一次性 / 周期性）
- 一次性 → 日期时间选择器
- 周期性 → 频率快捷选择（每天/工作日/每周一/每月1号/自定义 cron）+ 时:分
- 失败重试（次数 + 间隔）
- 频率快捷选择自动转 cron 表达式

### API 层

`web/src/api/opsflow/schedule-plans.ts` — 标准 CRUD + 额外 action 方法。

## RBAC 菜单

在 OpsFlow 主菜单下新增菜单项：
- `opsflow-schedule-plan` → 路由 `/api/opsflow/schedule-plans/`
- 位于"执行记录"之后
- 通过 `add_opsflow_menu.py` 管理命令注册

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 调度触发时 template 被删除 | CASCADE，调度自动移除 |
| 调度触发时 template 是草稿 | 跳过执行，记 OpsLog 警告 |
| 同时触发大量调度 | APScheduler 默认线程池 10 + max_instances=1 控制 |
| 一次性任务错过时间 | misfire_grace_time=900s，超时标记 expired |
| Django 重启调度恢复 | start() 时扫描 DB 重新注册 |
| cron 任务上一次未完成 | coalesce=True + max_instances=1，跳过重叠 |
| 触发 execution 失败 | 按 max_retries 重试，间隔 retry_delay |
| 调度执行频率极高（每分钟） | max_instances=1 防止堆积 |
| 修改调度时正在触发 | APScheduler 的 modify_job 线程安全 |
