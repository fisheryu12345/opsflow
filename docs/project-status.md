# OpsFlow IT 智能管控平台 — 项目状态

> 最后更新: 2026-06-05
> 覆盖: 后端 12 个 Django App, 前端 20+ 功能模块

---

## 总体成熟度

```
模块                   成熟度    后端  前端  关键缺口数
─────────────────────────────────────────────────────
OpsFlow 流程引擎        ★★★★★   ✅   ✅   3
RBAC/系统管理           ★★★★★   ✅   ✅   2
Monitor 监控告警中心    ★★★★☆   ✅   ✅   4
CMDB 配置管理           ★★★★☆   ✅   ✅   3
ITSM 服务管理           ★★★★☆   ✅   ✅   4
Portal 门户             ★★★★☆   ✅   ✅   2
OpenAPI 开放API         ★★★★☆   ✅   ✅   2
Job Platform 作业平台   ★★★☆☆   ✅   ⚠️   5
OpsAgent 运维代理       ★★★☆☆   ✅   ⚠️   4
OAuth2/SSO             ★★★☆☆   ✅   ✅   3
Knowledge 知识库        ★★★☆☆   ✅   ✅   3
Integration 集成中心    ★★★☆☆   ✅   ❌   5
CI/CD + K8s            ★☆☆☆☆   ❌   ❌   6
```

---

## 各模块详情

### 1. OpsFlow 流程引擎 — ★★★★★

**状态：生产就绪 | 40+ API 端点 | 20+ 插件 | 12 看板端点**

| 子模块 | 状态 |
|--------|------|
| 项目管理 (OpsProject/Member/Env) | ✅ 完备 |
| 模板管理 (FlowTemplate/Version/Category/Collect) | ✅ 完备 |
| 模板编辑器 (Canvas/PropertyPanel/PluginPicker/VariableBrowser) | ✅ 完备 |
| AI 辅助 (生成/Diff/布局/优化) | ✅ 中等 |
| 变量系统 (Mako 引擎/CMDB 变量/注册中心) | ✅ 完备 |
| 插件系统 (20+ 插件 Ansible/Redfish/ESXi/NetApp/ServiceNow/HTTP/Monitor/CMDB/ITSM) | ✅ 丰富 |
| ITSM 插件 (create_ticket / update_ticket) | ✅ 新增 |
| 执行引擎 (启/停/重试/跳过/子流程/DryRun) | ✅ 完备 |
| 调度器 (Cron/一次性/CMDB触发/APScheduler) | ✅ 完备 |
| Webhook (HMAC 签名/重试/触发事件) | ✅ 完备 |
| 看板统计 (12 端点) | ✅ 丰富 |
| 审计日志 (OperationRecord/OpsLog/TraceLogger) | ✅ 完备 |
| 内部/外部 API 网关 | ✅ 中等 |
| 知识库 (向量搜索 / semantic_search) | ✅ 新增 |

**剩余缺口：**
- 插件市场 / 自定义插件 SDK（大）
- 模板 Git 版本化（中）
- 多人实时协作编辑（大）

---

### 2. RBAC & 系统管理 — ★★★★★

**状态：生产就绪 | 16 个 ViewSet**

| 功能 | 状态 |
|------|------|
| 用户/角色/部门/菜单/岗位 CRUD | ✅ 完备 |
| 按钮级权限 + 字段级权限 + 数据权限范围 | ✅ 完备 |
| JWT 认证 + 验证码登录 | ✅ 完备 |
| OAuth2/SSO (OIDC/企业微信/钉钉) | ✅ 新增 |
| 登录页 SSO 按钮 | ✅ 新增 |
| 字典/系统配置/文件管理 | ✅ 完备 |
| 登录日志/操作日志/消息中心 | ✅ 完备 |
| API 白名单 | ✅ 完备 |

**剩余缺口：**
- LDAP/AD 登录（中）
- MFA/双因素认证（大）

---

### 3. Monitor 监控告警中心 — ★★★★☆

**状态：新架构 | 19 张表 | 42 后端文件 | 10 Tab 前端 | 14 种算法**

