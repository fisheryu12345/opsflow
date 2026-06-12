# Process CMDB 建模与生命周期管理 — 业务 DR 基础层设计

> 创建日期: 2026-06-12
> 状态: 设计草案
> 涉及 App: cmdb, opsflow

---

## 1. 概述

为业务 DR (Disaster Recovery) 系统构建基础层：将进程/服务注册到 CMDB Neo4j，通过 ProcessManager 类实现主机端定时采集和自动上报，提供 OpsFlow 原子实现进程启停和状态检查。

### 核心能力

- 进程模型定义（Process）存储在 CMDB Neo4j，含监听地址和远程连接信息
- ProcessManager 类内置 APScheduler 定时采集，通过 ss + ps 命令发现进程，上报到 CMDB API
- 自动发现进程间的 CALLS 关系（A主机进程 → B主机进程，含端口）
- OpsFlow 标准原子：process_start / process_stop / process_status
- 只采集指定应用用户的进程，不处理系统进程

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────┐
│  主机 A (Host)                                    │
│                                                   │
│  ProcessManager (Python 类，systemd 服务)           │
│  ┌─────────────────────────────────────────────┐  │
│  │  APScheduler (定时任务，默认 5 分钟)           │  │
│  │    └─ discover() → register()                │  │
│  │                                              │  │
│  │  discover():                                 │  │
│  │    ps aux → 进程列表 (按 app_users 过滤)       │  │
│  │    ss -tlnp → 监听端口 listen_addresses       │  │
│  │    ss -tnp  → 活跃连接 remote_connections     │  │
│  │                                              │  │
│  │  register():                                 │  │
│  │    HTTP POST → CMDB API → Neo4j              │  │
│  │    → 创建/更新 Process 节点                   │  │
│  │    → RUNS_ON → 关联本机 Host                  │  │
│  │    → CALLS → 交叉匹配远程进程                  │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ── HTTP → CMDB API (进程上报)                     │
│  ── Ansible Tower (process_start/stop 原子)        │
└──────────────────────────────────────────────────┘
         │ CALLS (跨主机)
         ▼
