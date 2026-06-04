# Job Platform Design — 基于 BK-Job 的作业平台重构

> 参考项目：[bk-job-master](../bk-job-master/) (Tencent BlueKing Job)
> 设计日期：2026-06-05
> 状态：Draft

---

## 1. 概述

### 1.1 目标

以 bk-job-master 为蓝本，完整重构 opsflow 的 `job_platform` 模块，构建一个功能完整的运维作业平台，涵盖脚本管理、文件分发、作业编排（模板→方案→实例）、执行引擎、定时调度、高危命令检测等功能。

### 1.2 架构策略 — 大爆炸完整重写

一次性实现全部功能模块。3 种执行通道（SSH / Ansible / Agent）+ 事件驱动链式执行引擎（Celery + Redis）作为底座，完整覆盖 bk-job-master 的所有核心能力。

### 1.3 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构方式 | 完整重写，不渐进 | 用户确认策略1 |
| 执行引擎 | Celery + Redis 事件驱动链 | 零新增依赖，已有 Celery/Redis 基础设施；task chain 自然映射 Job→Step→GseTask 三层事件 |
| 执行通道 | SSH + Ansible + Agent | SSH 复用现有 opsagent，Ansible 复用 ansible_trigger，Agent 全新开发 |
| 步骤模型 | 双向链表（previousStepId/nextStepId） | 参考 bk-job 链表模式，插入/删除/重排序高效 |
| 审批集成 | 深度复用 ITSM | ITSM 工单引擎提供审批流，Job 通过回调接收审批结果 |
| 主机选择 | 深度集成 CMDB | 复用 CMDB 拓扑树，支持动态主机解析 |
| 高危检测 | 规则引擎 + AI 语义双层检测 | 规则引擎快响应，AI 层做深度语义分析；复用 opsflow LLM 服务 |
| 与 opsflow 集成 | 混合架构（核心自研 + pipeline 集成点） | 新增 `job_execute` 插件节点类型，使 pipeline 可调用 Job 平台 |

---

## 2. 数据模型

### 2.1 三层层次结构

```
Template (作业模板)
  ├── first_step → Step (链表头)
  ├── last_step  → Step (链表尾)
  ├── variables: Variable[] (全局变量)
  ├── status: draft / published / deprecated
  ├── tags, category, version
  └── plans: Plan[] (关联的执行方案)

Plan (执行方案, 继承自 Template)
  ├── template → Template (FK, 来源模板)
  ├── steps: Step[] (复制自模板, 可调整启用/禁用)
  ├── enable_steps: List[step_id] (启用的步骤ID列表)
  ├── variables: Variable[] (可覆盖模板变量)
  └── is_debug: bool (调试模式标志)

Instance (执行实例)
  ├── plan → Plan? (来源方案, 可为空=快速执行)
  ├── template → Template? (直接来源模板, 可为空)
  ├── status: pending/running/success/failed/stopped/approving
  ├── current_step_index: int (当前执行到的步骤索引)
  ├── start_time, end_time, total_time
  ├── executor: ssh/ansible/agent (执行通道)
  ├── variables: JSON (运行时变量值快照)
  ├── triggered_by: manual/cron/api
  └── steps: StepExecution[] (步骤执行记录)
```

### 2.2 步骤链表

```
Step
  ├── template → Template? (FK, 所属模板)
  ├── plan → Plan? (FK, 所属方案)
  ├── type: script / file / approval
  ├── previous_step → Step? (FK, 前驱节点)
  ├── next_step → Step? (FK, 后继节点)
  ├── template_step_id: int? (方案中记录原始模板步骤ID)
  ├── enable: bool (方案中是否启用此步骤)
  ├── ref_variables: JSON[变量名] (引用的变量名列表)
  │
  ├── (以下根据 type 选择其一)
  ├── script_step → ScriptStep? (一对一)
  ├── file_step → FileStep? (一对一)
  └── approval_step → ApprovalStep? (一对一)
```

**步骤子类型**：

