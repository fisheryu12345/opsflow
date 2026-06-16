# Agent 设计文档

> 版本: v1.0 | 日期: 2026-06-15 | 作者: OpsFlow Team
> 状态: 已定稿 | 批准后进入实施

---

## 一、背景与目标

OpsFlow 平台当前远程执行依赖 SSH（paramiko），存在以下问题：
- Python 并发瓶颈，大规模批量执行效率低
- SSH 依赖凭据管理，密码/密钥泄露风险
- 无在线 Agent，无法做到指令推送、实时结果流
- 无文件传输的标准通道
- 无主机端数据采集基础设施

**目标：** 用 Go 实现 Agent 组件，替换 SSH 成为远程执行首选通道，并作为 CMDB 数据采集器和文件传输通道。

### 与 OpsFlow 平台的关系

| 能力域 | 对应子产品 | 定位 |
|--------|-----------|------|
| ⑤ 批量作业 | Job Platform | Agent 成为执行后端，替代 SSH |
| ① 编排自动化 | OpsFlow Core | 新增 Agent 原子插件（agent_exec_cmd） |
| ② 配置管理 | CMDB | Agent 作为数据采集器，定时采集主机/进程信息上报 CMDB |
| ⭐ 平台能力定位 | **Agent 执行层** | 与 Celery/Tower/SSH 并列，成为 Layer 4 首选执行通道 |

---

## 二、整体架构

### 架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                       OpsFlow Django Backend                       │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Job Plat │  │ Pipeline   │  │ CMDB     │  │  Agent Admin   │ │
│  │ (作业)   │  │ (工作流)    │  │ (配置管理) │  │  (管理界面/API) │ │
│  └────┬─────┘  └─────┬──────┘  └────┬─────┘  └───────┬────────┘ │
│       │              │              │              │           │
│  ┌────▼──────────────▼──────────────▼──────────────▼───────┐   │
│  │              ws_push.py (统一WebSocket推送层)              │   │
│  └───────────────────────┬──────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                           │ HTTP REST API
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Agent Server (Go 独立进程)                       │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ REST API    │  │ WS Gateway   │  │ File Transfer Service  │  │
│  │ :8080       │  │ :8081        │  │ :8082                  │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬────────────┘  │
│         │                │                      │              │
│  ┌──────▼────────────────▼──────────────────────▼──────────┐   │
│  │  Handler: Agent/Task/File/Subproc/Broadcast              │   │
│  └──────┬─────────────────────────────────────────────────┘   │
│  ┌──────▼─────────────────────────────────────────────────┐   │
│  │  Service: AgentManager/TaskScheduler/FileCoord          │   │
│  │  + Connection Pool map[agent_id]*WSConn (读写锁)        │   │
│  └──────┬─────────────────────────────────────────────────┘   │
│  ┌──────▼─────────────────────────────────────────────────┐   │
│  │  Storage: Memory + BoltDB + LocalDisk + Async→Django   │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │ WS (控制)      │ WS (控制)      │ HTTP (文件)
          ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Agent (Linux)    │ │ Agent (Windows)  │ │ Agent (AIX)      │
│ ┌────────────┐   │ │ ┌────────────┐   │ │ ┌────────────┐   │
│ │ Subproc    │   │ │ │ Subproc    │   │ │ │ Subproc    │   │
│ │ Manager    │   │ │ │ Manager    │   │ │ │ Manager    │   │
│ └────────────┘   │ │ └────────────┘   │ │ └────────────┘   │
│ collector        │ │ collector        │ │ collector        │
│ executor/file    │ │ executor/file    │ │ executor/file    │
└──────────────────┘ └──────────────────┘ └──────────────────┘

┌──────────────────────────────────────────────┐
│ Agent Gateway (可选，跨站点部署)                │
│ 站内 Agent 连 Gateway, Gateway 连中心 Server  │
│ 职责: 连接代理/本地聚合/离线缓冲/文件缓存       │
└──────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 语言 | 部署位置 | 职责 |
|------|------|---------|------|
| **Agent Server** | Go | OpsFlow 服务端（独立进程） | Agent 连接管理、指令路由、文件代理、结果批量写回 Django |
| **Agent** | Go | 被管控主机 | 接收指令、执行命令、文件传输、CMDB 采集、子进程管理、热升级 |
| **Agent Admin** | Python/Django | OpsFlow 内部 | Agent 管理界面、REST API、任务编排 |
| **Agent Gateway** | Go | 跨站点/跨云节点 | 连接代理、本地聚合、文件缓存（与 Agent 共享代码库） |

