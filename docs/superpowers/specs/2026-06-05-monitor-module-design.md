# Monitor Module Design — OpsFlow 监控告警中心

> 基于 bk-monitor-master 架构参考，推倒重写 opsflow 当前 monitor 模块。
> 参考 bk-monitor 的四层策略模型、FTA 故障自愈引擎、告警管道设计。
> 与现有 OpsFlow 体系通过 SPI 适配器层松耦合集成。

---

## 1. 架构总览

### 1.1 四层架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Frontend (Vue3 / Element Plus)                     │
│  AlertCenter │ StrategyEditor │ DutyCalendar │ Dashboard             │
│  NotifyGroup │ ShieldPlan     │ FTAConfig    │ IncidentView          │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ REST API (DetailResponse / ErrorResponse)
┌───────────────────────────▼──────────────────────────────────────────┐
│                      API Layer (ViewSets)                            │
│  MonitorStrategyVS │ MonitorItemVS │ AlertVS │ AlertEventVS          │
│  NotifyGroupVS     │ DutyPlanVS    │ ShieldPlanVS │ ActionPluginVS   │
│  AlertAssignGroupVS │ CollectConfigVS │ DashboardVS                  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                   Alert Pipeline (Alarm Backends)                     │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐  │
│  │ Event    │→ │ Strategy │→ │ Alert    │→ │ Converge │→ │Action │  │
│  │ Ingest   │  │ Match    │  │ Build    │  │ & Shield │  │Dispatch│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └───────┘  │
│       │              │              │            │            │       │
│  ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐  ┌───▼────┐  ┌───▼────┐  │
│  │Webhook  │   │Algorithm  │  │Alert    │  │Shield  │  │Notify  │  │
│  │Receiver │   │Engine     │  │DB       │  │Cache   │  │Adapter │  │
│  └─────────┘   └───────────┘  └─────────┘  └────────┘  └────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                   SPI Adapter Layer (插件式)                          │
│                                                                       │
│  BaseDataSourceAdapter     BaseNotifyAdapter    BaseActionAdapter     │
│       │                          │                      │             │
│  ┌────┴──────┐            ┌──────┴──────┐       ┌──────┴──────┐      │
│  │Prometheus │            │Integration  │       │OpsFlow     │      │
│  │InfluxDB   │            │Hub          │       │Trigger     │      │
│  │自建采集Push│            │WeCom/Ding   │       │AWX/Tower   │      │
│  └───────────┘            │Email/SMS    │       │ITSM Ticket │      │
│                           └─────────────┘       └─────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                    Integration Hub (现有复用)                         │
│  ConnectorDefinition │ ConnectorInstance │ ConnectorCredential        │
│  AES-256 加密凭据     │ 健康检查           │ JSON Schema 配置表单      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 调度方式

管道采用 **APScheduler** 驱动，不引入 Celery：

```
Django 进程
├── OpsflowScheduler (已有)
│    ├── 流程定时触发
│    ├── 超时检查 (10s)
│    └── 空间清理
│
└── MonitorScheduler (新增)
     ├── 待处理事件消费 (由 webhook push 触发，用 Redis List 做轻量队列)
     ├── 告警升级检查 (60s)
     ├── 静默/屏蔽生效 (60s)
     ├── 自动恢复检测 (300s)
     └── 告警事件清理 (3600s)
```

**Webhook 到管道的触发路径：**
```
Grafana/Prometheus Webhook POST → Django View
  → AlertEvent 落库 (status='pending')
  → Redis List LPUSH event_id
  → APScheduler 秒级轮询 BRPOP
  → 进入管道处理
```

