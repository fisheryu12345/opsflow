# monitor — 模块索引

> 上次自动更新: 2026-06-12

---

## `monitor/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Monitor and alerting app |
| `admin.py` | Admin configuration for Monitor app | `MonitorStrategyAdmin`<br>`MonitorItemAdmin`<br>`AlertEventAdmin`<br>`AlertAdmin`<br>`AlertLogAdmin`<br>`NotifyGroupAdmin` |
| `apps.py` | AppConfig for monitor app — 启动 MonitorScheduler | `MonitorConfig` |
| `serializers.py` | Serializers for Monitor app — 所有模型的序列化器 | `MonitorAlgorithmConfigSerializer`<br>`MonitorDetectConfigSerializer`<br>`MonitorQueryConfigSerializer`<br>`MonitorItemSerializer`<br>`MonitorStrategyListSerializer` — 策略列表 — 精简版<br>`MonitorStrategyDetailSerializer` — 策略详情 — 嵌套所有子级 |
| `urls.py` |  | URL configuration for Monitor app |

## `monitor\adapters/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | SPI Adapter base interfaces — 数据源/通知/动作/目标解析四类适配器基类 | `MetricValue` — 指标值<br>`HealthResult` — 健康检查结果<br>`NotifyMessage` — 通知消息<br>`NotifyResult` — 通知结果<br>`ActionContext` — 动作执行上下文<br>`ActionResult` — 动作执行结果 |

## `monitor\adapters\action/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Action adapters package |
| `awx.py` | AWX/Tower action adapter — 触发 AWX 作业执行 | `AwxAction` — AWX/Tower 作业触发适配器 |
| `base.py` |  | Action adapter base — re-export from parent |
| `itsm.py` | ITSM action adapter — 创建 ITSM 工单 | `ItsmAction` — ITSM 工单创建适配器 |
| `opsflow.py` | OpsFlow action adapter — 触发 OpsFlow 自动化流程执行 | `OpsflowAction` — OpsFlow 流程触发适配器 — 通过 OpsFlow API 触发自愈流程 |

## `monitor\adapters\datasource/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | DataSource adapters package |
| `base.py` |  | DataSource adapter base — re-export from parent |
| `custom.py` | Custom DataSource adapter stub — 自建采集数据源适配器 | `CustomDataSource` — 自定义数据源适配器 — 由自建采集插件推流的数据 |
| `influxdb.py` | InfluxDB DataSource adapter | `InfluxdbDataSource` — InfluxDB 数据源适配器 (兼容 v1 + v2) |
| `prometheus.py` | Prometheus DataSource adapter | `PrometheusDataSource` — Prometheus 数据源适配器 |

## `monitor\adapters\notify/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Notify adapters package |
| `base.py` |  | Notify adapter base — re-export from parent |
| `dingtalk.py` | DingTalk (钉钉) notify adapter — 通过机器人 Webhook 发送告警通知 | `DingTalkNotify` — 钉钉机器人通知适配器 |
| `email.py` | Email notify adapter — 通过 SMTP 发送告警邮件 | `EmailNotify` — 邮件通知适配器 |
| `integration_hub.py` | Integration Hub notify adapter — 复用已有的集成中心通知通道 | `IntegrationHubNotify` — 集成中心通知适配器 复用 integration 模块的 ConnectorInstance 管理通知通道配置。 支持的通道: wecom / dingtalk / email / sms / web |
| `sms.py` | SMS notify adapter stub — 短信通知适配器 (需对接具体短信网关) | `SmsNotify` — 短信通知适配器 — 通过 Integration Hub 短信连接器发送 |
| `wecom.py` | WeCom (企业微信) notify adapter — 通过机器人 Webhook 发送告警通知 | `WeComNotify` — 企业微信机器人通知适配器 |

## `monitor\adapters\target/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Target resolver adapters package |
| `base.py` |  | Target resolver adapter base — re-export from parent |
| `cmdb.py` | CMDB Target resolver — 从 CMDB 查询监控目标 | `CmdbTargetResolver` — CMDB 目标解析器 — 通过 CMDB API 查询主机/服务实例 |
| `static.py` | Static Target resolver — 静态列表方式指定监控目标 | `StaticTargetResolver` — 静态目标解析器 — 直接返回配置中的 IP / 主机名列表 |

## `monitor\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands package for monitor app |

## `monitor\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands package for monitor app |