```
ScriptStep
  ├── script_source: local / citing / public
  ├── script → Script? (FK, 引用脚本库中的脚本)
  ├── content: TEXT (内联脚本内容)
  ├── language: shell / python / powershell / bat / sql
  ├── script_params: TEXT (脚本参数)
  ├── timeout: int (秒)
  ├── account → Account (FK, 执行账号)
  ├── execute_target: TargetConfig (目标主机配置)
  ├── ignore_error: bool (失败时是否忽略继续)
  └── secure_param: bool (参数是否敏感隐藏)

FileStep
  ├── file_sources: JSON[FileSource] (多个文件源)
  ├── destination_path: str (目标路径)
  ├── transfer_mode: strict / force / safe
  ├── speed_limit: int (KB/s, 0=不限)
  ├── account → Account (FK, 目标端账号)
  └── execute_target: TargetConfig

ApprovalStep
  ├── approval_type: anyone / all
  ├── approvers: JSON[用户ID或角色]
  ├── approval_message: TEXT (支持变量渲染)
  └── notify_channels: JSON[渠道]
```

### 2.3 变量系统

```
Variable
  ├── template → Template? (FK, 所属模板)
  ├── plan → Plan? (FK, 所属方案)
  ├── name: str
  ├── type: string / namespace / cipher / host_list
  ├── default_value: JSON
  ├── changeable: bool (执行时是否允许修改)
  ├── required: bool
  └── follow_template: bool (方案是否跟随模板值)
```

变量引用机制：
- 步骤的 `ref_variables` 字段记录引用的变量名列表
- 修改变量名 / 删除变量时自动同步到所有引用步骤
- 执行时变量值快照存储在 `Instance.variables` 中

### 2.4 目标主机配置 (TargetConfig)

```
TargetConfig
  ├── source: cmdb_node / static_list / variable_ref
  ├── cmdb_nodes: JSON[]? (CMDB 节点ID列表, 动态解析)
  ├── static_hosts: JSON[]? (静态 IP/域名列表)
  ├── variable_name: str? (引用变量中的主机列表)
  ├── exclude_hosts: JSON[]? (排除的主机)
  └── total_count: int (解析后实际主机数)
```

执行时，`TargetConfig` 会实时解析 CMDB 节点为具体 IP 列表，支持动态主机拓扑。

### 2.5 执行实例状态机

```
     ┌────────────────────────────────────┐
     │           BLANK (初始)              │
     └────────────┬───────────────────────┘
                  │ start
     ┌────────────▼───────────────────────┐
     │           RUNNING                   │
     └──┬──────┬──────┬──────┬────────────┘
        │      │      │      │
  step  │ step │ step │ step │ all steps
  done  │ fail │ stop │ wait │ done
        │      │      │      │
  ┌─────▼┐ ┌──▼──┐ ┌──▼──┐ ┌▼───────────┐
  │continue│ │fail │ │stop │ │ SUCCESS    │
  │to next │ │     │ │ ping │ └────────────┘
  └────┬───┘ └─────┘ └─────┘
       │
       └── (循环直到所有步骤完成)
```

特殊状态：
- `WAITING_USER` — 审批步骤等待审批
- `CONFIRM_TERMINATED` — 审批拒绝终止
- `IGNORE_ERROR` — 步骤出错但设置了 ignore_error

---

## 3. 执行引擎

### 3.1 事件驱动链

基于 Celery + Redis 实现的三层事件驱动：

```
JobStartTask (Celery chain 起点)
  │
  ▼
StepExecTask (根据 step.type 分发)
  │
  ├── ScriptStep → ScriptExecutor (SSH/Ansible/Agent)
  ├── FileStep   → FileExecutor (SCP/Ansible/Agent)
  └── ApprovalStep → ApprovalExecutor (对接 ITSM)
        │
        ▼
  StepResultPollTask (轮询/等待结果)
        │
  ┌─────┴─────┐
  │ 成功/忽略   │ 失败
  └─────┬─────┘ └──────→ JobFailTask
        │
  ┌─────▼─────┐
  │ NextStep?  │ → 还有下一步 → StepExecTask (循环)
  │ 或结束？    │ → 全部完成 → JobFinishTask
  └───────────┘
```