### 1.3 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| AlertEvent 和 Alert 分离 | 两张独立表 | 原始事件用于审计/回溯，Alert 是收敛后的可操作实体 |
| CMDB 关联 | 只存字符串 ID | 避免模型 ForeignKey 紧耦合，通过 SPI 解析 |
| severity 类型 | 整数 1/2/3 | 比较排序方便，致命>预警>提醒 |
| 策略模型 | 四层 (Strategy→Item→QueryConfig→Detect→Algorithm) | 对标 bk-monitor，层间松耦合，独立扩展 |
| 通知+值班 | 同一模型体系 | 一条规则同时承载"通知谁"和"值班怎么排" |
| 动作插件 | 独立模型 (ActionPlugin) | 可动态注册类型，不写死通知/脚本/流程触发 |
| Adapter 加载 | settings 配置类路径 + 运行时反射 | 无需注册中心，简单可靠 |

---

## 2. 数据模型

### 2.1 策略与检测体系

#### MonitorStrategy — 策略

| 字段 | 类型 | 说明 |
|------|------|------|
| id | AutoField | 主键 |
| name | CharField(128) | 策略名称, db_index |
| bk_biz_id | IntegerField | 业务ID, db_index |
| scenario | CharField(32) | 监控场景 (host/service/custom) |
| source | CharField(32) | 来源系统, default='monitor' |
| type | CharField(12) | 策略类型: monitor/fta/dashboard |
| is_enabled | BooleanField | 是否启用, default=True |
| is_invalid | BooleanField | 是否失效, default=False |
| invalid_type | CharField(32) | 失效类型 |
| priority | IntegerField | 优先级, null=True |
| priority_group_key | CharField(64) | 优先级分组, null=True |
| create_user | CharField(32) | |
| create_time | DateTimeField | auto_now_add |
| update_user | CharField(32) | |
| update_time | DateTimeField | auto_now |

#### MonitorItem — 监控项

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | FK→MonitorStrategy | 关联策略, db_index |
| name | CharField(256) | 监控项名称 |
| expression | TextField | 计算公式 |
| origin_sql | TextField | 原始查询语句 |
| no_data_config | JSONField | 无数据配置, default=dict |
| target | JSONField | 监控目标表达式, default=list |
| meta | JSONField | 查询配置元数据, default=list |
| metric_type | CharField(32) | 指标类型, default='' |
| time_delay | IntegerField | 策略等待时间(秒), default=0 |

#### MonitorQueryConfig — 查询配置

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | FK→MonitorStrategy | 关联策略, db_index |
| item_id | FK→MonitorItem | 关联监控项, db_index |
| alias | CharField(12) | 别名 |
| data_source_label | CharField(32) | 数据来源标签: prometheus/influxdb/custom |
| data_type_label | CharField(32) | 数据类型标签: metric/event/log |
| metric_id | CharField(128) | 指标ID |
| config | JSONField | 查询配置 (promql/agg_interval等) |

#### MonitorDetectConfig — 检测配置

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | FK→MonitorStrategy | 关联策略, db_index |
| item_id | FK→MonitorItem | 关联监控项, db_index |
| level | IntegerField | 告警级别: 1=致命 2=预警 3=提醒 |
| expression | TextField | 计算公式, default='' |
| trigger_config | JSONField | 触发条件, default=dict (count=N/percentage=P) |
| recovery_config | JSONField | 恢复条件, default=dict |
| connector | CharField(4) | 同级别算法连接符: and/or, default='and' |

#### MonitorAlgorithmConfig — 算法配置

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | FK→MonitorStrategy | 关联策略 |
| item_id | FK→MonitorItem | 关联监控项 |
| level | IntegerField | 告警级别 |
| type | CharField(64) | 算法类型, db_index |
| config | JSONField | 算法配置参数 |

**支持的算法类型：**

