# Linux Application Process Manager Design

> Date: 2026-06-15 | Status: Draft
> Author: AI (Claude)
> Related: Go Agent, CMDB, DR Service

---

## Background

OpsFlow 需要统一的 Linux 应用进程管理能力，覆盖三个场景：

### 场景说明

| # | 场景 | 当前状态 | 目标 |
|---|------|---------|------|
| 1 | **进程生命周期管理** | Ansible Tower 远程执行（process_start/stop 插件），无自主控制能力 | Agent 直接管控：start/stop/restart/status |
| 2 | **进程拓扑采集** | Python agent（agent-py/）已实现 ps+ss 采集+CALLS 发现，但被标记为备份 | Go agent 原生实现相同能力+扩展 |
| 3 | **DR 容灾原数据** | DR Service 只依赖 BELONGS_TO+DrGroup 分组，无 CALLS 依赖链 | 全量拓扑（A→B→C→D）支撑切流顺序编排 |

### 设计约束

- **Go 增量扩展**：不修改现有 agent 的 collector/executor/ws 核心代码
- **SUSE + RedHat 兼容**：systemctl CLI 在两系统上一致
- **管理对象**：systemd service + 本工具启动的进程
- **进程标识**：自动生成（结合 CMDB 注册分类）

---

## Architecture

```
                    ┌────────────────────────────────────┐
                    │       OpsFlow Server (Django)       │
                    │  CMDB API ↑  DR Service ↑  Plugin  │
                    └──────────┬────────────────────┬────┘
                               │                    │
              ┌────────────────▼────┐   ┌───────────▼──────────┐
              │  Agent Server        │   │  Agent Server        │
              │  internal/collect    │   │  WS Hub (消息路由)   │
              └────────┬─────────────┘   └──────────┬──────────┘
                       │ ▲                         │ ▲
       采集上行        │ │         控制下行          │ │
                       ▼ │                         ▼ │
              ┌──────────────────────────────────────────┐
              │           Go Agent (目标主机)              │
              │                                           │
              │  ┌──────────────┐   ┌──────────────────┐  │
              │  │ Collector    │   │   Executor        │  │
              │  │ ↑ process    │   │ ← systemctl      │  │
              │  │ ↑ host_info  │   │ ← kill/restart   │  │
              │  └──────┬───────┘   └──────────────────┘  │
              │         │                                  │
              │         ▼                                  │
              │  ┌──────────────────┐                      │
              │  │ Registry         │ ← /etc/opsflow/apps/ │
              │  │ (app state)      │ ← /etc/systemd/      │
              │  └──────────────────┘                      │
              └──────────────────────────────────────────┘
```

### 数据流（双向）

- **上行（采集）**：Agent Collector → ws_client.SendJSON() → Agent Server → Django internal_api → Neo4j
- **下行（控制）**：OpsFlow Plugin → Agent Server WS → agent.go 消息路由 → Executor.Execute() → systemctl/kill
- **拓扑消费**：DR Service 从 Neo4j 读取 CALLS 链 → 生成切流 pipeline

### 与现有代码的关系

| 现有文件 | 改动 |
|---------|------|
| `collector.go` | 不改。新增 `ProcCollector` |
| `executor.go` | 不改。复用 `Execute()` |
| `types.go` | 不改。追加新结构体 |
| `agent.go` | +3 行 case |
| `main.go` | +1 行启动 |
| `gateway.go`, `ws_client.go`, `config.go`, `upgrade/`, `file/` | 不改 |

---

## Agent 端设计

### process_collector.go（新增）

单次采集方法：

```go
func (c *ProcCollector) Collect() *ProcessCollectBody {
    running   := c.psAux()              // 所有运行进程
    listeners := c.ssListen(running)     // 监听端口 → 关联 PID
    conns     := c.ssConns(running)      // 活跃连接 → 关联 PID
    svcs      := c.systemctlList()       // systemd services
    apps      := c.registry.List()       // 本工具注册的应用
    return &ProcessCollectBody{...}
}
```

### 进程归属判定

采集结果合并时，每个进程判定归属类型：

```
进程 cmdline 匹配某个 systemd unit?    → source=systemd
进程 PID 在本地注册表中（本工具启动）?  → source=agent, registered=true
两者都不是（手动启动/非受管）?          → source=discovery, registered=false
```

