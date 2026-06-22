# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## df82a1c9

> 提交日期: 2026-06-17 | 提交信息: feat: implement CMDB hierarchy refactor — Service→Application→Process model

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | 后端 | 新增 Application ModelDefinition + HAS_PROCESS/PROTECTED_BY 关联/模型关联种子数据 |
| `backend/agent_app/internal_views.py` | 后端 | `_sync_applications()` 同步 Application 节点 + HAS_PROCESS; `_match_calls_topology()` 建立 Application 级 CALLS |
| `backend/agent_app/apps.py` | 后端 | 实现 `get_registry_pids()` 修复死代码 |
| `backend/opsflow/services/dr_service.py` | 后端 | DR 拓扑查询改为 Application 级; neighbors_to_pipeline() 使用 Application 名 + host_ip |
| `backend/opsflow/views/mixins/template_dr.py` | 后端 | 修复 `_get_llm_client()` 解包错误 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | DR 拓扑改为选中 Group 后才加载; 边过滤新增 PROTECTED_BY/HAS_PROCESS |
| `docs/cmdb/features/` | 文档 | Application 模型层次重构文档 |
| `docs/opsflow/features/` | 文档 | DR Pipeline 适配文档 |
| `backend/seed_monitor_dr.py` | 脚本 | 监控业务 DR mock 数据种子脚本 |
| `backend/clean_neo4j.py` | 脚本 | Neo4j 无效数据清理脚本 |
| `.gitignore` | 配置 | 忽略 backend/logs/ |

### 解决

- **问题/背景：** CMDB 模型扁平化在 Process(PID)级，DrGroup 直接关联 Process，CALLS 在 4 个 nginx worker 间毫无意义；缺少 Application 层承载启停语义和 DR 拓扑
- **办法：** 新增 `:Application` Neo4j 节点 + HAS_PROCESS/PROTECTED_BY 关系，将 CALLS 和 DR 关联提升到 Application 层；修复 LLM 客户端调用；前端 DR 拓扑改为 Group 选择后才加载

### 文档

- **生成文档：**
  - `docs/cmdb/features/2026-06-17-application-model-hierarchy.md`
  - `docs/opsflow/features/2026-06-17-dr-pipeline-adapter.md`

### 验证

- 改动类型: feat+refactor+fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

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

1. **应用进程管理**：应用进程的启动/停止/重启/状态查看不在本计划范围内
2. **文件传输完整链路**：Agent Server分块存储 → WS通知Agent → Agent并发HTTP拉取chunks → sha256校验 → 合并
3. **Agent Server后端批量写回**：command_result的batch_results内网端点已创建，但Agent Server的handleCommandResult尚未调用backend.Push()
4. **子进程管理器**：Agent subproc模块的框架已建，但exporter生命周期管理未实现
5. **Agent热升级端到端**：升级协议已定义，但Server端的upgrade API和Django AgentUpgrade模型尚未对接
6. **Gateway跨站点模式**：Gateway核心代码已实现，但未经过端到端测试验证
7. **CMDB采集数据写入Neo4j**：Agent collector已采集host_info，Django internal_views已接收reports，但尚未对接CMDB Service写入Neo4j
8. **Windows/AIX Agent安装包**：跨平台编译Makefile已建，但Windows Service注册和AIX SRC注册的install.sh尚未完善

### 验证

- 改动类型: feat
- 清理乱码: 有（build/目录下的二进制exe文件）
- 子App index.md 更新: agent_app（需要时更新）
- 工作区状态: 干净 ✅