---

## 三、消息协议

### 3.1 统一消息信封

```json
{
  "version": "1.0",
  "msg_id": "uuid-v7",
  "type": "command | command_result | heartbeat | register | register_ack | file_push | file_pull | file_progress | collect | collect_result | gateway_route | disconnect | upgrade",
  "topic": "agent:*",
  "timestamp": "2026-06-15T10:00:00Z",
  "source": "server | agent | gateway",
  "target": { "agent_id": "", "biz_id": "", "hosts": [] },
  "body": {},
  "ttl": 300,
  "trace_id": ""
}
```

### 3.2 消息类型

| type | 方向 | 说明 |
|------|------|------|
| `command` | Server→Agent | 下发指令执行 |
| `command_result` | Agent→Server | 指令结果回流（实时流式） |
| `heartbeat` | Agent→Server | 心跳上报（30s 间隔，含负载信息） |
| `register` | Agent→Server | 注册/重连 |
| `register_ack` | Server→Agent | 注册确认（含心跳间隔配置） |
| `file_push` | Server→Agent | 文件推送通知 |
| `file_pull` | Agent→Server | 文件拉取请求 |
| `file_progress` | 双向 | 文件传输进度 |
| `collect` | Server→Agent | 采集指令（CMDB 数据采集） |
| `collect_result` | Agent→Server | 采集结果上报 |
| `upgrade` | Server→Agent | Agent 升级指令 |
| `upgrade_ack` | Agent→Server | 升级结果反馈 |
| `gateway_route` | Server→Gateway | 路由表更新 |
| `disconnect` | 双向 | 优雅断开 |

### 3.3 指令下发

```json
{"type": "command", "msg_id": "a1b2c3d4", "body": {
  "exec_id": "uuid",
  "timeout": 3600,
  "script_type": "shell|python|bat|powershell",
  "script_content": "echo hello",
  "script_params": ["--verbose"],
  "env_vars": {"PATH": "/usr/local/bin"},
  "work_dir": "/tmp",
  "output_limit": 10485760
}}
```

### 3.4 结果回流（实时流式）

```json
{"type": "command_result", "msg_id": "a1b2c3d4", "body": {
  "exec_id": "uuid", "seq": 1, "is_final": false,
  "stdout": "progress...", "stderr": "",
  "exit_code": null, "finish_time": 1718418000
}}
```

### 3.5 心跳

```json
{"type": "heartbeat", "body": {
  "agent_id": "", "hostname": "", "ip": "",
  "version": "1.0.0", "uptime": 3600,
  "load": [0.5,0.3,0.2], "memory_usage": 45.2,
  "disk_usage": {"root": 62.1},
  "cpu_count": 8, "timestamp": 1718418000
}}
```

心跳间隔：默认 30s，Server 通过 `register_ack` 可动态调整。

### 3.6 Agent 升级协议

```json
{"type": "upgrade", "body": {
  "upgrade_id": "uuid",
  "download_url": "https://agent-server:8080/v1/agents/download/1.1.0/agent-linux-amd64",
  "checksum": "sha256:xxxx",
  "version": "1.1.0",
  "timeout": 300,
  "rollback_version": "1.0.0",
  "rollback_checksum": "sha256:yyyy"
}}
```

升级流程：

```
Server 下发 upgrade → Agent 收到 → 下载新二进制 → sha256校验
  → 创建备份(旧二进制重命名) → fork 新进程(新二进制同名替换)
  → 新进程建新 WS 连接 → 发送 upgrade_ack → 旧进程优雅退出
  → 升级失败 → 自动回滚(恢复旧二进制 → 重启)
```

---

## 四、安全设计

