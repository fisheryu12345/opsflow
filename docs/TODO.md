# OPSflow 平台开发路线图总览

> 基于 `docs/opsflow_target.md` 顶层设计 · 最后代码验证: 2026-06-07
> 顶层设计锚定版本: `78ad9ee2b3a82b83981fc77c254b59d1721d4494`

## 总览

| 子产品 | 成熟度 | P0 | P1 | P2 | 完成率 |
|-------|:------:|:--:|:--:|:--:|:------:|
| OpsFlow Core | ⭐⭐⭐⭐⭐ (5/5) | 1/1 | 4/7 | 2/7 | 37% |
| dvadmin (RBAC) | ⭐⭐⭐⭐⭐ (5/5) | 0/0 | 0/0 | 0/0 | 100% |
| CMDB | ⭐⭐⭐⭐☆ (4/5) | 0/1 | 0/0 | 0/0 | 0% |
| ITSM | ⭐⭐⭐⭐☆ (4/5) | 0/0 | 1/1 | 0/0 | 0% |
| Monitor | ⭐⭐⭐⭐☆ (4/5) | 0/1 | 0/0 | 0/0 | 0% |
| Open API | ⭐⭐⭐⭐☆ (4/5) | 1/1 | 0/0 | 0/0 | 100% |
| Portal | ⭐⭐⭐⭐☆ (4/5) | 0/0 | 0/0 | 0/0 | 100% |
| Integration Hub | ⭐⭐⭐☆☆ (3/5) | 1/1 | 0/0 | 0/0 | 100% |
| Job Platform | ⭐⭐⭐☆☆ (3/5) | 0/0 | 0/0 | 1/2 | 20% |
| OpsAgent | ⭐⭐⭐☆☆ (3/5) | 0/0 | 1/1 | 0/0 | 0% |
| Agent (远程) | ⭐⭐☆☆☆ (2/5) | 0/0 | 0/0 | 1/1 | 0% |
| CI/CD + K8s | ⭐☆☆☆☆ (1/5) | 0/0 | 0/0 | 1/1 | 0% |

---

### OpsFlow Core (⭐⭐⭐⭐⭐)

**定位:** 整个平台的核心，所有运维自动化流程的编排与执行中枢

| 模块 | 职责 | 状态 |
|------|------|:----:|
| FlowEngine | 流程执行主入口 (start/pause/resume/cancel/retry/skip) | ✅ 完整 |
| PipelineBuilder | 前端 pipeline_tree → bamboo-engine DAG | ✅ 完整 |
| PluginService | 原子执行路由 (execute/schedule/rollback) | ✅ 完整 |
| NodeCommandDispatcher | 节点级操作 + 轨迹追踪 | ✅ 完整 |
| Signals (handlers) | 状态变更异步处理 (state/trace/notify/timeout) | ✅ 完整 |
| SafetyGuard | Pipeline 安全校验 | ✅ 完整 |
| SchedulerService | APScheduler 定时调度 | ✅ 完整 |
| LLMService | DeepSeek AI 生成/精炼/分析 | ✅ 完整 |
| VariableResolver | ${key} 变量运行时解析 + Mako | ✅ 完整 |
| LayoutEngine | Sugiyama 分层图自动布局 | ✅ 完整 |
| WebhookService | Webhook 回调分发 | ✅ 完整 |
| apigw/ (已迁移) | 外部 API (已迁移到 `open_api` app) | ✅ 已迁移 |
| AutoRetry + Timeout | 节点自动重试 + 超时策略 | ✅ 完整 |
| NodeSync | TemplateNode/ExecutionNode 双向同步 | ✅ 完整 |
| ConflictChecker | 多人编辑冲突检测 | ✅ 完整 |
| AuditLogger | 操作审计记录 | ✅ 完整 |

#### P0 — 高优先级
- [x] **Open API 独立化** — 已迁移至 `backend/open_api/` (`open_api/views/external.py` 中实现 `trigger_pipeline`/`query_execution`/`list_pipeline_templates`，`opsflow/core/apigw/` 已删除)

#### P1 — 中优先级
- [ ] **项目级 RBAC 增强** — viewer 只读权限强制 + 跨项目模板共享管理界面（顶层设计参考: §5.2 P1）
- [ ] **操作审计前端** — OperationRecord 浏览/过滤/导出页面（后端 API `/api/opsflow/audit/` 已就绪，前端 `opsflow-audit` 页面待开发）
- [ ] **TemplateNode/ExecutionNode 节点同步定时任务** — 确保 pipeline_tree 和节点持久化行记录一致性（`core/node_sync.py` 已实现同步逻辑，但缺少定期校验任务）
- [x] **Dry Run 增强** — 执行结束支持一键清理测试数据（代码验证: `DryRunDialog.vue` 已存在，但后端清理命令 `clean_opsflow_data --dry-run-only` 待实现）
- [ ] **模板自动保存冲突提示** — 多人编辑时冲突检测前端集成（`core/conflict_checker.py` 已实现检测逻辑，但前端未集成冲突提示 UI）

