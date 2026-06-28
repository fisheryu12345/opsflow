# Agent (远程执行) — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md
> 注意：由 Go Agent (agent/) + Django agent_app (agent_app/) + OpsFlow 插件 三层组成

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐☆☆☆ (2/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | 通信链路完整(Python→Go Server→Go Agent)，但批量纳管、文件Pull、实时推送、升级编排缺失 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| Agent 注册认证 | P0 | ✅ | Agent → Server 注册 | WS 全链路(register→heartbeat→reconnect)，AgentInstance 模型完整 |
| 命令执行 (exec) | P0 | ✅ | 接收指令→执行→返回 | Executor(shell/python/bat/powershell) + Timeout + 截断，agent_app→Go Server→Agent WS→结果回写 |
| 心跳保活 | P0 | ✅ | 心跳+离线检测 | 30s 心跳 ticker，90s 超时断开，Agent Server 状态追踪 |
| 主机信息采集 | P1 | ✅ | 主机数据采集 | Collector(hostname/IP/OS/CPU/Memory/Disk) → CMDB Neo4j |
| 进程信息采集 | P1 | ✅ | 进程/服务采集 | ProcCollector(ps aux+ss+systemctl) → CALLS 拓扑自动发现 |
| 文件推送 (Push) | P1 | ✅ | 文件分发 | Agent Server 4MB chunk + SHA256 + 4 并发下载 |
| Agent Server REST API | P1 | ✅ | Django 面对的 HTTP 接口 | 4 端点(exec/file_push/apps/health) |
| AgentInstance CRUD | P1 | ✅ | Agent 管理 | 6 个 ViewSets，内部 API auth-exempt |
| CMDB 同步 | P1 | ✅ | 采集数据→Neo4j | Host/Process/Application 节点 + RUNS_ON + CALLS + HAS_PROCESS |
| OpsFlow 原子插件 | P1 | ✅ | 流程编排调用 | 7 个 agent 插件(exec_cmd/file_push/file_pull/process_start/stop/restart/status) |
| 文件上传 Pull | P1 | 🔄 | 从 Agent 拉文件 | Uploader handler 未组装，server 端 pull endpoint 不存在 |
| 批量纳管 (push_install) | P2 | 🔄 | SSH 自动部署 Agent | paramiko 上传+配置+启动，<b>批量批量执行未完成</b> |
| 升级编排 | P2 | 🔄 | Agent 版本升级 | UpgradeManager(Go 端完整)，Django Upgrade 模型+API 就绪，<b>无升级触发 UI/API</b> |
| 重连网关 (Gateway) | P2 | ✅ | 跨网段代理 | Gateway 模式完整(Go)，本地 WS 代理 |
| 实时推送结果 | P2 | 📅 | WebSocket→前端 | TaskResult.pushed_at 字段就绪，<b>无前端 WS/SSE 推送实现</b> |
| Windows/AIX 支持 | P2 | 🔄 | 跨平台安装 | service install stub(仅 log warning) |
| 内网 API 认证 | P0 | 📅 | Server→Django 认证 | csrf_exempt + 无 token 校验，APIToken 字段存在<b>未验证</b> |
| 流式命令输出 | P2 | 🔄 | 实时结果流 | Seq/IsFinal 字段就绪，<b>实际仅返回一次 final</b> |
| TLS/加密 | P2 | 📅 | wss:// 加密 | Server TLS config 就绪(注释状态)，Agent 无 TLS |
| 文件上传批量写回 | P2 | 📅 | 批量结果回写 | BackendClient 已实现(50条/2s)，Django batch_results 端点就绪 |
| 前端页面 | P1 | ✅ | Agent 管理界面 | List/Install/Execution/FilePush 视图完整，i18n 中英各 97 key |
| 多租户隔离 | P2 | 📅 | biz_id 隔离 | AgentInstance.biz_id 字段就绪，<b>internal_views 无条件过滤</b> |

## TODO

### P0
- [ ] internal_views 添加 APIToken 校验（当前 csrf_exempt 无认证）
- [ ] 修复 agent_file_pull 插件（server 端无 pull endpoint）

### P1
- [ ] 批量 Agent 纳管（当前 push_install 单台）
- [ ] 升级编排 UI/API（Go 端完整，Django 缺触发层）
- [ ] 实时结果流（Seq/IsFinal 字段已设计，仅返回一次 final）
- [ ] 文件 Pull 实现

### P2
- [ ] 内网 API 认证
- [ ] Windows/AIX 安装脚本
- [ ] TLS 加密通信
- [ ] 前端实时推送
- [ ] 流式输出完善
- [ ] 多租户隔离
- [ ] 补充测试用例