### 3.2 状态存储和恢复

- **事件流**：通过 Celery task chain 驱动，不依赖外部消息队列
- **状态持久化**：每个关键节点写入 MySQL（JobExecution.status, StepExecution.status）
- **结果缓存**：Redis 缓存每主机执行中间结果
- **故障恢复**：Celery task 失败时自动重试（配置重试次数 + backoff）
- **幂等性**：每个 StepExecution 有唯一 `execution_key`，防止重复执行

### 3.3 结果收集

参考 bk-job-master 的 `ResultHandleManager` + `DelayQueue` 模式，Python 实现：

```
每主机执行完成后：
1. Agent/SSH 返回结果 → 写入 Redis (execution_id:host -> result)
2. StepResultCollector 检查是否所有主机已完成
3. 全部完成 → 触发 Step Complete 事件
4. 部分失败 → 根据 ignore_error 判断
5. 超时未完成 → 触发 Timeout 事件
```

---

## 4. 脚本管理

### 4.1 模型

```
Script
  ├── name, description
  ├── script_type: shell / python / powershell / bat / sql
  ├── content: TEXT (当前在线版本的内容)
  ├── params_schema: JSON (参数 Schema, 用于前端动态表单)
  ├── tags: JSON[]
  ├── category: builtin / public / private
  ├── status: draft / online / disabled
  │
  ├── ScriptVersion (版本)
  │   ├── version: str (语义化版本号 "1.0.0")
  │   ├── content: TEXT (版本内容快照)
  │   ├── changelog: TEXT
  │   ├── status: draft / online / disabled
  │   └── created_by, created_at
  │
  └── ScriptReference (引用追踪)
      ├── script → Script
      ├── referenced_by_type: template / plan
      └── referenced_by_id: int (FK ID)
```

### 4.2 关键流程

- **创建脚本** → 自动创建 ScriptVersion v1.0.0 (draft) → 发布后变为 online
- **更新脚本** → 创建新版本 → 发布上线 → 通知所有引用此脚本的模板
- **引用追踪**：删除脚本时检查引用，有引用拒绝删除
- **内置脚本**：系统预置（磁盘检查、日志清理、Nginx 健康检查等），不可删除

---

## 5. 文件分发

### 5.1 模型

```
FileSourceConfig
  ├── type: server / local / file_source / base64
  ├── files: JSON[] (文件路径列表)
  ├── account → Account? (源端账号, server 类型需要)
  └── file_source_id: int? (FileSource FK, 预配置文件源)

FileSource (预配置文件源)
  ├── name, description
  ├── type: s3 / ftp / samba / nfs / custom
  ├── config: JSON (连接配置)
  ├── credential_type: password / key / secret
  └── is_active: bool
```

### 5.2 传输模式

| 模式 | 行为 | 场景 |
|------|------|------|
| `strict` | 目标路径必须为空目录 | 安全部署 |
| `force` | 强制覆盖已有文件 | 更新配置文件 |
| `safe` | 同名文件自动重命名(加时间戳) | 日志/备份 |

### 5.3 执行映射

| 通道 | 文件传输方式 |
|------|-------------|
| SSH | scp / rsync (通过 SSH 通道) |
| Ansible | ansible copy / synchronize module |
| Agent | 二进制分块传输 + 校验和确认 |

---

## 6. 审批步骤

### 6.1 流程

```
1. Job 执行到 ApprovalStep
2. StepExecTask 启动 → StepExecution 状态 = WAITING_USER
3. 调用 ITSM 创建工单（工单类型 = 作业审批）
   - 工单标题: "【作业审批】{job.name} - 步骤: {step.name}"
   - 工单内容: approval_message (渲染后的)
   - 审批人: approvers 列表
   - 通知渠道: notify_channels
4. ITSM 回调 Job API: POST /api/job-platform/approvals/callback/
   - {execution_id, step_instance_id, action: approve/reject, comment}
5. 接收回调 → 更新 StepExecution 状态
   - approve → SUCCESS → 继续下个步骤
   - reject → CONFIRM_TERMINATED → Job 终止
```