| 算法 | 适用场景 | 核心参数 |
|------|---------|---------|
| Threshold | CPU>90% | method(gt/lt/gte/lte), threshold |
| SimpleRingRatio | 流量突增 | ratio(浮点), floor(下限) |
| AdvancedRingRatio | 带基线环比 | ratio, floor, refer_duration(参考窗口) |
| SimpleYearRound | 同比昨天 | ratio, floor |
| AdvancedYearRound | 同比上周 | ratio, floor, refer_period |
| YearRoundAmplitude | 波动幅度异常 | threshold |
| IntelligentDetect | 智能异常检测 | sensitivity, use_sdk(bool) |
| TimeSeriesForecasting | 时序预测 | forecast_window, confidence |
| PartialNodes | 集群节点失联 | min_count, percentage |
| OsRestart | 主机重启检测 | — |

#### MonitorStrategyLabel — 策略标签

| 字段 | 类型 | 说明 |
|------|------|------|
| label_name | CharField(128) | 标签名称 |
| bk_biz_id | IntegerField | 业务ID, db_index |
| strategy_id | IntegerField | 策略ID |

#### MonitorStrategyHistory — 策略变更历史

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | IntegerField | 关联策略ID, db_index |
| create_time | DateTimeField | 创建时间, auto_now_add |
| create_user | CharField(32) | 操作人 |
| content | JSONField | 保存内容 |
| operate | CharField(12) | 操作: delete/create/update |
| status | BooleanField | 操作状态 |
| message | TextField | 错误信息 |

### 2.2 告警事件体系

#### AlertEvent — 原始告警事件

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| event_id | CharField(128), unique | 事件唯一ID, 由数据源提供 |
| strategy_id | IntegerField, db_index | 关联策略ID, null=True |
| item_id | IntegerField, db_index | 关联监控项ID, null=True |
| alert_name | CharField(255) | 告警名称 |
| description | TextField | 描述, null=True |
| severity | IntegerField | 级别: 1/2/3 |
| status | CharField(32) | 状态: abnormal/recovered/closed |
| target_type | CharField(64) | 目标类型: host/service/instance |
| target | CharField(512) | 具体目标标识 |
| metric | CharField(128) | 指标名 |
| metric_value | FloatField | 指标值, null=True |
| tags | JSONField | 标签, default=dict |
| dedupe_keys | JSONField | 去重键列表, default=list |
| dedupe_md5 | CharField(64) | 去重指纹, db_index |
| time | DateTimeField | 事件时间 |
| anomaly_time | DateTimeField | 异常时间 |
| create_time | DateTimeField | 记录时间, auto_now_add |
| bk_biz_id | IntegerField | 业务ID, db_index |
| cmdb_host_id | CharField(64) | 关联主机ID, null=True |
| cmdb_biz_id | CharField(64) | 关联业务ID, null=True |
| extra_info | JSONField | 数据源原始信息, default=dict |

**索引：** 联合索引 (strategy_id, status, time)

#### Alert — 聚合告警

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigAutoField | 主键 |
| alert_id | CharField(64), unique | 系统生成告警ID |
| strategy_id | IntegerField, db_index | 关联策略ID, null=True |
| severity | IntegerField | 级别: 1/2/3, db_index |
| status | CharField(32) | 状态, db_index |
| title | CharField(255) | 告警标题 |
| description | TextField | 描述, null=True |
| current_value | FloatField | 当前指标值, null=True |
| metric_unit | CharField(64) | 指标单位, null=True |
| labels | JSONField | 标签, default=dict |
| annotations | JSONField | 注解, default=dict |
| fired_at | DateTimeField | 首次触发时间, db_index |
| resolved_at | DateTimeField | 恢复时间, null=True |
| acknowledged_at | DateTimeField | 确认时间, null=True |
| acknowledged_by | CharField(128) | 确认人, null=True |
| duration | IntegerField | 持续时长(秒), default=0 |
| event_count | IntegerField | 累计事件数, default=1 |
| cmdb_host_id | CharField(64) | 关联主机ID, null=True |
| cmdb_biz_id | CharField(64) | 关联业务ID, null=True |
| assignee | CharField(128) | 当前负责人, null=True |
| incident_id | CharField(64) | 关联 ITSM 工单ID, null=True |
| escalation_count | IntegerField | 升级次数, default=0 |
| next_escalate_at | DateTimeField | 下次升级时间, null=True |

