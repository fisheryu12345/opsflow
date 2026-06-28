# ITSM — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐☆ (4/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | AI 生成器未用真实 LLM，双向 OpsFlow 审批集成未完成，服务目录未建 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 工作流模板引擎 | P0 | ✅ | Workflow/State/Transition/Field 管理 | 完整 CRUD + deploy 版本快照 |
| 工单生命周期 | P0 | ✅ | Ticket CRUD + 流转 | submit/node_submit/approve/reject/suspend/resume/close |
| Pipeline 驱动执行 | P0 | ✅ | Bamboo-engine DAG 驱动 | PipelineWrapper(build_tree/run/pause/resume/revoke/callback) |
| 4 种节点类型 | P0 | ✅ | 填单/审批/会签/自动任务 | ItsmFillForm/ItsmApproval/ItsmSign/ItsmAutoTask 组件 |
| 多级审批/会签 | P0 | ✅ | 多审批人/顺序/并行 | SignTask + RoleResolver(6种解析) + delegation |
| SLA 引擎 | P1 | ✅ | 超时升级 | SlaEngine(start/pause/resume/stop) + Celery 每分钟检查 |
| 通知渠道 | P1 | ✅ | 钉钉/企微/邮件/IntegrationHub | 4 个 channel 实现 |
| 审批委托 | P1 | ✅ | 代理审批 | 时间范围+工单类型过滤 |
| 传统 ITSM 模型 | P1 | ✅ | Incident/Change/Problem/ServiceRequest | 完整 CRUD + 状态转换 |
| OpsFlow 集成 | P1 | ✅ | 审批后触发 OpsFlow 执行 | TicketOpsflowConfig + on_ticket_approved 完整 |
| 仪表盘 | P1 | ✅ | 工单统计 | summary/my_tasks/trend/status_dist/overdue |
| SlaPolicy 模型 | P1 | ✅ | SLA 策略定义 | PriorityMatrix + SLA 策略 |
| AI 智能生成 | P2 | 🔄 | LLM 生成工作流 | AIGenerator：内置关键词模板引擎，<b>未接入真实 DeepSeek</b> |
| 服务目录 | P2 | 📅 | 可请求的 IT 服务项 | ServiceCategory 模型存在，但无完整服务项+履行流程 |
| OpsFlow 双向审批 | P2 | 📅 | OpsFlow 审批节点创建 ITSM 工单 | 仅 ITSM→OpsFlow 单向，反向未实现 |
| Monitor 告警→工单 | P2 | 📅 | 告警自动创建工单 | 无 Ticket ← Alert 集成 |
| 变更日历 | P2 | 📅 | 变更时间线展示 | 无前端组件 |
| AI 全面 LLM 替代 | P2 | 📅 | DeepSeek 替代关键词模板 | — |

## TODO

### P0
- [ ] 无

### P1
- [ ] AIGenerator 接入 DeepSeek
- [ ] 服务目录完整实现

### P2
- [ ] OpsFlow 审批节点 ↔ ITSM 工单双向
- [ ] Monitor 告警 → 创建工单
- [ ] 变更日历前端
- [ ] SlaPolicy 字段命名对齐（model: response_minutes → engine: handle_time）
- [ ] 补充测试用例