## `monitor\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Monitor models — 告警策略、事件、通知、动作等完整数据模型 |
| `action.py` | Action models — AlertAssignGroup, AlertAssignRule, ActionPlugin | `AlertAssignGroup` — 告警分派规则组 — 按优先级排序的一组分派规则<br>`AlertAssignRule` — 告警分派规则 — conditions 匹配则执行 action<br>`ActionPlugin` — 动作插件 — 告警触发后可执行的动作类型，支持插件化注册 |
| `alert.py` | Alert models — AlertEvent(原始事件), Alert(聚合告警), AlertLog(流水日志) | `AlertEvent` — 原始告警事件 (Event) 来自数据源 (Prometheus/Grafana/自建采集) 的原始告警记录。 每条 event 对应一次检测触发，经策略匹配后可能创建/更新 Alert。<br>`Alert` — 聚合告警 (Alert) 经过策略匹配、收敛后的可操作告警实体。 一条 Alert 可关联 N 条原始 Event。<br>`AlertLog` — 告警流水日志 — 记录告警生命周期中的所有状态变更和操作 |
| `collect.py` | CollectConfig model — 采集配置（数据源接入配置） | `CollectConfig` — 采集配置 — 定义如何采集监控指标（Prometheus/InfluxDB/自建插件） |
| `notification.py` | Notification models — NotifyGroup, DutyPlan, DutyArrange, NotifyConfig | `NotifyGroup` — 通知组 — 告警通知的接收者分组，可关联值班计划<br>`DutyPlan` — 值班计划 — 定义通知组的值班排班规则<br>`DutyArrange` — 排班明细 — 某人某时间段内值班<br>`NotifyConfig` — 通知配置 — 通知组的通知渠道和通知时段 |
| `shield.py` | ShieldPlan model — 告警静默/屏蔽计划 | `ShieldPlan` — 告警静默/屏蔽计划 — 在指定时间范围内屏蔽符合条件的告警 |
| `strategy.py` | Strategy models — MoniorStrategy 四层策略模型 (Strategy→Item→QueryConfig→Detect→Algorithm) | `MonitorStrategy` — 监控策略 (Strategy) 对标 bk-monitor StrategyModel。定义一组监控项的集合及触发行为。<br>`MonitorItem` — 监控项 (Item) 对标 bk-monitor ItemModel。定义一条具体的监控指标及查询方式。<br>`MonitorQueryConfig` — 查询配置 (QueryConfig) 对标 bk-monitor QueryConfigModel。定义指标查询的数据源和参数。<br>`MonitorDetectConfig` — 检测配置 (Detect Config) 对标 bk-monitor DetectModel。定义告警级别、触发条件与恢复条件。<br>`MonitorAlgorithmConfig` — 检测算法配置 (Algorithm Config) 对标 bk-monitor AlgorithmModel。定义具体的检测算法及参数。<br>`MonitorStrategyLabel` — 策略标签<br>`default_target()`<br>`no_data_config()` |

## `monitor\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Monitor services — pipeline engine, algorithm engine, schedu |
| `adapter_loader.py` | SPI Adapter Loader — 从 settings 配置加载适配器实例 | `AdapterLoader` — 适配器加载器 — 根据 settings.MONITOR_ADAPTERS 加载适配器 |
| `algorithm_engine.py` | Algorithm Engine — 检测算法引擎 | `BaseAlgorithm` — 算法基类<br>`ThresholdAlgorithm` — 静态阈值算法 — method: gt/lt/gte/lte, threshold: float<br>`SimpleRingRatioAlgorithm` — 简易环比 — 与上一周期值比较变化率<br>`AdvancedRingRatioAlgorithm` — 高级环比 — 与过去 N 个周期的均值比较<br>`SimpleYearRoundAlgorithm` — 简易同比 — 与 N 个周期前同一点比较<br>`AdvancedYearRoundAlgorithm` — 高级同比 — 与历史同期多周期的中位数比较<br>`get_algorithm()` — 获取算法实例<br>`run_detection()` — 执行检测 — 返回 (is_triggered, anomaly_value, expression) |
| `pipeline.py` | Alert Pipeline — 告警处理管道引擎 | `AlertPipeline` — 告警管道 — 处理单条事件/告警的全生命周期 每个阶段返回 dict 或 None (中断) |
| `scheduler.py` | MonitorScheduler — 监控告警中心调度器 | `MonitorScheduler` — 监控告警中心调度器 — 独立于 OpsflowScheduler |
| `webhook_receivers.py` | Webhook receivers — Prometheus AlertManager / Grafana / 自定义推流 | `prometheus_webhook()` — Prometheus AlertManager Webhook 接收端点 配置 AlertManager → webhook_configs → url: /a<br>`grafana_webhook()` — Grafana Alerting Webhook 接收端点 配置 Grafana Notification Channel → Webhook → /api/m<br>`custom_push()` — 自定义采集推流端点 POST /api/monitor/webhook/custom/{code}/ body: {"events": [{"alert_nam |

## `monitor\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Views package for monitor app |
| `action_views.py` | Action views — AlertAssignGroup, ActionPlugin ViewSets | `AlertAssignGroupViewSet` — 告警分派规则组管理<br>`ActionPluginViewSet` — 动作插件管理 |
| `alert_views.py` | Alert views — AlertEvent, Alert, AlertLog ViewSets | `AlertEventViewSet` — 原始告警事件（只读）<br>`AlertViewSet` — 聚合告警管理 |
| `collect_views.py` | Collect views — CollectConfig ViewSet | `CollectConfigViewSet` — 采集配置管理 |
| `dashboard_views.py` | Dashboard views — 监控看板统计端点 | `DashboardViewSet` — 监控看板统计 (只读) |
| `notification_views.py` | Notification views — NotifyGroup, DutyPlan, DutyArrange ViewSets | `NotifyGroupViewSet` — 通知组管理<br>`DutyPlanViewSet` — 值班计划管理<br>`DutyArrangeViewSet` — 排班明细管理 |
| `shield_views.py` | Shield views — ShieldPlan ViewSet | `ShieldPlanViewSet` — 告警屏蔽计划管理 |
| `strategy_views.py` | Strategy views — MonitorStrategy & MonitorItem ViewSets | `MonitorStrategyViewSet` — 监控策略管理<br>`MonitorItemViewSet` — 监控项管理 |