**状态机：** firing → acknowledged → resolved → closed

#### AlertLog — 告警流水日志

| 字段 | 类型 | 说明 |
|------|------|------|
| alert_id | CharField(64), db_index | 关联告警ID |
| operate | CharField(32) | 操作类型 |
| operator | CharField(128) | 操作人/系统 |
| create_time | DateTimeField | 时间, auto_now_add |
| description | TextField | 描述 |
| extra | JSONField | 变更详情, default=dict |

### 2.3 通知与值班体系

#### NotifyGroup — 通知组

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(255) | 组名称 |
| bk_biz_id | IntegerField | 业务ID, db_index |
| is_enabled | BooleanField | 是否启用, default=True |
| description | TextField | 描述, null=True |

#### DutyPlan — 值班计划

| 字段 | 类型 | 说明 |
|------|------|------|
| group | FK→NotifyGroup | 关联通知组 |
| name | CharField(255) | 计划名称 |
| is_enabled | BooleanField | 是否启用, default=True |
| plan_type | CharField(32) | 类型: daily/weekly/custom |
| config | JSONField | 排班配置 |

#### DutyArrange — 排班明细

| 字段 | 类型 | 说明 |
|------|------|------|
| plan | FK→DutyPlan | 关联值班计划 |
| user_id | IntegerField | 值班人 |
| date_from | DateTimeField | 开始时间 |
| date_to | DateTimeField | 结束时间 |
| duty_type | CharField(32) | 值班类型: primary/backup |

#### NotifyConfig — 通知配置

| 字段 | 类型 | 说明 |
|------|------|------|
| group | FK→NotifyGroup | 关联通知组 |
| channel | CharField(64) | 通道: wecom/dingtalk/email/sms/webhook |
| config | JSONField | 通道配置 (webhook_url/secret等) |
| notify_time | JSONField | 通知时段, default=dict |
| at_mention | JSONField | @提及配置, default=list |

### 2.4 告警分派与动作

#### AlertAssignGroup — 分派规则组

| 字段 | 类型 | 说明 |
|------|------|------|
| priority | IntegerField, db_index | 优先级, default=-1 |
| name | CharField(128) | 规则组名 |
| bk_biz_id | IntegerField | 业务ID, db_index |
| is_builtin | BooleanField | 是否内置, default=False |
| is_enabled | BooleanField | 是否启用, default=True |
| settings | JSONField | 其他属性, default=dict |

#### AlertAssignRule — 分派规则

| 字段 | 类型 | 说明 |
|------|------|------|
| assign_group_id | FK→AlertAssignGroup | 关联组 |
| bk_biz_id | IntegerField | 业务ID |
| name | CharField(128) | 规则名称 |
| conditions | JSONField | 条件表达式 |
| action_type | CharField(32) | 动作类型 |
| notify_group_id | IntegerField | 通知组ID, null=True |
| action_plugin_id | IntegerField | 动作插件ID, null=True |
| action_config | JSONField | 动作配置, default=dict |
| is_enabled | BooleanField | 是否启用, default=True |

#### ActionPlugin — 动作插件

| 字段 | 类型 | 说明 |
|------|------|------|
| plugin_type | CharField(64) | 插件类型: notice/webhook/job/sops/itsm/common |
| plugin_key | CharField(64) | 唯一标识 |
| name | CharField(64) | 插件名称 |
| description | TextField | 详细描述 |
| is_builtin | BooleanField | 是否内置, default=False |
| plugin_source | CharField(64) | 来源: builtin/peripheral/bk_plugin |
| has_child | BooleanField | 是否有子级联, default=False |
| category | CharField(64) | 插件分类 |
| config_schema | JSONField | 参数配置 JSON Schema |
| adapter_class | CharField(512) | 适配器类路径, null=True |