### 上报消息结构（types.go 尾部追加）

```go
const (
    MsgCollectProcess    MessageType = "collect_process"
    MsgProcessControl    MessageType = "process_control"
    MsgProcessCtrlResult MessageType = "process_control_result"
)

type ProcessCollectBody struct {
    CollectType string         `json:"collect_type"` // "process"
    Processes   []*ProcessInfo `json:"processes"`
    Services    []*ServiceInfo `json:"services"`
    Connections []*NetConn     `json:"connections"`
    Timestamp   int64          `json:"timestamp"`
}

type ProcessInfo struct {
    PID            int         `json:"pid"`
    Name           string      `json:"name"`
    User           string      `json:"user"`
    Cmdline        string      `json:"cmdline"`
    CPU            float64     `json:"cpu_percent"`
    MemMB          float64     `json:"memory_mb"`
    ListenAddrs    []ListenAddr `json:"listen_addrs"`
    Source         string      `json:"source"`        // systemd|agent|discovery
    Registered     bool        `json:"registered"`
    ServiceUnit    string      `json:"service_unit,omitempty"` // systemd unit name
}

type ServiceInfo struct {
    UnitName    string `json:"unit_name"`    // e.g. nginx.service
    State       string `json:"state"`        // active/inactive/failed
    SubState    string `json:"sub_state"`    // running/exited/dead
    MainPID     int    `json:"main_pid"`     // master PID（来自 systemctl show）
    WorkerPIDs  []int  `json:"worker_pids,omitempty"` // worker PIDs
    Enabled     bool   `json:"enabled"`
    Description string `json:"description"`
}

type ProcessControlBody struct {
    ControlID   string `json:"control_id"`
    Action      string `json:"action"`        // start|stop|restart|status
    ServiceName string `json:"service_name"`  // systemd unit or app name
    PID         *int   `json:"pid,omitempty"`
    Force       bool   `json:"force,omitempty"`
    Timeout     int    `json:"timeout,omitempty"` // 默认 30s
}
```

### 进程生命周期状态机

```
created → starting → running → stopping → stopped → removed
                      ↓
                   failed
```

| 状态 | 含义 |
|------|------|
| `created` | 注册表中有此应用记录，但尚未启动 |
| `starting` | 命令已下发，等待 ps 验证中 |
| `running` | `ps` 确认进程存活 |
| `stopping` | kill 已下发，等待进程退出 |
| `stopped` | `ps` 找不到进程（Server 端差异对比得出） |
| `failed` | start 后验证失败，或进程异常退出 |

agent 在 start/stop 命令执行后 sleep 1s 做 ps 主动验证，避免状态反馈延迟到下一轮采集。

### 采集周期与状态上报

| 事件 | 行为 |
|------|------|
| 每 5 分钟定时采集 | 全量上报当前存活进程 |
| Server 端差异对比 | 上次有本轮无 → 标记 stopped |
| 连续 3 轮消失 | 自动从 Neo4j 归档/软删除 |
| 进程状态变化 | 下轮采集自动反映 |

### systemd 多进程去重

同一 systemd unit 下的多个 PID（如 nginx master + N 个 worker）合并为一条 CMDB Process 记录：

```go
type ServiceInfo struct {
    UnitName    string   `json:"unit_name"`    // nginx.service
    State       string   `json:"state"`
    MainPID     int      `json:"main_pid"`     // master PID
    WorkerPIDs  []int    `json:"worker_pids,omitempty"`
}
```

CMDB `Process.pid` 记录 master PID，worker PIDs 存入 `extra_fields`。nginx 等多进程 systemd unit 在 CMDB 中只产生一条记录。查询命令：

```bash
systemctl show -p MainPID nginx.service
```

---

## 应用注册表设计

本工具启动的应用在 `/etc/opsflow/apps/` 下以 JSON 文件注册，每个应用一个文件：

```json
// /etc/opsflow/apps/myapp.json
{
  "name": "myapp",
  "version": 1,
  "created_at": "2026-06-15T10:00:00Z",
  "command": "/opt/myapp/bin/start.sh",
  "user": "appuser",
  "stop_command": "/opt/myapp/bin/stop.sh",
  "pid_file": "/var/run/myapp.pid",
  "env": {"JAVA_HOME": "/usr/lib/jvm/java-11"},
  "auto_restart": true
}
```