#### P2 — 低优先级
- [x] **配置驱动表单架构** — 参考 bk-sops 的 JSON Schema 表单架构（`plugins/base.py` 中 `get_form_config()` 已返回 `FormConfig` 对象，但前端 PropertyPanel 仍以手写表单为主）
- [x] **批量删除模板/执行** — 前端批量选择 + 后端批量删除端点（代码验证: 当前是单条操作，缺少批量端点）
- [ ] **Tower Webhook 回调方案** — 替代轮询，减少 Tower API 压力

---

### dvadmin (RBAC) (⭐⭐⭐⭐⭐)

**定位:** 基础平台框架 — 用户/角色/权限/菜单/部门管理

| 模块 | 职责 | 状态 |
|------|------|:----:|
| 用户管理 | 用户 CRUD + 部门关联 | ✅ 完整 |
| 角色管理 | 角色 CRUD + 权限分配 | ✅ 完整 |
| 菜单管理 | 动态菜单树 + 路由配置 | ✅ 完整 |
| 部门管理 | 组织架构管理 | ✅ 完整 |
| 字典管理 | 数据字典配置 | ✅ 完整 |
| 配置管理 | 系统配置参数 | ✅ 完整 |
| JWT 认证 | 登录/登出/刷新 Token | ✅ 完整 |

**TODO:** 无待办任务（成熟度 5/5，生产就绪）

---

### CMDB (⭐⭐⭐⭐☆)

**定位:** 唯一的数据真相源，为所有子产品提供资产、拓扑、资源关系。正在从 MySQL 模型向 Neo4j 图数据库重构。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| Neo4j 客户端 | Neo4j 图数据库连接池管理 (`neo4j_client.py`) | ✅ 完整 |
| 数据库路由 | Django ORM → Neo4j 路由 (`neo4j_router.py`) | ✅ 完整 |
| 模型管理 | 资源模型定义（服务器/网络/存储/中间件/应用） | 🔄 重构中 |
| 拓扑引擎 | 资产间关系的图查询与可视化 | 🔄 重构中 |
| 资源查询 | 资源筛选/搜索/详情 | ✅ Mock 数据 8 组 |
| CMDB 变量 | OpsFlow 变量系统集成 (cmdb_variables.py) | ✅ 基础 |
| 变更追踪 | 资源变更历史记录 | 📅 规划 |
| 自动发现 | Agent 上报 + 轮询扫描自动更新 | 📅 规划 |

#### P0 — 高优先级
- [ ] **CMDB Neo4j 重构** — 完成模型驱动架构，替换 Mock 数据为真实 Neo4j 查询（当前已有 `Neo4jClient` 和 `Neo4jRouter` 基础设施，但模型定义和 CRUD 操作仍需完善）

---

### ITSM (⭐⭐⭐⭐☆)

**定位:** 事件管理、变更管理、审批流程。审批节点与 OpsFlow 深度集成，工单可触发编排流程。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| 工单管理 | 事件/服务请求/变更工单创建流转 | ✅ 基础 |
| 审批流 | 多级审批 + 会签 + 知会 | ✅ 基础 |
| 变更管理 | 变更申请/评估/审批/实施/回顾 | ✅ 基础 |
| 服务目录 | 定义可请求的 IT 服务项 | 📅 规划 |
| OpsFlow 集成 | 审批节点贯通 + 变更自动实施 | 🔄 完善中 |

#### P1 — 中优先级
- [ ] **ITSM OpsFlow 审批深度集成** — OpsFlow 审批节点与 ITSM 工单系统双向贯通（顶层设计参考: §5.2 P1）

---

### Monitor (⭐⭐⭐⭐☆)

**定位:** 告警检测 + 通知分发 + 自愈触发。复用外部监控系统（Prometheus），专注于告警聚合、通知路由、自愈闭环。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| AlertManager | 多源告警接入 → 去重 → 聚合 → 路由 | ✅ 基础 |
| Notification | 通知渠道 (钉钉/企微/邮件/短信) + 升级策略 | ✅ 基础 |
| SelfHealing | 告警 → 匹配策略 → 触发 OpsFlow 流程 | 🔄 完善中 |
| Strategy | 自愈策略配置 (条件 + 动作 + 生效时间) | ✅ 基础 |
| 自愈闭环 | 流程完成 → 更新告警状态 | 📅 规划 |

**代码验证:** `webhook_receivers.py` 中存在 `_trigger_pipeline()` 函数用于触发自愈流程，但未发现独立的 `SelfHealing` 服务模块。

#### P0 — 高优先级
- [ ] **Monitor 自愈闭环** — 自愈流程完成后自动更新告警状态，信号驱动（当前有 `_trigger_pipeline()` 触发入口，但缺少流程完成后的回调处理）

---

### Open API (⭐⭐⭐⭐☆)