| 功能 | 状态 |
|------|------|
| 策略四层模型 (Strategy→Item→QueryConfig→Detect→Algorithm) | ✅ 完备 |
| 告警事件分离 (AlertEvent / Alert / AlertLog) | ✅ 完备 |
| 通知组 + 值班计划 + 排班明细 | ✅ 完备 |
| 分派规则组 + 规则 + 动作插件 | ✅ 完备 |
| 屏蔽计划 + 采集配置 | ✅ 完备 |
| 告警管道 6 阶段 (Clean→Match→Build→Shield→Converge→Dispatch) | ✅ 完备 |
| 14 种检测算法 (阈值/环比/同比/振幅/智能检测/时序预测/节点/重启/Ping/端口) | ✅ 完备 |
| Webhook 接收 (Prometheus/Grafana/自定义推流) | ✅ 完备 |
| MonitorScheduler (4 个定时任务) | ✅ 完备 |
| 数据源适配器 (Prometheus/InfluxDB/自定义) | ✅ 完备 |
| 通知适配器 (企业微信/钉钉/邮件/SMS/集成中心) | ✅ 完备 |
| 动作适配器 (OpsFlow/AWX/ITSM) | ✅ 完备 |
| 目标解析器 (CMDB/静态) | ✅ 完备 |
| 种子数据 (seed_monitor 7 内置 ActionPlugin) | ✅ 完备 |
| 前端 10 Tab 页面 | ✅ 完备 |
| 策略创建 4 步向导 (StrategyWizard.vue) | ✅ 新增 |
| 前端看板 (ECharts 趋势图) | ✅ 完备 |

**剩余缺口：**
- K8s 集群监控（大）
- 日志告警（大）
- ML 智能异常检测/预测（大）

---

### 4. CMDB 配置管理数据库 — ★★★★☆

**状态：Beta+ | 模型抽象层 + Neo4j 实例层 + 拓扑引擎**

| 功能 | 状态 |
|------|------|
| 模型分类/模型定义/字段/属性分组/关联类型/关联/唯一约束 | ✅ 完备 |
| 主线上拓扑 (Biz→Set→Module→Host) | ✅ 完备 |
| 实例动态 CRUD (Cypher 驱动 / 动态序列化) | ✅ 完备 |
| 实例关联 CRUD + 邻居遍历 | ✅ 完备 |
| 拓扑查询 (力导向图/子树展开/影响分析/全局搜索) | ✅ 完备 |
| 批量导入 (CSV/JSON) | ✅ 完备 |
| CI 变更历史追踪 (字段级 diff) | ✅ 新增 |
| CI 事件订阅 Webhook | ✅ 新增 |
| Excel 导入导出 (openpyxl) | ✅ 新增 |
| 种子数据 (内置模型/字段/拓扑) | ✅ 完备 |

**剩余缺口：**
- 云同步适配器（阿里云/腾讯云/AWS 空壳）（中）
- 资源池/区域管理（小）
- 配置合规/漂移检测（大）

---

### 5. ITSM 服务管理 — ★★★★☆

**状态：Beta | 工作流引擎 + 工单生命周期 + SLA**

| 功能 | 状态 |
|------|------|
| Incident/Change/ServiceRequest/Problem CRUD | ✅ 完备 |
| 工作流 9 种节点类型 (START/END/APPROVAL/SIGN/TASK/ROUTER_P/COVERAGE/WEBHOOK) | ✅ 完备 |
| WorkflowVersion 版本/部署/回滚 | ✅ 完备 |
| Ticket 完整生命周期 (草稿→运行→挂起→完成→终止→失败) | ✅ 完备 |
| SLA 引擎 + 优先级矩阵 | ✅ 完备 |
| 处理器解析 (人员/发起人/上级/角色/组织/变量) | ✅ 完备 |
| 审批委托 (ApprovalDelegate) | ✅ 新增 |
| 通知渠道 (企业微信/钉钉/邮件/站内信) | ✅ 新增 |
| ITSM 看板 (统计卡片/趋势图/待办/超时) | ✅ 新增 |
| ITSM↔OpsFlow 打通 (审批触发流程) | ✅ 新增 |
| OpsFlow 插件 (创建/更新 ITSM 工单) | ✅ 新增 |
| ITSM 前端 (Dashboard / Delegation) | ✅ 新增 |