### 6.2 回调安全

- 回调 URL 使用签名验证（HMAC-SHA256）
- 回调请求记录到 audit log
- 支持超时自动拒绝（配置 N 小时内未审批则自动终止）

---

## 7. 定时作业

### 7.1 模型

```
CronJob
  ├── name, description
  ├── plan → Plan? (FK, 关联执行方案)
  ├── script → Script? (快速执行: 直接关联脚本)
  ├── cron_expression: str ("0 2 * * *")
  ├── timezone: str (默认 "Asia/Shanghai")
  ├── variables_override: JSON (覆盖变量值)
  ├── target_override: TargetConfig (覆盖目标主机)
  ├── is_active: bool
  ├── start_date / end_date (有效期范围)
  ├── misfire_grace: int (允许的延迟执行秒数)
  ├── last_run_at / next_run_at
  │
  ├── CronJobExecution (执行历史)
  │   ├── cron_job → CronJob (FK)
  │   ├── execution → JobExecution (FK)
  │   ├── scheduled_time / actual_time
  │   └── status: pending / running / success / failed
  └──
```

### 7.2 调度策略

- 基于 APScheduler + DjangoJobStore（opsflow 已配置）
- 每次触发时创建 JobExecution 并调用执行引擎
- 保留最近 100 条执行历史，超限自动清理
- 支持 `execute-now` 立即执行一次（不等待 Cron）

---

## 8. 高危命令检测

### 8.1 双层检测架构

```
Layer 1 — 规则引擎 (同步, 毫秒级)
  ├── 关键字匹配 (pattern in command)
  ├── 正则匹配 (re.search)
  ├── 动作: reject / approval / warn
  └── 内置规则 + 用户自定义规则

Layer 2 — AI 语义检测 (异步, 百毫秒级)
  ├── 复用 opsflow/core/llm_service.py
  ├── 分析脚本意图: 数据破坏 / 权限提升 / 信息泄露 / 资源耗尽 / 后门植入
  ├── 返回: risk_level (none/low/medium/high/critical) + 原因 + 修改建议
  └── 缓存: 相同脚本内容命中缓存跳过 AI 调用
```

### 8.2 模型

```
DangerousCmdRule
  ├── name, description
  ├── pattern: str (关键字或正则)
  ├── is_regex: bool
  ├── script_type: shell / python / sql / all
  ├── action: reject / approval / warn
  ├── severity: low / medium / high / critical
  └── is_active: bool

DangerousCheckLog (检测记录)
  ├── script_content: TEXT (被检测的脚本)
  ├── rule_hit: JSON[] (命中的规则)
  ├── ai_result: JSON (AI 检测结果)
  ├── final_action: allow / reject / approval / warn
  └── checked_at, checked_by
```

### 8.3 检测时机

| 时机 | 触发 | 动作 |
|------|------|------|
| 脚本保存/更新 | 规则引擎 | 提示用户存在高危操作 |
| Job 执行前 | 规则引擎 + AI | 拦截 / 创建审批 / 警告 |
| 快速执行前 | 规则引擎 + AI | 同上 |

---

## 9. 账号管理

### 9.1 模型

```
Account
  ├── name: str (别名, 如 "prod-root")
  ├── protocol: ssh / winrm / mysql / postgresql
  ├── username: str
  ├── password: ENCRYPTED (AES-256 加密存储)
  ├── ssh_key: TEXT (可选, 加密存储)
  ├── port: int
  ├── credential_type: password / key / secret
  ├── category: system / database / cloud
  ├── scope: global / project
  └── is_active: bool
```

### 9.2 安全策略

- 密码/私钥使用项目已有 AES 加密工具存储
- API 返回时自动屏蔽敏感字段（`***`）
- 删除前检查是否被任何 Step 引用
- 操作日志记录所有账号使用记录

---