**定位:** 平台对外的统一 API 出口，独立于 opsflow 核心。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| Token 认证 | Bearer Token 认证 (`OpenApiAuthentication`) | ✅ 完整 |
| 限流 | 按 ApiApp 配置的 QPS 限流 (`OpenApiRateThrottle`) | ✅ 完整 |
| 第三方应用管理 | ApiApp CRUD (`ApiAppViewSet`) | ✅ 完整 |
| Token 管理 | 创建/吊销/重新生成 (`OpenApiTokenViewSet`) | ✅ 完整 |
| 事件订阅 | Webhook 事件订阅管理 (`WebhookSubscriptionViewSet`) | ✅ 完整 |
| 调用日志 | API 调用记录 (`OpenApiLogViewSet`) | ✅ 完整 |
| Pipeline 端点 | 触发执行/查询状态/列出模板 | ✅ 完整（从 `opsflow/core/apigw/` 迁入） |
| CMDB 同步端点 | 外部资产推送 | ✅ 基础 |
| 健康检查 | 含认证应用信息 | ✅ 完整 |

**已完成 P0 Open API 独立化任务** — 无待办。

---

### Portal (⭐⭐⭐⭐☆)

**定位:** OpsWorks 首页仪表盘，聚合用户待办、系统概览和快捷入口。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| 首页仪表盘 | 用户待办、系统概览、快捷操作 | ✅ 完整 |

**TODO:** 无待办任务。

---

### Integration Hub (⭐⭐⭐⭐☆)

**定位:** 横向基础设施层，所有子产品的外部系统连接管理统一入口。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| 连接器管理 | 连接器注册/配置/版本管理 | ✅ 基础 |
| 协议适配 | REST / SOAP / SSH / SNMP / JDBC / gRPC 统一抽象 | 🔄 完善中 |
| 凭证管理 | 加密存储 + 自动注入 (`credential_service.py` 已实现 `encrypt_credential`/`decrypt_credential`) | ✅ 完整 |
| 运行监控 | 连接健康检查 + 调用统计 + 熔断/重试 | 📅 规划 |

**P0 凭证管理任务已由代码验证完成。**

---

### Job Platform (⭐⭐⭐☆☆)

**定位:** 脚本托管、批量分发、文件传输。与 OpsFlow 互补——OpsFlow 负责编排流程，Job Platform 负责单次批量执行。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| 脚本管理 | 脚本版本管理/语法检查/参数定义 | ✅ 基础 |
| 作业执行 | 脚本分发 → 目标执行 → 结果收集 (`services/executor.py` 25 个方法) | ✅ 基础 |
| 文件分发 | 源 → 目标文件传输 | 🔄 完善中 |
| 执行账户 | SSH Key/密码管理，执行身份控制 | 📅 规划 |

#### P2 — 低优先级
- [ ] **Job Platform SSH 执行器完善** — 连接池 + 密钥管理 + 批量分发（顶层设计参考: §5.2 P2）

---

### OpsAgent (⭐⭐⭐☆☆)

**定位:** 基于 DeepSeek 的对话式运维界面，自然语言 → 工具调用 → 操作执行。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| Session | 对话会话管理 (上下文/历史/状态) | ✅ 基础 |
| AgentMemory | 持久化经验记忆 (故障模式/操作经验) | ✅ 基础 |
| ToolRegistry | 工具注册 (`auto_discover()` 自动发现) | ✅ 基础 |
| AuditRecord | 风险评估 (操作 × 环境 × 影响半径) | ✅ 基础 |
| 多轮操作 | 通过对话完成复杂多步运维操作 | 📅 规划 |

#### P1 — 中优先级
- [ ] **OpsAgent 工具链完善** — 更多 Tool: CMDB 查询/ITSM 工单/Monitor 告警（顶层设计参考: §5.2 P1）

---

### Agent 远程程序 (⭐⭐☆☆☆)

**定位:** 运行在目标主机上的 Agent 程序，负责命令执行、数据采集、心跳上报。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| Agent 注册 | Agent → Server 注册和认证 | 📅 规划 |
| 命令执行 | 接收 Server 指令 → 执行 → 返回结果 | 📅 规划 |
| 数据采集 | 主机信息/进程/日志采集上报 | 📅 规划 |
| 心跳保活 | 定期心跳 + 离线检测 | 📅 规划 |

**代码验证:** `backend/agent/` 目录存在但内容为通用 Python 包，非 Django app（未注册 INSTALLED_APPS）。

#### P2 — 低优先级
- [ ] **Agent 远程程序** — Agent 注册/心跳/命令下发/数据采集（顶层设计参考: §5.2 P2）

---

### CI/CD + K8s (⭐☆☆☆☆)

**定位:** OpsFlow 平台自身的持续集成与 Kubernetes 部署支持。

| 模块 | 职责 | 状态 |
|------|------|:----:|
| CI/CD Pipeline | GitHub Actions / GitLab CI | 📅 规划 |
| K8s 部署 | Helm Chart / Operator | 📅 规划 |

#### P2 — 低优先级
- [ ] **CI/CD + K8s 部署支持** — Helm Chart / Operator / GitOps 集成（顶层设计参考: §5.2 P2）