**剩余缺口：**
- 服务目录（中）
- 工单模板（小）
- 满意度评价/CSAT（小）

---

### 6. Portal 门户 — ★★★★☆

**状态：中等 | 跨模块聚合仪表盘**

| 功能 | 状态 |
|------|------|
| dashboard_summary (跨模块统计) | ✅ 完备 |
| my_tasks (待办聚合) | ✅ 完备 |
| recent_activity (活动流) | ✅ 新增 |
| favorites (收藏夹) | ✅ 新增 |
| health (系统健康) | ✅ 新增 |
| 前端门户页 (统计卡片/活动流/收藏/快捷操作) | ✅ 新增 |

**剩余缺口：**
- 全局搜索（大）
- 可配置小部件（中）

---

### 7. OpenAPI 开放API — ★★★★☆

**状态：Beta | Token 认证 + 频率限制**

| 功能 | 状态 |
|------|------|
| ApiApp/OpenApiToken/WebhookSubscription/OpenApiLog | ✅ 完备 |
| 外部 API (health/cmdb_sync/create_incident/trigger_execution) | ✅ 完备 |
| Bearer Token 认证 | ✅ 新增 |
| 频率限制 (滑动窗口 QPS) | ✅ 新增 |
| IP 白名单 | ✅ 新增 |
| Token 续期 | ✅ 新增 |

**剩余缺口：**
- Swagger/OpenAPI 文档（小）
- 出站 Webhook 签名（中）

---

### 8. Job Platform 作业平台 — ★★★☆☆

**状态：Alpha | 模型完整 + 执行器新增 + SSH 连接池**

| 功能 | 状态 |
|------|------|
| Script/JobDefinition/JobExecution/CronJob/Account 模型 | ✅ 完备 |
| DangerousCmdRule 危险命令检测 (14 规则) | ✅ 完备 |
| SSH 执行器 (paramiko 连接池 + subprocess 回退) | ✅ 新增 |
| Ansible 执行器 (ansible-runner + CLI 回退) | ✅ 新增 |
| 本地执行器 (subprocess) | ✅ 新增 |
| 变量渲染 ({{ var }} / \${var} / \$var) | ✅ 新增 |
| 执行 API (execute / status) | ✅ 新增 |
| 19 个 API 端点 | ✅ 完备 |
| 前端基础页面 | ⚠️ 基础 |

**剩余缺口：**
- 目标解析存根 `_resolve_targets()` 返回空列表（中）
- 审批步骤未对接 ITSM（中）
- 文件分发未实现 SFTP（中）
- 无 WebSSH 终端（中）
- 无跳板机支持（中）

---

### 9. OpsAgent 运维代理 — ★★★☆☆

**状态：Alpha | 5 工具 + 安全审计 + REPL**

| 功能 | 状态 |
|------|------|
| EnvironmentContext 环境定义 | ✅ 完备 |
| Session REPL + 一次性执行 | ✅ 完备 |
| AuditRecord 风险评分 | ✅ 完备 |
| AgentMemory 持久化 | ✅ 完备 |
| 5 工具 (ssh_exec/local_exec/cmdb_query/opsflow_trigger/monitor_query) | ✅ 完备 |
| CMDB 查询工具 (search_instances/get_topology/global_search) | ✅ 新增 |
| OpsFlow 触发工具 (list_templates/trigger_execution/get_status) | ✅ 新增 |
| Monitor 查询工具 (list_alerts/get_detail/alert_summary) | ✅ 新增 |
| 前端 Console + Sessions | ⚠️ Alpha |

**剩余缺口：**
- 无 RAG (知识库未接入 Agent)（中）
- 无自然语言执行（小）
- 无 WebSocket 流式输出（中）
- 无 ITSM 工单工具（小）

---

### 10. OAuth2/SSO — ★★★☆☆

**状态：Alpha | 3 Provider + JWT 签发**

| 功能 | 状态 |
|------|------|
| OIDC Provider (通用 OIDC 兼容 Keycloak/Okta/Azure AD) | ✅ 新增 |
| 企业微信扫码登录 | ✅ 新增 |
| 钉钉扫码登录 | ✅ 新增 |
| 首次登录自动创建用户 | ✅ 新增 |
| CSRF state 保护 | ✅ 新增 |
| 前端 SSO 按钮 | ✅ 新增 |