| 层面 | 措施 |
|------|------|
| Agent 注册认证 | 预置 Token（安装时注入），Server 存 sha256 校检 |
| 通信加密 | WS/HTTP 全走 TLS，Agent 可选校验 Server 证书指纹 |
| 指令鉴权 | Agent Server 验证指令来源为合法 Django 请求后才转发 |
| 主机指纹 | Token + AgentID + 硬件 UUID + MAC 联合校验 |
| 防重放 | msg_id 唯一性检查，TTL 超时拒绝 |
| 结果审计 | 所有执行记录写入 agent_task_execution 不可删除 |
| 子进程隔离 | 低权限用户运行，Linux cgroup/Windows Job Object 限制资源 |
| 升级安全 | sha256 校验，回滚冗余，旧二进制备份 |

### Agent 运行用户

Agent 主进程以 `agent` 专用系统用户运行，非 root。需要提权的操作通过 sudo 白名单 → `agent-helper` 辅助程序执行。Windows 上以 LocalSystem 启动但子进程降权运行。

---

## 五、数据模型

所有表前缀为 `agent_`，放在 Django App `backend/agent/django/` 中。

### 5.1 AgentInstance — Agent 注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | UUID | 硬件指纹生成，唯一标识 |
| biz_id | FK | 对应 ops_project |
| hostname | str | 主机名 |
| ip | str | 主 IP |
| ip_list | JSON | 所有 IP |
| os_type | str | linux / windows / aix |
| os_version | str | 操作系统版本 |
| arch | str | amd64 / arm64 / ppc64 |
| agent_version | str | Agent 版本号 |
| status | str | online / offline / unknown |
| last_heartbeat | datetime | 最后心跳 |
| first_register | datetime | 首次注册 |
| credential_token | str | sha256(预置 Token) |
| tags | JSON | 自定义标签 |
| enable_collect | bool | CMDB 采集 |
| enable_file | bool | 文件传输 |
| last_upgrade | datetime | 最后升级时间 |
| upgrade_status | str | none / upgrading / success / failed / rollback |

### 5.2 AgentTaskExecution — 任务执行记录

| 字段 | 类型 | 说明 |
|------|------|------|
| exec_id | UUID | 执行 ID |
| biz_id | FK | 业务 |
| task_source | str | job_platform / opsflow / opsagent / open_api |
| source_id | str | 来源方业务 ID |
| agent_id | ref | 目标 Agent |
| target_host | str | 主机冗余 |
| script_type | str | shell / bat / powershell / python |
| timeout | int | 超时秒数 |
| status | str | pending / dispatching / running / success / failed / timeout / cancelled |
| exit_code | int | 最终退出码 |
| error_msg | text | 错误信息 |
| start_time / finish_time | datetime | 时间戳 |

### 5.3 AgentTaskResult — 结果行数据

| 字段 | 类型 | 说明 |
|------|------|------|
| exec_id | ref | → AgentTaskExecution |
| seq | int | 分片序号 |
| is_final | bool | 是否最终片 |
| stdout | text | 分片 stdout |
| stderr | text | 分片 stderr |
| received_at | datetime | Server 收到时间 |
| pushed_at | datetime | 推送到前端时间 |

### 5.4 AgentFileTask — 文件传输任务

| 字段 | 类型 | 说明 |
|------|------|------|
| file_task_id | UUID | 任务 ID |
| biz_id | FK | 业务 |
| direction | str | push / pull |
| source_type | str | local / agent |
| target_type | str | agent / local |
| file_name | str | 文件名 |
| file_size | bigint | 文件大小 |
| file_hash | str | sha256 |
| chunk_size | int | 分块大小（4MB）|
| status | str | pending / transferring / success / failed |
| progress | int | 0-100 |
| error_msg | text | 错误信息 |

### 5.5 AgentCollect — CMDB 采集记录

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | ref | 所属 Agent |
| collect_type | str | host_info / process / disk / network / package |
| collect_interval | int | 采集间隔(秒) |
| last_collect | datetime | 最后采集时间 |
| last_data | JSON | 最新数据快照 |
| status | str | enabled / disabled |

### 5.6 AgentUpgrade — 升级记录