agent 通过 `app_registry.go` 管理：

| 方法 | 行为 |
|------|------|
| `Register(name, cmd, opts)` | 创建 `/etc/opsflow/apps/{name}.json` |
| `Unregister(name)` | 删除 JSON 文件 |
| `List()` | 扫描目录返回全部注册信息 |
| `FindByPID(pid)` | 遍历查找匹配 PID |
| `IsRegisteredPID(pid)` | 安全检查：PID 是否在注册表中 |

---

## 进程控制设计

### 控制路径

```
OpsFlow Pipeline (agent_process_start plugin)
  → Agent Server WebSocket
  → MsgProcessControl{action:"start", service_name:"nginx"}
  → agent.go 消息路由
  → 本地判断: systemctl is-enabled nginx ?
       YES → systemctl start nginx
       NO  → nohup /path/to/cmd &
  → sleep 1s → ps 主动验证
  → MsgProcessCtrlResult{success:true, pid:1234}
  → 结果回传
```

### 三种控制策略

| 操作 | 有 systemd unit | 无 systemd unit |
|------|----------------|----------------|
| start | `systemctl start $unit` | `nohup $cmd &` + 写 PID 文件 |
| stop | `systemctl stop $unit` | `kill $pid` / `kill -9 $pid` |
| restart | `systemctl restart $unit` | `kill -HUP $pid` 或 stop+start |
| status | `systemctl status $unit` | `ps -p $pid` |

### 业务层健康检查 — 由 Pipeline 完成

agent 不做业务层健康检查，只做 `ps` 进程级验证。不同应用的健康检查方式由 OpsFlow Pipeline 设计师灵活编排：

```
agent_process_start(service_name="nginx")
  → 返回 success, pid=1234

http_api_call(url="http://localhost:80/", method="GET")
  → 返回 200 OK
  → 确认 nginx 正常
```

| 应用 | 验证方式 | Pipeline 节点 |
|------|---------|-------------|
| nginx | HTTP 200 | `http_api_call` |
| MySQL | `mysqladmin ping` | `shell` |
| Java App | 端口监听 + HTTP health | `http_api_call` |
| 自定义 | 任意脚本 | `shell` |

### OpsFlow Plugin 原子

| 插件 | 输入参数 | 输出 |
|------|---------|------|
| `agent_process_start` | service_name, app_name, cmd, user | success, pid, message |
| `agent_process_stop` | service_name, app_name, force | success, message |
| `agent_process_restart` | service_name, app_name | success, message |

---

## Root vs 应用账户运行 Agent

| 维度 | Root 运行 | 应用账户运行（如 `opsflow`） |
|------|----------|---------------------------|
| **systemctl 操作** | ✅ 直接可用 | ❌ 需 sudo 或 polkit 授权 |
| **kill 任意进程** | ✅ 任何 PID | ❌ 只能 kill 自己的进程 |
| **采集全部进程** | ✅ ps aux 全部可见 | ❌ 只能看到自己的进程 |
| **ss 连接** | ✅ 全部连接 | ❌ 部分受限 |
| **写 PID 文件** | ✅ `/etc/opsflow/run/` | ✅ 需改路径 |
| **安全风险** | ❌ 被攻破=整机沦陷 | ✅ 影响范围有限 |
| **安装 systemd unit** | ✅ 无需额外配置 | ❌ 需 sudo |

**推荐：Agent 以 root 运行**，但通过注册表限制进程控制范围：

```go
func (e *Executor) processStop(cmd *ProcessControlBody) *ProcessCtrlResult {
    if cmd.PID != nil {
        // 安全检查：只能终止注册表中的进程
        if !e.registry.IsRegisteredPID(*cmd.PID) {
            return &ProcessCtrlResult{Success: false, Message: "PID not managed by this agent"}
        }
    }
    // 执行 kill
}
```

控制命令的鉴权在 OpsFlow Server 端处理，agent 不校验身份。

---

## 网络拓扑采集

### 数据流

```
Agent A: ss -tnp → remote_connections → WS 上报
Agent B: ss -tlnp → listen_addresses → WS 上报
                ↓
       Agent Server 端拓扑匹配引擎
                ↓
       Django internal_views → Neo4j CALLS 关系
```

