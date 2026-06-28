# Monitor — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐☆ (4/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | 四层告警策略引擎完整，但自愈闭环未对接 OpsFlow 完成，Prometheus 内嵌未实施 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 四层策略模型 | P0 | ✅ | Strategy→Item→QueryConfig→Detect→Algorithm | 完整：继承 bk-monitor 设计 |
| 告警聚合 (Alert) | P0 | ✅ | 多 Event → 单 Alert | Event 去重+收敛，severity/involved 统计 |
| 告警事件 (AlertEvent) | P0 | ✅ | 原始告警持久化 | 去重哈希(dedup_key)、source/severity/involved |
| 告警分配 (AlertAssign) | P0 | ✅ | 自动分派 | 策略级 AssignGroup + AssignRule |
| 通知组 (NotifyGroup) | P1 | ✅ | 多渠道通知 | 钉钉/企微/邮件/短信 通道 |
| 值班计划 (DutyPlan) | P1 | ✅ | 排班管理 | DutyArrange 时间片分配 |
| 告警升级 | P1 | ✅ | escalation_count + next_escalate_at | Alert 模型字段就绪，升级逻辑未完整实现 |
| 静默屏蔽 (ShieldPlan) | P1 | ✅ | 时间段屏蔽 | 按策略/级别/维度过滤 |
| 数据采集 (CollectConfig) | P1 | ✅ | 采集任务管理 | Prometheus 查询配置 |
| 动作插件 (ActionPlugin) | P2 | ✅ | 通知/恢复/自愈动作 | ActionPlugin 模型，具体插件实现未完成 |
| 自愈策略 (SelfHealing) | P2 | 🔄 | 告警→OpsFlow 流程 | bk_biz_id 字段就绪，business FK 新增，触发逻辑未对接 FlowEngine |
| Prometheus 集成 | P2 | 📅 | 内嵌 docker-compose | specs 已设计，未实施 |
| Grafana 预置看板 | P2 | 📅 | 4 个系统看板 | — |
| 告警自监控 | P2 | 📅 | 4 条内部告警规则 | — |
| 自愈闭环（完成回写） | P2 | 📅 | 流程完成→关闭告警 | — |
| WebSocket 实时推送 | P2 | 📅 | ws/monitor/alert/{id}/ | — |

## TODO

### P1
- [ ] ActionPlugin 插件完善（通知/恢复/自愈脚本）
- [ ] 告警升级逻辑完整实现

### P2
- [ ] 自愈策略 → OpsFlow 触发全链路
- [ ] 自愈闭环（流程完成→更新告警状态）
- [ ] Prometheus + Grafana docker-compose
- [ ] 4 条预置告警规则
- [ ] Monitor 自监控策略 seed
- [ ] WebSocket 实时推送
- [ ] 补充测试用例