| 字段 | 类型 | 说明 |
|------|------|------|
| upgrade_id | UUID | 升级记录 ID |
| agent_id | ref | 目标 Agent |
| from_version | str | 旧版本 |
| to_version | str | 新版本 |
| status | str | pending / downloading / upgrading / success / failed / rollback |
| checksum | str | sha256 |
| rollback_checksum | str | 旧版本 sha256 |
| started_at / finished_at | datetime | 时间戳 |
| error_msg | text | 错误信息 |

---

## 六、Django REST API

| 端点 | 方法 | 说明 | 调⽤方 |
|------|------|------|--------|
| `GET /api/agent/agents/` | List | Agent 列表，支持 biz/hostname/status 过滤 | 前端 |
| `GET /api/agent/agents/{id}/` | Detail | Agent 详情 + 在线状态 | 前端 |
| `PATCH /api/agent/agents/{id}/` | Update | 编辑标签、采集开关 | 前端 |
| `POST /api/agent/tasks/exec/` | Create | **下发指令** | Agent Server / 前端 |
| `GET /api/agent/tasks/{exec_id}/` | Detail | 任务详情 | 前端 |
| `GET /api/agent/tasks/{exec_id}/result/` | List | 结果流数据 | 前端 |
| `POST /api/agent/tasks/batch_results/` | Create | **Server 批量写回结果** | Agent Server |
| `POST /api/agent/files/push/` | Create | **发起文件推送** | 前端 |
| `POST /api/agent/files/pull/` | Create | **发起文件拉取** | 前端 |
| `GET /api/agent/files/{task_id}/` | Detail | 文件任务进度 | 前端 |
| `GET /api/agent/collect/rules/` | List | 采集规则配置 | 前端 |
| `POST /api/agent/agents/upgrade/` | Create | 下发升级指令 | 前端 |
| `GET /api/agent/agents/upgrade/{id}/` | Detail | 升级任务详情 | 前端 |
| `GET /api/agent/stats/` | Detail | 仪表盘统计 | 前端 |
| `POST /api/agent/collect/reports/` | Create | **Agent 采集数据上报** | Agent Server |

---

## 七、Agent Server 架构（Go）

### 技术栈

| 组件 | 选择 | 理由 |
|------|------|------|
| HTTP 路由 | chi | 轻量、标准库兼容 |
| WebSocket | gorilla/websocket | 成熟稳定 |
| 嵌入式 KV | bbolt | 持久化路由表/任务状态 |
| 日志 | slog (Go 1.21) | 零依赖，结构化 |
| 配置 | TOML | 清晰易读 |
| TLS | 标准库 crypto/tls | 内置 |

### 模块结构

```
backend/agent/server/
├── cmd/server/main.go
├── internal/
│   ├── config/              # 配置加载
│   ├── api/                 # REST API
│   │   ├── router.go
│   │   ├── middleware.go
│   │   ├── agent_handler.go
│   │   ├── task_handler.go
│   │   ├── file_handler.go
│   │   └── upgrade_handler.go
│   ├── ws/                  # WebSocket
│   │   ├── listener.go
│   │   ├── connection.go
│   │   ├── registry.go      # map[agent_id]*Conn
│   │   └── heartbeat.go
│   ├── service/             # 业务层
│   │   ├── agent_mgr.go
│   │   ├── task_scheduler.go
│   │   ├── file_coord.go
│   │   ├── upgrade_mgr.go
│   │   └── broadcast.go
│   ├── store/               # 存储层
│   │   ├── memory.go
│   │   ├── boltdb.go
│   │   └── filestore.go
│   ├── backend/             # → Django 异步写回
│   │   ├── client.go
│   │   └── batch.go
│   └── model/
│       ├── agent.go
│       ├── task.go
│       └── file.go
├── pkg/
│   ├── netutil/
│   └── crypto/
├── go.mod
└── go.sum
```

### 异步写回 Django

```
Agent 结果 (WS) → 内存 channel (buffered 10000)
  → 批量聚合器 goroutine:
    → 攒够 50 条 或 每 2 秒
    → HTTP POST → Django /api/agent/tasks/batch_results/
    → 失败重试 3 次，仍失败则持久化到 BoltDB 待重试
```

