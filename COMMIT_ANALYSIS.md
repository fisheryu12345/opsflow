# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## ed7cb503

> 提交日期: 2026-06-15 | 提交信息: feat: implement opsflow-agent system — Go Agent + Server + Django integration

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/agent/` | 后端 | Go Agent Server + Agent daemon 核心实现（14个Go包） |
| `backend/agent_app/` | 后端 | Django App（6个模型，ViewSets，内部API） |
| `backend/opsflow/plugins/agent/` | 后端 | OpsFlow原子插件（3个：exec_cmd/file_push/file_pull） |
| `backend/job_platform/` | 后端 | AgentExecutor远程执行通道替代SSH |
| `backend/application/` | 后端 | 注册agent_app到Django |
| `backend/common/` | 后端 | Agent管理菜单seed数据 |
| `backend/agent-py/` | 后端 | Python Agent备份（重命名） |
| `web/src/views/apps/agent/` | 前端 | Agent管理页面（列表/安装/执行/文件推送） |
| `web/src/api/agent/` | 前端 | Agent API客户端 |
| `web/src/i18n/lang/` | 前端 | Agent页国际化（中/英各97个key） |
| `docs/superpowers/specs/` | 文档 | Agent设计文档 |

### 解决

- **问题/背景：** OpsFlow缺少远程Agent基础设施，远程执行依赖SSH（paramiko），无法做到指令推送、实时结果流、文件传输和主机端数据采集
- **办法：** 用Go实现类蓝鲸GSE的Agent组件体系（Server + Agent + Gateway三层架构），替换SSH成为远程执行首选通道

### 未实现 TODO

以下是本次提交中已规划但未实现的功能，供后续迭代参考：

1. **应用进程管理（后续需求）**：应用进程的启动/停止/重启/状态查看不在本计划范围内。待Phase 2交付 + CMDB Process模型定义完成后，作为独立迭代实现。实现路径：OpsFlow新增 agent_process_start / agent_process_stop / agent_process_status / agent_process_restart 原子插件（底层复用agent_exec_cmd）+ Agent详情页进程操作界面

2. **文件传输完整链路**：Agent Server分块存储 → WS通知Agent → Agent并发HTTP拉取chunks → sha256校验 → 合并 → 结果回流。当前已完成Django上传端和Agent Server coordinator框架，但Agent端file_push handler的完整DownloadFile调用尚需验证

3. **Agent Server后端批量写回**：command_result的batch_results内网端点已创建，但Agent Server的handleCommandResult尚未调用backend.Push()，需在ws/server.go中接入

4. **子进程管理器（Subproc Manager）**：Agent subproc模块的框架已建，但exporter生命周期管理（安装/启动/守护/升级）未实现

5. **Agent热升级端到端**：升级协议已定义（upgrade消息类型），Agent端upgrade manager已实现下载/校验/进程替换逻辑，但Server端的upgrade API和Django AgentUpgrade模型尚未对接完整链路

6. **Gateway跨站点模式**：Gateway核心代码（gateway.go）已实现，但未经过端到端测试验证

7. **CMDB采集数据写入Neo4j**：Agent collector已采集host_info，Django internal_views已接收reports，但尚未对接CMDB Service写入Neo4j

8. **Windows/AIX Agent安装包**：跨平台编译Makefile已建，但Windows Service注册和AIX SRC注册的install.sh尚未完善

### 验证

- 改动类型: feat
- 清理乱码: 有（build/目录下的二进制exe文件）
- 子App index.md 更新: agent_app（需要时更新）
- 工作区状态: 干净 ✅