### 2.5 屏蔽与采集

#### ShieldPlan — 告警静默/屏蔽

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(255) | 计划名称 |
| bk_biz_id | IntegerField | 业务ID, db_index |
| is_enabled | BooleanField | 是否启用, default=True |
| shield_type | CharField(32) | 类型: strategy/target/tag/global |
| conditions | JSONField | 屏蔽条件 |
| time_range | JSONField | 一次性时间范围, null=True |
| schedule | JSONField | 周期性 cron 配置, null=True |
| description | TextField | 描述, null=True |

#### CollectConfig — 采集配置

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(255) | 配置名称 |
| bk_biz_id | IntegerField | 业务ID |
| data_source_label | CharField(32) | 数据源: prometheus/influxdb/custom |
| target | JSONField | 采集目标 |
| plugin | CharField(128) | 采集插件 |
| config | JSONField | 采集参数 |
| interval | IntegerField | 采集周期(秒) |
| is_enabled | BooleanField | 是否启用, default=True |

---

## 3. 告警管道 (Alert Pipeline)

### 3.1 管道阶段

#### 阶段 1: Event Ingest（事件摄入）

**输入：** 数据源推送的原始告警
**输出：** AlertEvent 记录

- Webhook 接收端点：`POST /api/monitor/webhook/prometheus/`、`POST /api/monitor/webhook/grafana/`、`POST /api/monitor/webhook/custom/{code}/`
- 原始 event 落库 status='pending'
- event_id 入 Redis List 触发管道

#### 阶段 2: Strategy Match（策略匹配）

**输入：** AlertEvent → 通过 strategy_id / 标签匹配策略
**输出：** 触发的检测结果

1. 从 Strategy Cache (Redis) 加载策略配置
2. 根据 data_source_label + metric_id 匹配 QueryConfig
3. 执行检测算法 (Algorithm Engine)
4. 判定是否触发(连续N次)、是否恢复

**算法引擎 SPI：**
```python
class BaseAlgorithm:
    """算法基类，所有检测算法继承此接口"""
    
    def check(self, values: list[float], config: dict) -> tuple[bool, float]:
        """返回 (是否触发, 异常值)"""
    
    def get_trigger_expression(self) -> str:
        """返回可读的触发表达式描述"""
```

#### 阶段 3: Alert Build（告警构建）

**输入：** 策略匹配结果
**输出：** Alert 记录

- 幂等创建/更新: `alert_id = hashlib.md5(strategy_id + target + dedupe_keys)`
- 新触发 → 创建 Alert (status='firing')
- 恢复 → 更新 Alert (status='resolved', resolved_at=now)
- 已有 firing Alert → 更新 event_count、current_value
- 每次变更记录 AlertLog

#### 阶段 4: Shield Filter（静默过滤）

**输入：** Alert
**输出：** 放行 / 丢弃

- 从 Shield Cache (Redis) 加载生效中的屏蔽计划
- 按 strategy_id / target / 标签 匹配
- 匹配则更新 Alert status='silenced'

#### 阶段 5: Convergence（收敛）

**输入：** Alert
**输出：** 可执行告警

| 策略 | 行为 |
|------|------|
| 指纹去重 | event.dedupe_md5 + alert.status=firing, 已存在则跳过 |
| 聚合收敛 | 同策略+同目标窗口内多次触发合并为一条, event_count++ |
| 依赖抑制 | A 规则触发时抑制 B 规则的关联告警 |

#### 阶段 6: Action Dispatch（动作分派）

**输入：** 可执行告警
**输出：** 通知/动作执行

1. 按 priority 匹配 AlertAssignGroup
2. 评估 conditions → 命中分派规则
3. 解析 notify_group_id → 获取通知组 + 当前值班人
4. 通过 Notify Adapter 执行通知
5. 通过 Action Adapter 执行自动化动作 (OpsFlow/AWX)