┌──────────────────────────────────────────────────┐
│  主机 B (Host)                                    │
│  Process(java:8080) ←─ ProcessManager            │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  CMDB Neo4j                                       │
│  (:Process)—[:RUNS_ON]→(:Host)                    │
│  (:Process)—[:CALLS]→(:Process)                   │
│  (:Process {listen_addresses, remote_connections}) │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  OpsFlow Pipeline                                 │
│  process_start → process_status → process_stop    │
│  (继承 TowerBasePlugin，通过 Tower 远程执行)        │
└──────────────────────────────────────────────────┘
```

---

## 3. CMDB 模型定义

### 3.1 Process 模型

在 CMDB 中创建 ModelDefinition `code='Process'`，对应 Neo4j Label `:Process`。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 进程名（nginx, java, mysql...） |
| `pid` | integer | 是 | 进程 PID |
| `user` | string | 是 | 运行用户 |
| `status` | enum | 是 | running / stopped / zombie |
| `command` | string | 否 | 启动命令（截取前 200 字符） |
| `listen_addresses` | json | 否 | 监听地址列表 |
| `remote_connections` | json | 否 | 主动外连列表 |
| `cpu_percent` | float | 否 | CPU 使用率 |
| `memory_mb` | integer | 否 | 内存占用(MB) |
| `host_instance_id` | string | 是 | 所属主机 CMDB instance_id |

**listen_addresses 格式：**
```json
[
  {"ip": "0.0.0.0", "port": 80, "protocol": "tcp"},
  {"ip": "127.0.0.1", "port": 3306, "protocol": "tcp"}
]
```

**remote_connections 格式：**
```json
[
  {"remote_ip": "192.168.1.2", "remote_port": 8080, "protocol": "tcp", "local_port": 54321},
  {"remote_ip": "10.0.0.5", "remote_port": 6379, "protocol": "tcp", "local_port": 43210}
]
```

### 3.2 关系类型 (AssociationType)

| asst_id | 说明 | 源→目标 | 方向 |
|---------|------|---------|------|
| `RUNS_ON` | 进程运行在主机上 | Process → Host | src_to_dest |
| `CALLS` | 进程调用另一进程（跨主机） | Process → Process | src_to_dest |
| `EXPOSES` | 进程暴露端口 | Process → Process（被调用方） | dest_to_src |

### 3.3 自动创建原则

- **RUNS_ON**: register() 时自动建立 `(Process)-[:RUNS_ON]->(Host {instance_id: host_instance_id})`
- **CALLS**: 遍历所有进程的 `remote_connections`，匹配 CMDB 中其他机的 `listen_addresses`，自动建立 `(LocalProcess)-[:CALLS]->(RemoteProcess)`
- **EXPOSES**: 与 CALLS 对称，自动创建 `(RemoteProcess)-[:EXPOSES]->(LocalProcess)`

---

## 4. ProcessManager 类设计

### 4.1 类接口

```python
class ProcessManager:
    """进程管理器 — 采集、上报、启停
    
    部署方式: 在目标主机上作为 service/systemd 运行
    定时任务: 内置 APScheduler，每 interval 秒执行 discover + register
    
    Args:
        cmdb_api_url: CMDB API 基础 URL
        api_token: API 认证令牌
        host_instance_id: 本主机的 CMDB instance_id
        app_users: 只采集这些系统用户的进程
        interval: 采集间隔（秒），默认 300
    """

    def discover(self) -> list[dict]:
        """采集本机进程信息
        
        执行流程:
        1. ps aux | grep app_users → 进程基础信息 (pid, name, user, cpu%, mem, command)
        2. ss -tlnp -p → 监听端口 → 关联到 PID → listen_addresses
        3. ss -tnp -p  → 活跃连接 → 关联到 PID → remote_connections
        4. 按 PID 合并为统一结构
        Returns: [{name, pid, user, status, listen_addresses, remote_connections, ...}]
        """

    def register(self, processes: list[dict]) -> dict:
        """上报进程到 CMDB
        
        1. 对每个进程: POST /api/cmdb/instances/Process/ (create or update)
        2. 建立 RUNS_ON: POST /api/cmdb/instance-associations/create_relation/
        3. CALLS 发现: 交叉匹配 remote_connections → 自动建立 CALLS
        4. 清理: 之前存在但本次未出现的进程 → 标记 status=stopped
        Returns: {created: N, updated: N, calls_created: N}
        """

    def start_scheduler(self):
        """启动定时采集循环"""

    def stop_scheduler(self):
        """停止定时采集"""

    def status(self, pid_or_name: str) -> dict:
        """查询单个进程状态（本地 ps 检查）"""

    def start(self, command: str, user: str = None) -> dict:
        """启动进程（subprocess.Popen）"""

    def stop(self, pid: int, force: bool = False) -> dict:
        """停止进程（kill / kill -9）"""