**剩余缺口：**
- LDAP/AD 登录（中）
- SAML（大）
- MFA/2FA（大）

---

### 11. Knowledge 知识库 — ★★★☆☆

**状态：Alpha | 向量嵌入 + 语义搜索**

| 功能 | 状态 |
|------|------|
| OpsKnowledge 模型 (title/content/tags/embedding) | ✅ 完备 |
| VectorService (sentence-transformers + TF-IDF 回退) | ✅ 新增 |
| 余弦相似度搜索 | ✅ 新增 |
| index_knowledge 管理命令 | ✅ 新增 |
| semantic_search API 端点 | ✅ 新增 |
| 种子知识数据 | ⚠️ 基础 |

**剩余缺口：**
- 外部源导入 (Confluence/Notion)（大）
- 工单解决后自动提取知识（大）
- 知识审批工作流（中）

---

### 12. Integration 集成中心 — ★★★☆☆

**状态：Alpha | 连接器框架 + 凭据管理**

| 功能 | 状态 |
|------|------|
| ConnectorDefinition/ConnectorInstance/ConnectorCredential | ✅ 完备 |
| AES-256 凭据加密存储 | ✅ 完备 |
| 健康检查框架 | ✅ 完备 |
| 基础适配器框架 | ✅ 完备 |
| AI 适配器 (OpenAI/Anthropic) | ✅ 完备 |
| 通知适配器 (企业微信/钉钉/邮件/SMS) | ✅ 完备 |
| 阿里云适配器 | ⚠️ 存根 (需 SDK) |

**剩余缺口：**
- 阿里云适配器未接入真实 SDK（中）
- 无 AWS/Azure/GCP 适配器（中）
- 无连接器市场（大）
- 无 Webhook 接收器（中）

---

### 13. CI/CD + K8s — ★☆☆☆☆

**状态：完全缺失 | 平台最大空白**

| 功能 | 状态 |
|------|------|
| K8s 资源监控 (Pod/Node/Deployment/Event) | ❌ |
| K8s 告警 (OOMKiller/CrashLoopBackOff) | ❌ |
| Jenkins/GitLab CI/GitHub Actions 集成 | ❌ |
| 容器注册表集成 (Harbor/Docker Hub) | ❌ |
| 部署流水线 (蓝绿/金丝雀) | ❌ |
| Helm chart 管理 | ❌ |

---

## 文件统计

| 模块 | 后端文件 | 前端文件 | API 端点 |
|------|---------|---------|---------|
| dvadmin (RBAC) | ~30 | 20+ | 50+ |
| opsflow (引擎) | ~80 | 30+ | 40+ |
| monitor (监控) | 42 | 7 | 16+ |
| cmdb (配置管理) | ~30 | 5 | 20+ |
| itsm (服务管理) | ~25 | 5 | 20+ |
| opsagent (代理) | ~15 | 2 | 5 |
| job_platform (作业) | ~15 | 1 | 19 |
| integration (集成) | ~15 | 1 | 5 |
| iam (权限) | ~5 | 2 | 6 |
| open_api (开放) | ~8 | 1 | 8 |
| portal (门户) | ~3 | 1 | 6 |
| **总计** | **~300+** | **~80+** | **~200+** |

---

## 下一阶段建议

### P3 — 打磨优化（短平快）
1. **Job 目标解析** — 打通 CMDB 到 Job 的主机选择链（3-5天）
2. **Job 审批步骤** — 对接 ITSM 审批流程（2-3天）
3. **Job 文件分发** — paramiko SFTP 传输实现（2-3天）
4. **Swagger 文档** — drf-spectacular 集成（1天）
5. **OAuth state 存 Redis** — 生产环境加固（1天）

### P4 — 平台扩展（重量级）
1. **K8s 监控模块** — Pod/Node/Event 监控 + 告警（2-3周）
2. **CI/CD 流水线对接** — Jenkins/GitLab CI 插件（1-2周）
3. **云同步适配器** — 阿里云/AWS SDK 接入（1周）
4. **LDAP/AD 登录**（3-5天）
5. **全局搜索** — 跨模块统一搜索（1周）