### 3.2 升级策略

- Alert 未确认超过 N 分钟 → 升级 severity
- escalate_count++，通知更高级别组
- next_escalate_at 由 APScheduler 任务每 60s 检查

### 3.3 APScheduler 任务清单

```
MonitorScheduler 注册的任务：

1. 待处理事件消费 (interval=1s, 使用 Redis BRPOP)
   → 从 Redis List 弹出 event_id
   → 加载 AlertEvent → Strategy Match → Alert Build

2. 告警升级检查 (interval=60s)
   → 查找 firing + escalate_at < now 的告警
   → 执行升级逻辑

3. 静默/屏蔽生效 (interval=60s)
   → 检查 ShieldPlan 状态变化
   → 刷新 Shield Cache

4. 自动恢复检测 (interval=300s)
   → 查找超过 auto_resolve_seconds 未恢复的告警
   → 自动置为 resolved

5. 告警事件清理 (interval=3600s)
   → 清理超过 TTL 的 AlertEvent 记录
```

---

## 4. API 路由

### 4.1 路由表

```
/api/monitor/
├── strategies/            → MonitorStrategyViewSet
├── items/                 → MonitorItemViewSet
├── alert-events/          → AlertEventViewSet (只读)
├── alerts/                → AlertViewSet
├── notify-groups/         → NotifyGroupViewSet
├── duty-plans/            → DutyPlanViewSet
├── duty-arranges/         → DutyArrangeViewSet
├── assign-groups/         → AlertAssignGroupViewSet
├── action-plugins/        → ActionPluginViewSet
├── shield-plans/          → ShieldPlanViewSet
├── collect-configs/       → CollectConfigViewSet
├── targets/               → MonitorTargetViewSet (只读, SPI查询)
├── datasources/           → DataSourceViewSet (只读)
├── webhook/               → Webhook 接收端点
│   ├── prometheus/        → Prometheus AlertManager 接收
│   ├── grafana/           → Grafana Alerting 接收
│   └── custom/{code}/     → 自定义采集推流
├── dashboard/             → DashboardViewSet
│   ├── summary/           → 概览统计
│   ├── trend/             → 告警趋势
│   ├── severity-dist/     → 级别分布
│   └── top-alerts/        → TOP N
└── settings/              → MonitorSettingsView
```

### 4.2 响应格式

遵循 opsflow 项目规范，使用 `DetailResponse` / `SuccessResponse` / `ErrorResponse`。
所有列表接口支持：`search`、`filter_fields`、`ordering`、`page/limit`。

---

## 5. SPI 适配器接口

### 5.1 数据源适配器 (BaseDataSourceAdapter)

```python
class BaseDataSourceAdapter(ABC):
    """数据源适配器 — 对接 Prometheus/InfluxDB/自建采集"""

    @abstractmethod
    def fetch_metrics(self, query_config: dict) -> list[MetricValue]:
        """
        查询指标数据
        query_config: MonitorQueryConfig.config
        返回: [MetricValue(metric, value, timestamp, tags)]
        """

    @abstractmethod
    def health_check(self) -> HealthResult:
        """检查数据源连接"""
```

### 5.2 通知适配器 (BaseNotifyAdapter)

```python
class BaseNotifyAdapter(ABC):
    """通知适配器 — 企业微信/钉钉/邮件/短信"""

    @abstractmethod
    def send(self, recipients: list[str], message: NotifyMessage) -> NotifyResult:
        """发送通知"""
```

### 5.3 动作适配器 (BaseActionAdapter)

```python
class BaseActionAdapter(ABC):
    """动作适配器 — OpsFlow 流程/ AWX 作业/ITSM 工单"""

    @abstractmethod
    def execute(self, context: ActionContext) -> ActionResult:
        """执行自动化动作"""
```

### 5.4 目标解析器 (BaseTargetResolver)

