# OpsAgent — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐☆☆ (3/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | AI 对话工具链不完善，多轮复杂操作未实现，流式响应未实现 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| Session 会话管理 | P0 | ✅ | 对话会话生命周期 | Session 模型(session_id/operator/environment/mode/status)，REPL+oneshot 模式 |
| EnvironmentContext 环境 | P0 | ✅ | 运维上下文 | env_type(dev/staging/canary/prod)，topology_json，Business FK 新增 |
| AuditRecord 审计 | P1 | ✅ | 操作风险评估 | risk_score/action/env_dimension/impact_radius/recommendation |
| AgentMemory 记忆 | P1 | ✅ | 经验记忆持久化 | tag/summary/embedding(768d 默认值)，语义搜索 |
| LLM 接入 | P1 | ✅ | DeepSeek 集成 | 通过 integration.ui.ai_connector_service 调用 |
| SafetyEngine 安全引擎 | P1 | ✅ | 操作安全评估 | risk_score/action/env/impact 四维评估，APIMode auto-approve |
| Tool Registry | P1 | 🔄 | 工具调用注册 | 5 个工具已注册：cmdb_query/opsflow_execute/alert_query<i>/alert_ack/itsm_ticket_query</i> |
| CMDB 查询工具 | P1 | ✅ | 查资源 | ToolRegistry.parse_params -> cmdb services |
| OpsFlow 执行工具 | P1 | ✅ | 触发流程 | opsflow_execute -> FlowEngine |
| Monitor 告警工具 | P2 | 🔄 | 查询/确认告警 | alert_query 已注册，<b>alert_ack 确认操作未实现</b> |
| ITSM 工单工具 | P2 | 🔄 | 查询/创建工单 | itsm_ticket_query 已注册，<b>创建工单未实现</b> |
| WebSocket 流式响应 | P2 | ✅ | 实时流式输出 | ws_push 实现，Session result_json 存储 |
| 前段 Chat 面板 | P1 | ✅ | 对话 UI | ChatPanel + ToolCallCard + SessionHistory 组件 |
| 多轮复杂操作 | P2 | 📅 | 多步骤自动化 | — |
| i18n | P2 | ✅ | 中英双语 | en/zh-cn 各 97 key |

## TODO

### P1
- [ ] Monitor/ITSM 工具链完善（alert_ack/itsm_ticket_create）
- [ ] APIMode 安全评估（当前 auto-approve 所有调用）

### P2
- [ ] 多轮复杂操作编排
- [ ] 工具链扩展（更多子产品集成）
- [ ] 补充测试用例