## 10. 执行通道

### 10.1 抽象执行器接口

```python
class BaseExecutor(ABC):
    """所有执行通道的抽象基类"""

    @abstractmethod
    def execute(self, step_execution: StepExecution, targets: list[Host]) -> TaskResult:
        """在目标主机上执行步骤"""
        ...

    @abstractmethod
    def cancel(self, execution_id: str) -> bool:
        """取消正在执行的任务"""
        ...

    @abstractmethod
    def get_status(self, execution_id: str) -> ExecutionStatus:
        """查询执行状态"""
        ...

    @abstractmethod
    def stream_logs(self, execution_id: str) -> AsyncIterator[LogLine]:
        """实时流式获取日志"""
        ...
```

### 10.2 SSH 通道

- 复用 `opsagent.tools.ssh.SshTool`
- 连接池管理（同主机复用连接）
- 超时控制（SSH 连接超时 + 命令执行超时）
- 密钥自动探测（~/.ssh/ 常用密钥）

### 10.3 Ansible 通道

- 复用 `opsflow.core.ansible_trigger`
- 将脚本/文件分发转换为 ansible-runner 调用
- 事件回调映射到 WebSocket 实时推送

### 10.4 Agent 通道

```
Agent 服务端 (opsflow 内置)
  ├── WebSocket Server (Django Channels)
  ├── Agent 注册 / 心跳 / 保活
  ├── 命令推送 / 结果回传
  └── 重连 / 断线恢复

Agent 客户端 (独立 Python 包)
  ├── 守护进程模式 (systemd/supervisor)
  ├── 心跳: 每 30s
  ├── 执行: subprocess 执行脚本
  ├── 实时上报: stdout/stderr 行推送
  └── 结果: exit_code + summary
```

---

## 11. API 路由

```
api/job-platform/
├── scripts/           # 脚本管理 (+ versions, sync, references)
├── accounts/          # 账号管理 (+ test)
├── templates/         # 作业模板 (+ publish, plans, sync-plans)
├── plans/             # 执行方案 (+ enable-steps, execute)
├── executions/        # 执行实例 (+ stop, retry, steps, log, results, approvals)
├── quick-exec/        # 快速执行 (script, file, approval)
├── cron-jobs/         # 定时作业 (+ toggle, history, execute-now)
├── file-sources/      # 文件源管理
├── approval-configs/  # 审批配置 (+ callback)
├── dangerous-rules/   # 高危命令规则 (+ toggle, check)
└── dashboard/         # 统计 (overview, trends, top-scripts)
```

所有 API 遵循 opsflow 规范：
- 成功：`DetailResponse(data)` / `SuccessResponse(data, total=count)`
- 错误：`ErrorResponse(msg, code=4000)`

---

## 12. 与 opsflow pipeline 集成

### 12.1 job_execute 插件节点

在 `opsflow/plugins/` 中新增 `job_execute` 插件：

```python
class JobExecutePlugin(BasePlugin):
    """在 opsflow pipeline 中调用作业平台"""

    type = "job_execute"

    def execute(self, context, params):
        # params: {plan_id, variables, target_override}
        # 调用 job_platform API 执行方案
        execution = job_platform_api.execute_plan(
            plan_id=params["plan_id"],
            variables=params.get("variables", {}),
            target_override=params.get("target_override"),
        )
        # 轮询等待执行完成
        result = self.poll_until_complete(execution["id"])
        # 结果写回 pipeline 上下文
        return result
```

### 12.2 变量共享

- Pipeline 全局变量通过 `variables` 参数映射到 Job 模板输入变量
- Job 执行结果（成功数、失败数、日志链接）写回 Pipeline 上下文变量
- Job 执行中的审批步骤通过 ITSM（已在 opsflow 中）统一管理

---

## 13. 前端架构

### 13.1 页面组织