---

## 八、Agent 架构（Go）

### 模块结构

```
backend/agent/agent/
├── cmd/agent/main.go
├── internal/
│   ├── config/              # TOML 配置
│   ├── core/
│   │   ├── ws_client.go     # WS 连接管理（含自动重连、主备切换）
│   │   ├── heartbeat.go
│   │   ├── register.go
│   │   └── msg_handler.go
│   ├── executor/
│   │   ├── shell.go
│   │   ├── python.go
│   │   ├── win.go
│   │   └── stream.go
│   ├── file/
│   │   ├── download.go
│   │   ├── upload.go
│   │   └── chunk.go
│   ├── subproc/
│   │   ├── manager.go
│   │   ├── installer.go
│   │   ├── health.go
│   │   └── resource.go
│   ├── collector/
│   │   ├── host.go
│   │   ├── process.go
│   │   └── reporter.go
│   ├── upgrade/
│   │   ├── downloader.go
│   │   ├── swapper.go
│   │   └── self_restart.go
│   └── osutil/
│       ├── service_linux.go
│       ├── service_windows.go
│       └── service_aix.go
├── pkg/
│   ├── protocol/
│   │   ├── types.go
│   │   └── codec.go
│   └── hostid/
├── go.mod
├── go.sum
└── agent.toml.example
```

### Agent 配置

```toml
[agent]
agent_id = ""
token = "pre-shared-token"
data_dir = "/var/lib/agent"

[server]
endpoint = "wss://agent.opsflow.example.com:8081/ws"
api_endpoint = "https://agent.opsflow.example.com:8080"
backup_endpoint = ""
fingerprint_verify = true

[heartbeat]
interval = 30
jitter = 5

[collector]
enable = true
interval = 300

[subproc]
enable = true
bin_dir = "/var/lib/agent/bin"
data_dir = "/var/lib/agent/data"

[upgrade]
auto_upgrade = true
check_interval = 3600

[logging]
level = "info"
file = "/var/log/agent/agent.log"
max_size = 100
max_backups = 7
max_age = 30
compress = true
```

---

## 九、Agent 安装流程

三种安装方式覆盖不同场景：

### 方式 A：手动安装（兜底）

```
用户在 OpsFlow 界面操作:
1. Agent 管理 → 生成安装命令
2. 选择 OS 类型 → 自动生成带 Token 的安装命令
3. 复制命令到目标主机执行

示例:
curl -o- https://agent.opsflow.example.com/install.sh | \
  bash -s -- --token=TKN-XXXX --server=agent.opsflow.example.com:8081
```

安装脚本自动完成：下载 → 校验 → 写入 Token → 注册系统服务 → 启动 Agent → 注册到 OpsFlow。

### 方式 B：SSH 推送安装（推荐，批量场景）

```
用户操作:
 Step 1: 选择目标主机（CMDB 勾选 / IP 输入）
 Step 2: 选择 SSH 账户
 Step 3: 确认参数（版本、Token 自动生成）
 Step 4: 实时进度展示

后端: Django → SSH Executor → SCP 推送 Agent 二进制
  → 远程执行 install.sh → Agent 启动 → WS 注册 → 状态更新
```

### 方式 C：离线安装（封闭网络）

```
1. 在 OpsFlow 下载离线安装包（含二进制 + install.sh）
2. 复制到各主机执行 ./install.sh
3. 或通过 Ansible/Puppet 批量分发
```

---

## 十、文件传输设计

| 参数 | 值 |
|------|-----|
| 分块大小 | 4MB |
| 并发上传数 | 4 |
| 校验方式 | sha256（逐块 + 整体文件） |
| 重试策略 | 失败块最多重试 3 次 |
| 临时存储 | Agent Server `<data_dir>/chunks/<task_id>/` |
| 清理策略 | 完成后立即清理，兜底 24h 自动清理 |