```python
class BaseTargetResolver(ABC):
    """监控目标解析 — 从 CMDB/容器标签/静态列表解析目标"""

    @abstractmethod
    def resolve(self, target_expr: dict) -> list[MonitorTarget]:
        """将表达式解析为具体目标列表"""
```

### 5.5 注册方式

```python
# settings.py
MONITOR_ADAPTERS = {
    'datasource': {
        'prometheus': 'monitor.adapters.datasource.prometheus.PrometheusDataSource',
        'influxdb': 'monitor.adapters.datasource.influxdb.InfluxdbDataSource',
        'custom': 'monitor.adapters.datasource.custom.CustomDataSource',
    },
    'notify': {
        'integration_hub': 'monitor.adapters.notify.integration_hub.IntegrationHubNotify',
        'wecom': 'monitor.adapters.notify.wecom.WeComNotify',
        'dingtalk': 'monitor.adapters.notify.dingtalk.DingTalkNotify',
    },
    'action': {
        'opsflow': 'monitor.adapters.action.opsflow.OpsflowAction',
        'awx': 'monitor.adapters.action.awx.AwxAction',
        'itsm': 'monitor.adapters.action.itsm.ItsmAction',
    },
    'target_resolver': {
        'cmdb': 'monitor.adapters.target.cmdb.CmdbTargetResolver',
        'static': 'monitor.adapters.target.static.StaticTargetResolver',
    },
}

# 运行时加载
from django.utils.module_loading import import_string
adapter_cls = import_string(settings.MONITOR_ADAPTERS['datasource']['prometheus'])
adapter = adapter_cls(instance_config)
```

---

## 6. 前端页面

### 6.1 页面矩阵与路由

| 页面 | 路由 | 功能 | 优先级 | 阶段 |
|------|------|------|--------|------|
| 告警事件中心 | `/monitor/alerts` | 列表/搜索/过滤、确认/恢复/关闭/建单、批量操作、详情抽屉 | P0 | 一期 |
| 告警规则管理 | `/monitor/strategies` | 四层策略配置向导、克隆/启禁用、版本历史 | P0 | 一期 |
| 监控目标 | `/monitor/targets` | CMDB 目标查询、标签过滤、关联告警统计 | P0 | 一期 |
| 通知组管理 | `/monitor/notify-groups` | 组 CRUD、成员管理、通知渠道、测试通知 | P0 | 一期 |
| 告警看板 | `/monitor/dashboard` | 概览统计、趋势图、级别分布、TOP N | P0 | 一期 |
| 值班排班 | `/monitor/duty` | 日历视图、排班设置、换班操作 | P1 | 一期 |
| 告警分派规则 | `/monitor/assign-rules` | 规则组/规则 CRUD、条件编辑器、优先级排序 | P1 | 一期 |
| 静默管理 | `/monitor/shields` | 静默计划 CRUD、时间范围/周期配置 | P1 | 一期 |
| 动作插件管理 | `/monitor/actions` | 内置插件展示、自定义注册、测试 | P1 | 一期 |
| 故障聚合视图 | `/monitor/incidents` | 关联告警聚合为故障、根因分析 | P2 | 二期 |
| 采集器管理 | `/monitor/collectors` | 采集配置 CRUD、采集状态 | P2 | 二期 |
| 数据源管理 | `/monitor/datasources` | 注册数据源、指标浏览、连接测试 | P2 | 二期 |
| SLA 统计 | `/monitor/sla` | MTBF/MTTR、响应时效统计 | P2 | 二期 |
| 全局设置 | `/monitor/settings` | 管道间隔、清理策略、收敛窗口 | P2 | 二期 |

### 6.2 一期核心页面功能

#### 告警事件中心
- 表格视图：title / severity / status / metric_value / fired_at / duration
- 过滤：status × severity × strategy × time range
- 操作：确认、恢复、关闭、转派、关联工单
- 批量：批量确认、批量关闭
- 详情抽屉：事件流、流水日志、关联规则