### Server 端拓扑匹配（process_topology.py）

```python
class ProcessTopologyBuilder:
    """全量拓扑匹配引擎"""

    def rebuild(self):
        processes = self._get_all_processes()
        listen_map = self._build_listen_map(processes)

        for src in processes:
            for conn in src.connections:
                dst_id = listen_map.get(f"{conn.remote_ip}:{conn.remote_port}")
                if dst_id:
                    self._ensure_calls(src.instance_id, dst_id)
```

### 全链路示例

```
Agent A: myapp → 连接 10.0.1.2:3306
Agent B: mysqld → 监听 0.0.0.0:3306
                ↓
Neo4j: (myapp)-[:CALLS]->(mysqld)

DR Service 查询:
MATCH (p:Process)-[:CALLS*1..5]->(dep:Process)
RETURN p, dep
→ 得到调用链: myapp → mysqld → redis
```

---

## DR 集成

### 增强拓扑查询

```cypher
MATCH (g:DrGroup {instance_id: $gid})
<-[:BELONGS_TO]-(p:Process)
-[:CALLS*1..5]->(dep:Process)
OPTIONAL MATCH (p)-[:RUNS_ON]->(ph:Host)
OPTIONAL MATCH (dep)-[:RUNS_ON]->(dh:Host)
RETURN g, p, dep, ph, dh
```

### Pipeline 编排增强

| 当前（无 CALLS） | 增强后（有 CALLS） |
|-----------------|-------------------|
| 停止全部 → 启动全部 → 验证 | 按依赖反序停止：C→B→A |
| — | 按依赖正序启动：A'→B'→C' |
| 全量并行 | 依赖链串行 + 无依赖可并行 |

---

## CMDB Process 模型增强

现有模型追加字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | systemd \| agent \| discovery |
| `registered` | bool | 是否为本工具注册的受管应用 |
| `service_unit` | string | systemd unit name（如 nginx.service） |
| `extra_fields` | json | 扩展信息（如 worker_pids、env 等） |
| `app_version` | string | 应用版本号 |
| `auto_restart` | bool | 崩溃后自动重启标志 |

---

## SUSE vs RedHat 兼容

所有进程控制命令在两者上行为一致，无分支处理：

| 能力 | SUSE | RedHat |
|------|------|--------|
| `systemctl` | ✅ | ✅ |
| `ps aux` | ✅ | ✅ |
| `ss -tlnp` | ✅ | ✅ |
| `ss -tnp` | ✅ | ✅ |
| `kill` / `killall` | ✅ | ✅ |

---

## 错误处理

| 场景 | 行为 |
|------|------|
| systemd unit 不存在 | 回退直接命令 |
| PID 文件丢失（stop） | 报 "process not found" |
| 进程已运行（start） | 返回 "already running" |
| kill 无权限 | 报 "permission denied" |
| 超时（默认 30s） | timeout 错误 |
| ps/ss 命令不存在 | 跳过扫描，报 warning |
| WS 断连 | 采集结果缓存，重连后重发 |

---

## 文件清单

| # | 文件 | 类型 | 说明 |
|---|------|------|------|
| 1 | `agent/internal/core/process_collector.go` | 新增 | 进程采集核心 |
| 2 | `agent/internal/core/app_registry.go` | 新增 | 应用注册表 |
| 3 | `agent/pkg/protocol/types.go` | 追加 | 新消息结构体 |
| 4 | `agent/internal/core/agent.go` | +3 行 | 消息路由 |
| 5 | `agent/internal/core/collector.go` | 不改 | — |
| 6 | `agent/internal/core/executor.go` | 不改 | — |
| 7 | `agent_app/services/process_topology.py` | 新增 | 服务端拓扑匹配 |
| 8 | `agent_app/views/process_collect.py` | 新增 | 采集结果接收 API |
| 9 | `opsflow/plugins/agent/agent_process_start.py` | 新增 | 启动原子 |
| 10 | `opsflow/plugins/agent/agent_process_stop.py` | 新增 | 停止原子 |
| 11 | `opsflow/plugins/agent/agent_process_restart.py` | 新增 | 重启原子 |
| 12 | `opsflow/services/dr_service.py` | 增强 | CALLS 链查询 |