文件推送流程：
```
1. 用户上传文件到 Django 或 Agent Server
2. Agent Server 计算 sha256、分块（4MB/块）
3. Server 下发 file_push 通知到 Agent
4. Agent 并发 HTTP GET 分块（4 并发）
5. 每块下载完成后校验 sha256
6. 所有块完成 → 合并文件到目标路径
7. 整体 sha256 校验 → 返回 file_progress (100%)
8. 失败块最多重试 3 次 → 放弃则标记失败
```

---

## 十一、CMDB 自动采集

Agent 定时采集主机信息上报 CMDB，作为资产自动发现的数据源。采集数据通过以下路径写入 Neo4j：

```
Agent 定时采集 → WS collect_result → Agent Server
  → HTTP POST → Django /api/agent/collect/reports/
  → CMDB Service → 更新 Host 节点属性 / 创建 Process 节点 + RUNS_ON 关系
```

### 采集内容

| 采集类型 | 周期 | 数据量 | CMDB 写入目标 |
|---------|------|--------|-------------|
| `host_info` | 300s | ~2KB | Host 节点属性（cpu/mem/disk/os/kernel） |
| `process` | 600s | ~10KB | Process 节点 + `RUNS_ON` → Host 关系 |
| `disk` | 600s | ~3KB | Host 节点 disk 属性 |
| `network` | 600s | ~2KB | Host 节点 ip_list/nic 属性 |
| `package` | 3600s | ~20KB | 暂不写入，仅展示 |

### ⚠️ 进程采集 vs 进程管理

| | 进程采集（本计划 Phase 2） | 进程管理（后续需求） |
|--|---------------------------|-------------------|
| 行为 | 读 `/proc` 或 `ps aux` 拍照上报 | `systemctl start/stop/status` |
| 方向 | Agent → CMDB（只读） | Server → Agent（读写） |
| 实现方式 | Agent collector 模块内置 | OpsFlow agent_exec_cmd 原子编排 |
| 交付 | Phase 2 | Phase 2 之后的独立迭代 |

---

## 十二、与 OpsFlow 的集成

### 12.1 Job Platform — AgentExecutor

`backend/job_platform/services/executor.py` 新增 `AgentExecutor`。用户选择「远程执行」时默认走 Agent 通道，原有 SSH Executor 降级为兜底。

### 12.2 OpsFlow Pipeline — Agent 原子插件

新增插件组 `agent`：

| 插件编码 | 名称 | 功能 |
|---------|------|------|
| `agent_exec_cmd` | Agent 远程执行 | 在目标主机执行命令/脚本 |
| `agent_file_push` | Agent 文件推送 | 推送文件到目标主机 |
| `agent_file_pull` | Agent 文件拉取 | 从目标主机拉取文件 |

### 12.3 前端 Agent 管理界面

`web/src/views/apps/agent/`，侧边栏新增「Agent 管理」入口。CMDB 主机详情页显示 Agent 状态标签，可跳转 Agent 详情。

---

## 十三、跨站点部署（Agent Gateway）

```
站点 A (阿里云 VPC)         站点 B (私有 IDC)
  Agents                     Agents
     └──► Agent Gateway A       └──► Agent Gateway B
              │                          │
              └──── WS/加密隧道 ────┘
                          │
                 Agent Server (中心)
```

Gateway 与 Agent **共享同一套代码库**，启动时加 `--mode=gateway` 即可切换。职责：连接代理、本地聚合、离线缓冲、文件缓存。

---

## 十四、运维与治理

### 14.1 BoltDB 持久化

- 路径：`/var/lib/agent/server/db/agent-server.db`
- 备份：每日凌晨 3:00 快照，保留 7 天
- 恢复：停止 Server → 替换 db 文件 → 重启
- BoltDB 支持 ACID 事务，系统崩溃不会损坏

### 14.2 Token 生命周期

- **生成**：Django 每次安装自动生成 32 字节随机 Token
- **存储**：DB 中存 sha256 摘要，明文仅在安装时一次性展示
- **分发**：SSH 推送写⼊ install.sh / 手动安装展示在界面 / 离线 CSV 导出
- **轮转**：管理员在详情页刷新 Token，Agent 下次心跳时获取更新
- **吊销**：禁用 Agent 后 Server 拒绝该 Token

### 14.3 文件传输清理