#### 告警规则管理
- 策略列表：name / scenario / is_enabled / 最近告警数
- 创建向导：Step 1: 基本信息 → Step 2: 监控项+查询配置 → Step 3: 检测配置+算法 → Step 4: 通知+动作
- Step 3 可视化算法配置：阈值输入框 / 环比幅度滑块 / 同比参照选择
- 策略克隆、启用/禁用

#### 告警看板
- 告警概览卡片：Firing / Acknowledged / Resolved / Total
- 24h 告警趋势折线图
- 级别分布饼图
- TOP 10 告警规则排行
- TOP 10 告警主机排行

---

## 7. 实施阶段

### 第一阶段 (P0 + P1)
- 全部数据模型 + migration
- 策略/事件/告警/通知组/分派/动作/静默的 ViewSet CRUD
- Alert Pipeline 核心：
  - Webhook 接收 (Prometheus + Grafana)
  - Strategy Match 引擎（前 6 种算法）
  - Alert Build 与状态机
  - Shield Filter
  - Convergence (去重+聚合)
- APScheduler MonitorScheduler 注册
- Notify Adapter (对接 Integration Hub)
- 前端：告警事件中心 + 规则管理 + 通知组 + 看板 + 值班 + 分派 + 静默 + 动作插件

### 第二阶段 (P2)
- 采集器管理 + 数据源管理
- 故障聚合视图
- SLA 统计
- 全局设置
- 自建采集 Push API
- 剩余 4 种算法 (IntelligentDetect / TimeSeriesForecasting / PartialNodes / OsRestart)

---

## 8. 与现有模块的关系

### 复用 Integration Hub
- **通知发送**：Monitor 的 Notify Adapter 通过 Integration Hub 的 ConnectorInstance 获取通知通道配置
- **凭据管理**：采集器/数据源的访问凭据使用 Integration Credential 的 AES-256 加密存储
- **健康检查**：复用 Integration Hub 的健康检查框架

### 与 CMDB 松耦合
- Alert.cmdb_host_id 和 Alert.cmdb_biz_id 都存字符串
- TargetResolver SPI 负责将 CMDB 查询条件解析为主机/业务列表
- 不引入 ForeignKey，不循环依赖

### 触发 OpsFlow
- ActionPlugin type='opsflow' 通过 ActionAdapter 调用 OpsFlow API 触发自愈流程
- 动作执行后记录执行结果到 AlertLog

### 创建 ITSM 工单
- Alert 详情页"创建工单"按钮通过 ActionAdapter 调用 ITSM API
- incident_id 回填到 Alert 记录

---

## 9. 错误处理

| 场景 | 处理方式 |
|------|---------|
| Webhook JSON 解析失败 | 返回 400 + ErrorResponse，记录错误日志 |
| 数据源查询超时 | 标记策略为 invalid (invalid_type=invalid_source)，跳过检测 |
| 算法检测异常 | 跳过该算法，记日志，不影响其他算法检测 |
| 通知发送失败 | 重试 3 次（指数退避），记 AlertLog |
| 动作执行失败 | 记 AlertLog，标记 action_status=failed |
| 去重指纹碰撞 | 用 strategy_id + target + dedupe_keys_hash 的组合确保唯一性 |
| Redis 不可用 | 降级为纯轮询模式（APScheduler 定时扫库），不影响核心功能 |

---

## 10. 设计约束

- 所有 API 响应使用 `DetailResponse` / `ErrorResponse` / `SuccessResponse`
- 不使用 emoji 字符（MySQL utf8mb3 限制）
- Code 语言全英文，注释中英双语
- 策略模型四层结构不得合并，保持对标 bk-monitor 的可迁移性
- Adapter 必须通过 settings 配置注册，不允许硬编码
- 每个 APScheduler 任务必须有日志和异常捕获，防止一个任务炸掉整个 scheduler
