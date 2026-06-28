# Job Platform — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐☆☆ (3/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | SSH 执行器不完整，Agent 执行通道待集成，文件分发功能不完整，执行账户管理未实现 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 作业模板 CRUD | P0 | ✅ | 模板管理 | Template + Plan + Variable 模型完整，business FK 新增 |
| 脚本管理 | P0 | ✅ | 脚本版本管理 | Script + ScriptVersion，语法检查(dangerous_detector)，14 条内置高危规则 |
| 步骤系统 | P0 | ✅ | 多步骤编排 | Step/ScriptStep/FileStep/ApprovalStep，三选一互斥 |
| 作业执行 | P1 | 🔄 | 执行结果收集 | JobExecution/StepExecution 模型就绪，<b>_resolve_targets() 返回空列表</b> 阻塞 Host 执行 |
| SSH 执行器 | P1 | 🔄 | 远程 SSH 执行 | paramiko 基础框架齐全，URL 访问检查(SSH_ACCESS_URL)，<b>批量分发未完成</b> |
| Agent 执行器 | P1 | 🔄 | Agent 远程执行 | AgentExecutor 框架(48 行)，<b>未完整继承 SSH 的 execute 逻辑</b> |
| 文件分发 | P1 | 🔄 | 文件传输 | FileStep 模型就绪，<b>分发逻辑未实现</b> |
| 执行账户 | P2 | 📅 | SSH Key/密码管理 | Account 模型存在(scope/type/account/vault_id)但<b>无 vault/加密集成</b> |
| CronJob 定时执行 | P2 | 🔄 | 定时作业 | CronJob + CronJobExecution 模型就绪，执行逻辑未连接 |
| 危险命令检测 | P1 | ✅ | 内置规则 | dangerous_detector 完整，14 条规则+webhook 日志 |
| OpsFlow 集成 | P2 | 🔄 | 作为原子插件集成 | 插件 agent_exec_cmd/file_push 存在，通过 Job Platform 调度未实现 |
| 前端页面 | P1 | ✅ | 基础页面 | Script Console + Execution Panel + File Transfer 视图存在 |
| 多租户隔离 | P2 | ✅ | Business FK | template 模型已加 business FK |

## TODO

### P0
- [ ] 修复 _resolve_targets() 返回空列表问题

### P1
- [ ] SSH 执行器批量分发完整
- [ ] Agent 执行器完整继承
- [ ] 文件分发实现

### P2
- [ ] 执行账户管理 + vault 集成
- [ ] CronJob 定时执行
- [ ] OpsFlow 原子插件集成
- [ ] 补充测试用例
