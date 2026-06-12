# job_platform — 模块索引

> 上次自动更新: 2026-06-12

---

## `job_platform/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Job platform app package |
| `admin.py` |  | feat(job-platform): create batch execution and command contr |
| `apps.py` | Apps config for job_platform | `JobPlatformConfig` |
| `serializers.py` | Serializers for job_platform app — 所有模型序列化器 | `AccountSerializer`<br>`AccountCreateUpdateSerializer`<br>`FileSourceSerializer`<br>`ScriptSerializer`<br>`ScriptCreateUpdateSerializer`<br>`ScriptVersionSerializer` |
| `tasks.py` | Celery tasks for job_platform — AI detection + execution engine | `ai_script_check()` — AI 语义检测脚本安全性（异步）<br>`job_start_task()` — 作业执行入口 — 初始化并启动第一个步骤<br>`step_exec_task()` — 执行单个步骤 |
| `urls.py` |  | URL configuration for job_platform app |

## `job_platform\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Re-export all models for job_platform app |
| `models.py` | Job platform — batch execution, script management, file distribution | `Script` — 脚本管理<br>`JobDefinition` — 作业定义 — 可在多台主机上执行的任务模板<br>`JobExecution` — 作业执行记录<br>`DangerousCmdRule` — 高危命令规则 — 关键词/正则匹配，拦截或审批 |

## `job_platform\models\subs/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(job-platform): complete backend + frontend implementati |
| `base.py` | Base/shared models — Account, FileSource, DangerousCmdRule, DangerousCheckLog | `Account` — 执行账号 — SSH/数据库凭据，AES 加密存储<br>`FileSource` — 文件源 — S3/FTP/Samba/NFS 等预配置数据源<br>`DangerousCmdRule` — 高危命令检测规则 — 关键字/正则匹配，拦截/审批/警告<br>`DangerousCheckLog` — 高危命令检测记录 — 每次检测的详细日志 |
| `cron.py` | Cron models — CronJob, CronJobExecution | `CronJob` — 定时作业 — Cron 调度任务<br>`CronJobExecution` — 定时作业执行历史 |
| `execution.py` | Execution models — JobExecution, StepExecution | `JobExecution` — 作业执行实例 — 记录一次完整的作业执行过程<br>`StepExecution` — 步骤执行记录 — 单个步骤的执行详情 |
| `script.py` | Script models — Script, ScriptVersion, ScriptReference | `Script` — 脚本管理 — 可复用的执行脚本单元<br>`ScriptVersion` — 脚本版本 — 语义化版本管理<br>`ScriptReference` — 脚本引用追踪 — 记录脚本被哪些模板/方案引用 |
| `step.py` | Step models — Step, ScriptStep, FileStep, ApprovalStep | `Step` — 步骤 — 双向链表节点，支持 script/file/approval 三种类型<br>`ScriptStep` — 脚本步骤 — 脚本执行相关的详细配置<br>`FileStep` — 文件步骤 — 文件分发相关的详细配置<br>`ApprovalStep` — 审批步骤 — 人工审批相关配置 |
| `template.py` | Template/Plan models — Template, Plan, Variable | `Template` — 作业模板 — 可编排多步骤的作业定义模板<br>`Plan` — 执行方案 — 从模板派生的可执行配置<br>`Variable` — 全局变量 — 模板/方案级别的参数变量 |

## `job_platform\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for job_platform |
| `dangerous_cmd.py` | Dangerous command detection service | `check_dangerous_command()` — 检查命令是否高危，返回 {safe, blocked, action, reason} |
| `dangerous_detector.py` | Dangerous command detector — Rule engine + AI semantic analysis | `check_script_safety()` — 双层检测入口：规则引擎 → AI<br>`build_ai_check_prompt()` — 构建 AI 检测 Prompt<br>`sync_builtin_rules()` — 将内置规则同步到数据库（启动时调用） |
| `executor.py` | Job execution engine — JobExecutor class + Plan / Quick execution support | `JobExecutor` — 作业执行器 — 支持 SSH / Local / Ansible 三种执行方式<br>`async_execute()` — Execute job asynchronously in background thread — 后台异步执行作业<br>`async_execute_plan()` — Execute plan asynchronously (backward-compatible) — 异步执行方案（兼容旧接口）<br>`async_execute_job()` — Quick execute asynchronously (backward-compatible) — 异步快速执行（兼容旧接口） |
| `ssh_client.py` | SSH connection manager — Connection pooling, auth, command execution | `SSHConnectionPool` — Thread-safe SSH connection pool — 线程安全的 SSH 连接池<br>`SSHClient` — SSH client wrapper — 封装 paramiko 的 SSH 客户端<br>`SSHClientError` — SSH client base exception — SSH 客户端基础异常<br>`close_all_connections()` — Close all connections in the global pool — 关闭全局连接池所有连接 |

## `job_platform\tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(job-platform): complete backend + frontend implementati |
| `test_api.py` | Tests for job_platform API endpoints | `BaseAPITest` — API 测试基类 — 创建认证用户<br>`ScriptAPITest` — 脚本管理 API 测试<br>`TemplateAPITest` — 模板管理 API 测试<br>`AccountAPITest` — 账号管理 API 测试<br>`ExecutionAPITest` — 执行管理 API 测试<br>`DangerousRuleAPITest` — 高危命令规则 API 测试 |
| `test_models.py` | Tests for job_platform models | `AccountModelTest` — 账号模型测试<br>`ScriptModelTest` — 脚本模型测试<br>`TemplatePlanModelTest` — 模板/方案模型测试<br>`StepChainModelTest` — 步骤链表模型测试<br>`JobExecutionModelTest` — 执行实例模型测试<br>`DangerousCmdRuleModelTest` — 高危命令规则模型测试 |
| `test_services.py` | Tests for job_platform services — dangerous detector, executor | `DangerousDetectorTest` — 高危命令双层检测测试<br>`RulesEngineTest` — 规则引擎测试（不含 AI 层） |

## `job_platform\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(job-platform): complete backend + frontend implementati |
| `views.py` | Job platform views — 完整 ViewSet 集 | `AccountViewSet` — 执行账号 CRUD<br>`FileSourceViewSet` — 文件源 CRUD<br>`ScriptViewSet` — 脚本 CRUD + 版本管理<br>`TemplateViewSet` — 作业模板 CRUD<br>`PlanViewSet` — 执行方案 CRUD<br>`VariableViewSet` — 全局变量 CRUD |