完成后立即清理，兜底每 30 分钟扫描删除超过 24h 的临时目录，磁盘使用率超 80% 时触发告警。同时进行文件传输任务上限 20。

### 14.4 日志管理

Agent/Server 日志均为 JSON 格式（slog），支持按大小/时间轮转，便于 ELK/Loki 采集。

---

## 十五、实施计划

### 项目结构

```
backend/agent/
├── server/          # Go Agent Server
├── agent/           # Go Agent (含 Gateway 模式)
├── django/          # Django App
│   ├── models/
│   ├── views/
│   ├── serializers.py
│   ├── urls.py
│   ├── apps.py
│   └── admin.py
├── scripts/         # 安装脚本
├── Makefile         # 跨平台编译
├── go.work
└── README.md
```

现有 Python Agent `backend/agent/` 移入 `backend/agent-py/` 备用，Go 版本上线后清理。

### 实现阶段

**Phase 1 — 核心通道（Day 1-7）**

| 天 | 内容 |
|:--:|------|
| 1 | Go 项目骨架：go.work、主入口、配置加载、日志；协议定义 types.go/codec.go |
| 2-3 | Agent Server WS Listener + Connection Registry |
| 2-3 | Agent WS Client + 注册/心跳 + 自动重连（含备用 Server 切换） |
| 3-4 | Django models: AgentInstance + AgentTaskExecution |
| 4-5 | Django REST API + Agent Server HTTP 回调 |
| 5-6 | Agent Executor：命令执行 + 结果流式回传 |
| 6-7 | Agent Server 异步批量写回 Django + 端到端测试 |

**Phase 2 — 文件传输 + OpsFlow 集成（Day 8-14）**

| 天 | 内容 |
|:--:|------|
| 8-9 | Agent 文件分块下载/上传/sha256 校验 |
| 9-10 | Agent Server 文件协调 + 磁盘分块存储 |
| 10-11 | Django AgentFileTask model + API |
| 11-12 | Job Platform AgentExecutor |
| 12-13 | OpsFlow Agent 原子插件 (agent_exec_cmd/file_push/file_pull) |
| 13-14 | CMDB 采集: agent collector + Django 接收 + 集成测试 |

**Phase 3 — 升级 + Gateway + 管理前端（Day 15-21）**

| 天 | 内容 |
|:--:|------|
| 15-16 | Agent 热升级：下载/校验/进程替换/回滚 |
| 16-17 | Django AgentUpgrade model + API |
| 17-18 | Agent Gateway 模式 |
| 18-20 | 前端 Agent 管理界面（列表/详情/安装/文件/升级/采集） |
| 19-20 | 跨平台适配：AIX ppc64 / Windows Service / AIX SRC |
| 20-21 | Agent 安装包 + 全量集成测试 + 清理 Python Agent |

### 验证方案

| 验证项 | 方法 |
|--------|------|
| Agent 注册 | 启动 Agent → AgentInstance 记录 status=online |
| 指令下发 | Django API 下发 → Agent 收到执行 → 结果写回 Django |
| 文件推送 | 发起推送 → 目标文件存在且 sha256 一致 |
| Job Platform 集成 | 选 Agent 通道执行脚本 → 成功 |
| CMDB 采集 | 采集间隔后 CMDB 主机属性已更新 |
| Agent 升级 | 下发升级 → 版本变更 → 心跳恢复 |
| Gateway 模式 | Agent → Gateway → Server 全链路通信 |
| 跨平台 | Linux/Windows/AIX 各一台注册和执行正常 |
| 压力测试 | 500 Agent 在线 + 50 并发指令全部完成 |
| 断线重连 | 停 Server → Agent 重连 → 恢复后注册成功 |

---

## 十六、后续需求（TODO）

1. **应用进程管理**：Phase 2 交付后，基于 `agent_exec_cmd` 原子实现 `agent_process_start/stop/status/restart` 插件 + Agent 详情页进程操作界面。需前置 CMDB Process 模型定义完成。
2. **Python Agent 清理**：Go Agent 上线稳定后删除 `backend/agent-py/`，更新 `opsflow_target.md` 中 Agent 成熟度。