```
web/src/views/apps/job-platform/
├── index.vue                  # 入口: Tab 导航
├── components/                # 共享组件 (15+ 个)
├── template/                  # 模板管理
├── plan/                      # 执行方案
├── execution/                 # 执行管理
├── quick/                     # 快速执行
├── script/                    # 脚本管理
├── cron/                      # 定时作业
├── account/                   # 账号管理
├── approval/                  # 审批管理
├── rules/                     # 高危命令规则
└── dashboard/                 # 仪表盘
```

### 13.2 关键交互

- **模板编排**：拖拽排序步骤（链表操作）, 步骤配置面板, 实时预览
- **快速执行**：脚本编辑器（语法高亮）, CMDB 主机树选择器, 参数动态表单
- **执行日志**：WebSocket 实时日志流, 按主机筛选, 关键字搜索
- **Cron 输入**：图形化 cron 表达式工具 + 最近 5 次执行时间预览
- **主机选择**：CMDB 拓扑树 + 搜索 + 已选列表, 支持动态节点和静态 IP

### 13.3 实时推送

- WebSocket 连接: `ws://host/ws/job-platform/executions/{id}/`
- 推送事件：`log_line`, `step_status`, `execution_status`, `host_result`
- 使用 opsflow 已有的 Channels 基础设施

---

## 14. 与现有系统的集成

| 系统 | 集成方式 |
|------|----------|
| **CMDB** | 主机选择器引用 CMDB 拓扑节点, 动态解析为 IP |
| **ITSM** | 审批步骤创建 ITSM 工单, 通过回调接收审批结果 |
| **opsflow pipeline** | `job_execute` 插件节点, pipeline 可调用 Job 执行 |
| **opsagent** | 复用 SSH 工具, 共享连接池 |
| **Open API** | 提供稳定的外部 API 契约（替代目前的硬编码导入） |
| **Portal 仪表盘** | 展示执行统计和运行中的作业 |

---

## 15. 数据流全景

```
用户操作 (Web UI / API)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│                  API Layer                              │
│  (ViewSet + Serializer + Permission)                   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐    ┌─────────────────────────┐   │
│  │  资源管理 CRUD    │    │   执行控制 (execute/     │   │
│  │  (脚本/模板/方案/  │    │   stop/retry)          │   │
│  │   规则/账号)      │    └───────────┬─────────────┘   │
│  └─────────────────┘                │                   │
│                                     ▼                   │
│                          ┌──────────────────────┐       │
│                          │  Service Layer         │       │
│                          │  ├── 高危检测(规则+AI)  │       │
│                          │  ├── 变量解析            │       │
│                          │  ├── 目标解析(CMDB)      │       │
│                          │  └── 权限校验            │       │
│                          └──────────┬───────────┘       │
│                                     ▼                   │
│                          ┌──────────────────────┐       │
│                          │  Celery Task Chain    │       │
│                          │  (事件驱动执行引擎)     │       │
│                          └──────────┬───────────┘       │
│                                     ▼                   │
│                          ┌──────────────────────┐       │
│                          │  BaseExecutor         │       │
│                          └──────────────────────┘       │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │ SSH      │  │ Ansible      │  │ Agent (WebSocket) │  │
│  │ (paramiko│  │ (ansible-    │  │      通道         │  │
│  │ /asyncssh│  │  runner)     │  │                  │  │
│  └────┬───┘  └──────┬──────┘  └────────┬─────────┘  │
│       │              │                  │              │
│       └──────────────┴──────────────────┘              │
│                      │                                 │
│                      ▼                                 │
│               目标主机                                   │
└──────────────────────────────────────────────────────┘
```

---

## 16. 设计约束

1. **API 统一规范**：所有响应使用 `DetailResponse`/`SuccessResponse`/`ErrorResponse`
2. **无 emoji 存储**：MySQL utf8mb3 不支持 4 字节 Unicode
3. **代码语言**：代码字符串全英文，注释中英双语
4. **文件规范**：单文件控制在 500 行以内
5. **测试要求**：每个模块至少包含单元测试和 API 测试
6. **操作审计**：所有敏感操作记录 audit log

---

*本文档是基于 bk-job-master 分析和用户确认的设计要点编制的完整设计规范。*
