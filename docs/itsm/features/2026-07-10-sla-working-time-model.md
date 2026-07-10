# SLA Working Time Model — 工作时间模型

> 提交: c15e9353 | 日期: 2026-07-10
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

OpsFlow ITSM 原有 SLA 引擎使用纯自然时间计算截止时间（`now + timedelta(minutes=N)`），不支持工作时间/假期/加班的概念。周五 17:30 来的 P1 工单会在周五 18:30 超时 — 但此时已下班。

BK-ITSM 有成熟的三层工作时间模型（Schedule → Day → Duration），本功能将其完整引入 OpsFlow ITSM。

同时修复两个已有缺陷：
1. `SlaEngine.start_ticket_sla()` 中 `response_minutes`/`resolve_minutes` 变量名互换
2. `EscalationLevel` 升级动作已定义但未接入引擎

## 实现方案

### 数据模型：Schedule → Day → Duration

```
Schedule (排班表)
├── name, name_en, project(FK nullable), is_builtin
├── days: M2M → Day (NORMAL — 常规工作日)
├── workdays: M2M → Day (WORKDAY — 加班日)
└── holidays: M2M → Day (HOLIDAY — 节假日)

Day (日期定义)
├── name, name_en
├── type_of_day: NORMAL | WORKDAY | HOLIDAY
├── day_of_week: "0,1,2,3,4" (NORMAL 用)
├── start_date / end_date (WORKDAY/HOLIDAY 用)
└── durations: M2M → Duration

Duration (工作时间段)
├── name, name_en
├── start_time: 09:00:00
└── end_time: 12:00:00
```

**内置种子数据：** "5×8 标准"（Mon-Fri 08-12/14-18）和 "7×24"（全天候）。

**SlaPolicy 重构：** schedule FK(PROTECT) + response/resolve time+unit 替换原 minutes + escalation_levels M2M。

### SlaTime 引擎 — 核心算法

`backend/itsm/services/sla_time.py` 实现三层计算：

1. **TimeDelta** — 单区间，支持 `intersection`/`difference`/`union` 集合运算
2. **MultiTimeDelta** — 多区间代数，支持 `difference`/`union` 批量运算 + `closest_td_time` 边界查找
3. **SlaTime** — 核心计算器：

```python
class SlaTime:
    def date_time_deltas(self, date) -> [TimeDelta]:
        """三步：NORMAL 匹配 → 假期裁剪 → 加班补充"""
        
    def sla_time(self, start, end) -> int:
        """两 datetime 间的有效 SLA 秒数"""
        
    def sla_deadline(self, start_time, sla_seconds) -> datetime:
        """工作日历化截止时间 — 逐日推进 consuming working seconds"""
```

**关键算法设计决策：**

- `date_time_deltas()` 使用 `days - holidays + workdays` 三重逻辑（非单表 M2M + type 字段），三个独立 M2M 让 Django 查询更清晰
- `sla_deadline()` 逐日推进非一次求解，自然处理跨周末/假期边界
- SlaTime 构造时预拉取 Schedule → Day → Duration 到 indexed dict，避免 N+1 查询

### SlaEngine 改造

`backend/itsm/services/sla_engine.py` 五处变更：

| 方法 | 改动 |
|------|------|
| `start_ticket_sla()` | 用 SlaTime 替代 timedelta + swap 修复 + total_seconds/begin_at 固化 |
| `pause_ticket_sla()` | 记录 cost_time（有效 SLA 秒数）替代简单暂停 |
| `resume_ticket_sla()` | 用 remaining = total_seconds - cost_time 重新计算 deadline |
| `check_all_active_sla()` | 每轮先 update_cost_time() 再评估升级 |
| `_execute_escalation()` | 查询 EscalationLevel 按 level 升序执行动作 |

### 升级动作执行

```python
def _execute_escalation(ticket, sla_task):
    levels = sla_task.sla_policy.escalation_levels.order_by('level')
    for level in levels:
        if sla_task.cost_time >= level.timeout_minutes * 60:
            if level.action == 'notify_only': ...
            elif level.action == 'transfer_leader': ...
            elif level.action == 'transfer_next': ...
            elif level.action == 'notify_users': ...
```

### Swap Bug 修复

原代码（有误）：
```python
handle_deadline = now + timedelta(minutes=policy.response_minutes)  # 应该是 resolve
reply_deadline = now + timedelta(minutes=policy.resolve_minutes)    # 应该是 response
```

修复后：
```python
resolve_secs = policy.resolve_seconds  # response_time → reply_deadline
response_secs = policy.response_seconds  # resolve_time → deadline
deadline = sla_calc.sla_deadline(now, resolve_secs)
reply_deadline = sla_calc.sla_deadline(now, response_secs)
```

### 前端组件

| 组件 | 作用 |
|------|------|
| `ScheduleList.vue` | 排班表列表（表格 + 新建/编辑/删除，is_builtin 禁止删除） |
| `ScheduleEdit.vue` | 编辑对话框（3 tab: 工作日/加班日/节假日，每 tab 含 Day + Duration CRUD） |
| `ScheduleDayList.vue` | Day 列表子组件（含 Duration 展开编辑） |
| `HolidayCalendar.vue` | 假期日期范围选择器（el-date-picker） |
| `SlaPolicyList.vue`(改) | schedule 下拉 + time/unit 字段 + escalation_levels 多选 + 创建按钮 |

### i18n 冲突解决

发现 `opsflow/zh-cn.ts` 和 `integration/zh-cn.ts` 也有 `schedule` key，Object.assign 浅合并导致 ITSM 的 `schedule` 被覆盖。解决方案：重命名为 `slaSchedule`（4 个组件 33 处引用同步修改）。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/schedule.py` | Duration/Day/Schedule 模型 (152行) |
| `backend/itsm/models/catalog.py` | SlaPolicy 重构 — schedule FK + time/unit + escalation_levels (82行) |
| `backend/itsm/models/sla.py` | SlaTask 新增 cost_time/total_seconds/begin_at |
| `backend/itsm/services/sla_time.py` | TimeDelta/MultiTimeDelta/SlaTime 引擎 (410行) |
| `backend/itsm/services/sla_engine.py` | SlaTime 集成 + EscalationLevel 接入 + swap fix (204行变更) |
| `backend/itsm/tests/test_sla_time.py` | 29 个测试 — TimeDelta/SlaTime/SlaEngine/Escalation/SwapBug |
| `backend/itsm/migrations/0005_sla_working_time.py` | 19步迁移 — 建表→种子→数据迁移→约束变更 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 新增 schedule tab (key=schedule, sort=80) |
| `web/.../components/ScheduleList.vue` | 排班表列表页 |
| `web/.../components/ScheduleEdit.vue` | 排班编辑对话框 (含 Day CRUD) |
| `web/.../components/SlaPolicyList.vue` | SLA 策略编辑改造 |

## 使用方式

1. **配置排班表：** ITSM → 排班表 tab → 新建（可选全局或项目级）
2. **配置 SLA 策略：** ITSM → SLA tab → 新建策略 → 选择排班表 + 设置响应/解决时限
3. **配置升级：** ITSM → 升级 tab → 创建升级级别（通知/转组长/升级/通知指定用户）
4. **绑定到 SLA 策略：** 在策略编辑中选择升级级别
5. **创建工单后：** 系统根据策略的排班表自动计算工作时间下的截止时间
6. **升级触发：** 每分钟检查一次，cost_time 超阈值自动执行升级动作

### 关联文档

- 设计规格: [2026-07-10-sla-working-time-model-design.md](../../superpowers/specs/2026-07-10-sla-working-time-model-design.md)