```

### 4.2 discover() 实现细节

```python
def discover(self) -> list[dict]:
    import subprocess
    import json
    import re
    
    # Step 1: ps aux 获取进程列表
    ps_output = subprocess.run(
        ["ps", "aux"], capture_output=True, text=True
    ).stdout
    
    users_filter = "|".join(self.app_users)
    # 过滤只保留指定用户的进程行
    process_rows = [l for l in ps_output.split("\n")[1:]
                    if any(u in l for u in self.app_users)]
    
    processes = {}
    for row in process_rows:
        parts = row.split(None, 10)
        if len(parts) < 11:
            continue
        pid = int(parts[1])
        processes[pid] = {
            "name": parts[10].split("/")[-1].split()[0][:64],
            "pid": pid,
            "user": parts[0],
            "status": "running",
            "cpu_percent": float(parts[2]),
            "memory_mb": round(float(parts[3]) * 1024 / 1024, 1)  # VSZ→MB
                if parts[3] else 0,
            "command": parts[10][:200],
            "listen_addresses": [],
            "remote_connections": [],
        }
    
    # Step 2: ss -tlnp 获取监听端口
    ss_listen = subprocess.run(
        ["ss", "-tlnp", "-p"], capture_output=True, text=True
    ).stdout
    for line in ss_listen.split("\n")[1:]:
        if not line.strip():
            continue
        # ss output: State Recv-Q Send-Q Local:port Peer:port Users
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[3]
        proto = parts[0].lower()
        # 提取 PID from users column "users:(("nginx",pid=1234,fd=5))"
        pid_match = re.search(r"pid=(\d+)", line)
        if not pid_match:
            continue
        pid = int(pid_match.group(1))
        if pid in processes:
            ip_port = local.rsplit(":", 1)
            processes[pid]["listen_addresses"].append({
                "ip": ip_port[0] if len(ip_port) > 1 else "0.0.0.0",
                "port": int(ip_port[-1].split(",")[0]),
                "protocol": proto,
            })
    
    # Step 3: ss -tnp 获取活跃连接
    ss_conn = subprocess.run(
        ["ss", "-tnp", "-p"], capture_output=True, text=True
    ).stdout
    for line in ss_conn.split("\n")[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[3]
        remote = parts[4]
        proto = parts[0].lower()
        pid_match = re.search(r"pid=(\d+)", line)
        if not pid_match:
            continue
        pid = int(pid_match.group(1))
        if pid in processes:
            loc_ip, loc_port = local.rsplit(":", 1)
            rem_ip, rem_port = remote.rsplit(":", 1)
            processes[pid]["remote_connections"].append({
                "remote_ip": rem_ip,
                "remote_port": int(rem_port),
                "protocol": proto,
                "local_port": int(loc_port),
            })
    
    return list(processes.values())
```

### 4.3 register() 实现细节

```python
def register(self, processes: list[dict]) -> dict:
    import requests
    
    headers = {"Authorization": f"Bearer {self.api_token}"}
    base = self.cmdb_api_url.rstrip("/")
    stats = {"created": 0, "updated": 0, "calls_created": 0}
    
    # 获取当前已注册的进程列表（用于清理）
    resp = requests.get(
        f"{base}/instances/Process/",
        params={"filters": json.dumps({"host_instance_id": self.host_instance_id})},
        headers=headers,
    )
    existing = {p["instance_id"]: p for p in resp.json().get("items", [])}
    current_names = set()
    
    for proc in processes:
        # upsert: 按 host_instance_id + pid 匹配
        match = [e for e in existing.values()
                 if e.get("pid") == proc["pid"]]
        if match:
            # 更新
            rid = match[0]["instance_id"]
            requests.put(
                f"{base}/instances/Process/{rid}/",
                json=proc, headers=headers,
            )
            stats["updated"] += 1
        else:
            # 创建
            proc["host_instance_id"] = self.host_instance_id
            resp = requests.post(
                f"{base}/instances/Process/",
                json=proc, headers=headers,
            )
            rid = resp.json().get("instance_id", "")
            current_names.add(rid)
            stats["created"] += 1
        
        # 建立 RUNS_ON 关系
        requests.post(
            f"{base}/instance-associations/create_relation/",
            json={
                "src_id": rid, "dst_id": self.host_instance_id,
                "asst_type_id": "RUNS_ON",
            },
            headers=headers,
        )
    
    # 交叉匹配 CALLS
    stats["calls_created"] = self._discover_calls(processes)
    
    # 清理已消失的进程（标记 stopped）
    for eid, ep in existing.items():
        if ep.get("name") not in current_names:
            requests.patch(
                f"{base}/instances/Process/{eid}/",
                json={"status": "stopped"}, headers=headers,
            )
            stats["updated"] += 1
    
    return stats

def _discover_calls(self, local_processes: list[dict]) -> int:
    """交叉匹配 remote_connections → 建立 CALLS 关系"""
    # 收集所有本地进程的 remote_connections
    all_remotes = []
    for p in local_processes:
        for conn in p.get("remote_connections", []):
            all_remotes.append(conn)
    
    if not all_remotes:
        return 0
    
    # 查询 CMDB 中所有其他主机的 Process，匹配 listen_addresses
    resp = requests.get(
        f"{base}/topology/search/",
        params={"q": json.dumps(all_remotes[:50])},
        headers=headers,
    )
    # ... 匹配逻辑
    return calls_count
```

---

## 5. OpsFlow 进程生命周期原子

### 5.1 process_start

| 元数据 | 值 |
|--------|-----|
| `code` | `process_start` |
| `name` | 进程启动 |
| `group` | Process（新分组） |
| `risk_level` | high |
| 基类 | `TowerBasePlugin` |

**表单字段：**

| tag_code | type | 必填 | 说明 |
|----------|------|------|------|
| `instance_id` | input | 是 | CMDB Process 的 instance_id |

**执行流程：**
1. execute() → 通过 CMDB API 获取 Process 的 `command` 和所在 `Host` 信息
2. Tower 在目标主机上执行 `nohup {command} > /dev/null 2>&1 &`
3. schedule() 轮询 Tower 作业状态
4. 完成后调用 CMDB API 更新 Process.status = 'running'

### 5.2 process_stop

| 元数据 | 值 |
|--------|-----|
| `code` | `process_stop` |
| `name` | 进程停止 |
| `group` | Process |
| `risk_level` | high |
| 基类 | `TowerBasePlugin` |

**表单字段：**

| tag_code | type | 必填 | 说明 |
|----------|------|------|------|
| `instance_id` | input | 是 | CMDB Process 的 instance_id |
| `force` | checkbox | 否 | 是否强制 kill -9，默认 false |

**执行流程：**
1. execute() → 获取 Process 的 pid
2. Tower 执行 `kill {pid}` 或 `kill -9 {pid}`
3. schedule() 轮询/验证进程已消失
4. 更新 CMDB Process.status = 'stopped'

### 5.3 process_status

| 元数据 | 值 |
|--------|-----|
| `code` | `process_status` |
| `name` | 进程状态检查 |
| `group` | Process |
| `risk_level` | low |
| 基类 | `TowerBasePlugin` |

**表单字段：**

| tag_code | type | 必填 | 说明 |
|----------|------|------|------|
| `instance_id` | input | 是 | CMDB Process 的 instance_id |

**输出 Schema：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | running / stopped / zombie |
| `pid` | int | 进程 PID |
| `cpu_percent` | float | CPU 使用率 |
| `memory_mb` | int | 内存占用 |
| `listen_addresses` | json | 当前监听端口列表 |
| `remote_connections` | json | 当前活跃连接列表 |

---

## 6. 种子数据

需要在 CMDB 中预先创建的种子数据：

**ModelDefinition:**
- `Process` — 进程模型

**ModelField (Process):**
- name(string), pid(integer), user(string), status(enum), command(string)
- listen_addresses(json), remote_connections(json)
- cpu_percent(float), memory_mb(integer), host_instance_id(string)

**AssociationType:**
- `RUNS_ON` — 运行在
- `CALLS` — 调用
- `EXPOSES` — 暴露

---

## 7. 文件位置

| 文件 | 说明 |
|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | **新建** — 种子数据命令 |
| `backend/opsflow/plugins/process/__init__.py` | **新建** — Process 插件包 |
| `backend/opsflow/plugins/process/process_start.py` | **新建** — 进程启动原子 |
| `backend/opsflow/plugins/process/process_stop.py` | **新建** — 进程停止原子 |
| `backend/opsflow/plugins/process/process_status.py` | **新建** — 进程状态检查原子 |
| `agent/agent/process_manager.py` | **新建** — ProcessManager 类 |
| `agent/setup.py` | **修改** — 添加 APScheduler 和 requests 依赖 |

---

## 8. DR 站点与拓扑可视化 — Phase 2

### 8.1 DrSite 模型

在 CMDB 中创建 ModelDefinition `code='DrSite'`，实例存储在 Neo4j 中，走现有的 DynamicInstanceViewSet CRUD。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 站点名称（如「主站-北京」、「灾备站-上海」） |
| `site_type` | enum | 是 | primary / standby / dr |
| `region` | string | 否 | 站点地域（北京 / 上海 / cn-hangzhou） |
| `status` | enum | 是 | normal / warning / down |
| `description` | string | 否 | 站点描述 |
| `priority` | integer | 是 | 切换优先级（1=最高），默认 1 |

### 8.2 DrGroup 模型

`DrGroup` 是 DR 切换的最小逻辑单元，包含一个主站服务栈和对应的备站资源。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | DR 组名称（如「核心交易-DR组」） |
| `description` | string | 否 | 描述 |
| `status` | enum | 是 | active / failed_over / recovering / disconnected |

### 8.3 新增关系类型 (AssociationType)

| asst_id | 说明 | 源→目标 | 方向 |
|---------|------|---------|------|
| `FAILOVER_TO` | DrSite failover 到另一 DrSite | DrSite → DrSite | src_to_dest |
| `BELONGS_TO` | Process 属于某个 DrGroup | Process → DrGroup | src_to_dest |
| `PROTECTED_BY` | DrGroup 保护哪些 Process | DrGroup → Process | src_to_dest |
| `SITE_CONTAINS` | DrSite 包含哪些 Host | DrSite → Host | src_to_dest |

### 8.4 拓扑结构示例

```
DrSite(primary: 北京)
  │ SITE_CONTAINS
  ├─ Host(web-01) → Process(nginx:80)
  ├─ Host(app-01) → Process(java:8080)
  └─ Host(db-01)  → Process(mysql:3306)
  │
  │ FAILOVER_TO
  ▼
DrSite(standby: 上海)
  │ SITE_CONTAINS
  ├─ Host(web-dr-01) → Process(nginx:80)
  ├─ Host(app-dr-01) → Process(java:8080)
  └─ Host(db-dr-01)  → Process(mysql:3306)

DrGroup(核心交易-DR组)
  │ BELONGS_TO
  ├─ Process(nginx:80 on 北京)
  ├─ Process(java:8080 on 北京)
  └─ Process(mysql:3306 on 北京)
  │ PROTECTED_BY
  └─ Process(nginx:80 on 上海) ← 备站对应进程
```

### 8.5 前端力导向图

在现有 CMDB 页面新增一个 **"DR 拓扑" tab**，使用 `@antv/g6` 的 `Graph`（非 TreeGraph）做力导向图。

**节点视觉：**

| 节点类型 | 形状 | 颜色 | 说明 |
|----------|------|------|------|
| DrSite (primary) | 大圆角矩形 | 蓝色 #1890ff | 主站点 |
| DrSite (standby) | 大圆角矩形 | 红色 #f5222d | 备站点 |
| Host | 小矩形 | 灰色 #8c8c8c | 按站点分组排列 |
| Process | 小圆 | 绿色/红色/灰色 | 按 status 着色 |

**边视觉：**

| 关系类型 | 样式 | 说明 |
|----------|------|------|
| FAILOVER_TO | 红色粗箭头（3px） | 主→备 failover 方向 |
| SITE_CONTAINS | 灰色虚线（1.5px） | 站点包含主机 |
| RUNS_ON | 灰色实线（1px） | 进程运行在主机上 |
| CALLS | 淡蓝色虚箭头（2px） | 跨主机进程调用 |
| BELONGS_TO | 橙色点线（1px） | 进程属于 DR 组 |

**交互：**
- 鼠标悬停节点 → 高亮显示其一阶邻居，其余变暗
- 右键菜单 → 查看属性 / 执行切换 / 查看影响分析
- 力导向布局 → 自动按站点点分组聚合

### 8.6 种子数据

新增到 `seed_dr_models.py` management command：

**ModelDefinition:**
- `DrSite` — DR 站点
- `DrGroup` — DR 保护组

**AssociationType:**
- `FAILOVER_TO` — 站点间容灾切换
- `BELONGS_TO` — 进程归属 DR 组
- `PROTECTED_BY` — DR 组保护进程
- `SITE_CONTAINS` — 站点包含主机

---

## 9. AI 辅助 DR 编排 — Phase 3

### 9.1 核心流程

DR pipeline 的入口在 **新建 Template 的 Step 2**，作为第 4 个选项（与空白、AI 生成、克隆并列）：

```
用户在 CreateTemplateWizard Step 2 选择「DR 切换」
         │
         ▼
选择目标 Service/DrGroup → AI 读取 Neo4j 拓扑
         │
         ▼
AI 生成 DR pipeline 模板（process_stop → process_start → process_status）
         │
         ▼
用户在 Designer 中打开模板，可审查/修改
         │
         ▼
通过 SubmitWizard 提交执行（含 ServiceNow Change Request 审批）
         │
         ▼
DR pipeline 执行 → G6 实时展示切换进度（WebSocket）
```

### 9.2 CreateTemplateWizard 新增「DR 切换」选项

**Step 2** 新增第 4 个 mode 卡片 `method === 'dr'`，内容：

```html
<!-- DR 切换卡片 -->
<el-radio-card value="dr" icon="Switch">
  DR 切换
  <template #description>选择目标服务，自动生成灾备切换流程</template>
</el-radio-card>

<!-- DR 专属表单 -->
<template v-if="method === 'dr'">
  <el-form-item label="目标服务 / DR 组">
    <el-select v-model="drGroupId" placeholder="选择要切换的服务...">
      <el-option v-for="g in drGroups" :key="g.id" :label="g.name" :value="g.id" />
    </el-select>
  </el-form-item>
</template>
```

**handleCreate()** 新增 DR 分支：

```javascript
if (method.value === 'dr') {
  // 调用 AI 生成 DR pipeline 的 API
  const res = await CreateDrPipeline({ dr_group_id: drGroupId.value })
  // 结果包含 pipeline_tree + 建议说明
  template = await CreateTemplate({
    name: res.name, category: 'dr',
    pipeline_tree: res.pipeline_tree,
  })
}
```

### 9.3 后端 API: `create_dr_pipeline`

**位置:** `backend/opsflow/views/mixins/template_dr.py` (新文件)

```python
class TemplateDRMixin:
    @action(detail=False, methods=['post'])
    def create_dr_pipeline(self, request):
        """AI 生成 DR 切换 pipeline
        
        输入: {"dr_group_id": "xxx"}
        流程:
          1. 读取 Neo4j → DrGroup + 关联的 Process + 拓扑关系
          2. 构建拓扑描述文本
          3. 调用 AI (ai_text_gen / LLM) → 生成 pipeline_tree
          4. pipeline_tree 含 process_stop/start/status 节点
          5. 返回 {name, pipeline_tree, description}
        """
```

**AI prompt 模板：**

```
你是一个运维 DR 专家。以下是一个 DR 组及其关联进程的拓扑信息：

DR组: {dr_group_name}
主站: {primary_site_name}
备站: {standby_site_name}

主站进程:
{process_list}

备站进程:
{standby_process_list}

进程间调用关系:
{calls_relations}

请生成一个标准 DR 切换 pipeline，步骤包括：
1. 停止主站进程（process_stop）
2. 启动备站进程（process_start）
3. 验证备站健康（process_status）
```

### 9.4 G6 实时进度展示

执行 DR pipeline 时，通过现有 WebSocket 推送机制，在 DR 拓扑图（力导向图 tab）上实时高亮：

- 正在操作的 Process 节点 → 闪烁/黄色高亮
- 已停止的 Process → 红色
- 已启动的 Process → 绿色
- 已完成所有操作的 Process → 灰色带绿色边框

**数据流：**

```
pipeline 节点执行完成
  → signals/state.py 更新 execution context
  → _promote_results 写入 _node_outputs
  → WebSocket 推送 (push_to_user, topic="dr_progress")
  → 前端 G6 收到消息，更新节点着色
```

### 9.5 新增/修改文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/opsflow/components/dialogs/CreateTemplateWizard.vue` | **修改** — Step 2 新增 DR 切换选项 + 表单 |
| `web/src/views/apps/opsflow/api/templates.ts` | **修改** — 新增 `CreateDrPipeline()` API 函数 |
| `backend/opsflow/views/mixins/template_dr.py` | **新建** — `create_dr_pipeline` API 端点 |
| `backend/opsflow/views/template_views.py` | **修改** — 注册 TemplateDRMixin |
| `web/src/views/apps/cmdb/index.vue` | **修改** — DR 拓扑 tab 接入 WebSocket 进度 |

## 10. 未纳入范围

- ❌ 进程启停通过 Agent WebSocket — 统一走 Tower
- ❌ 全量系统进程采集 — 只采集 app_users 指定用户
