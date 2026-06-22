# CMDB 层次重构: Service → Application → Process

> 提交: df82a1c9 | 日期: 2026-06-17
> 涉及 App: cmdb
> 类型: 功能新增+架构重构

---

## 背景

原 CMDB 模型将所有节点扁平化为 Process（PID 级），DR 操作直接作用在进程上，缺乏应用和业务层的抽象。CALLS 拓扑匹配结果是 Process→Process，但在有 4 个 nginx worker 进程的场景下毫无意义。

**问题：**
- DrGroup 直接关联 Process（PID 级），太细
- CALLS 在 Process 间建立，但 nginx 有 4 个 worker 都各自建 CALLS
- 没有 Application 层承载启停语义
- 没有 业务(Service) 层组织多个应用

**目标层次：**
```
DrGroup (容灾组 = 业务层)
  ├── PROTECTED_BY (was BELONGS_TO)
  │    └── Application (应用) — e.g. "nginx", "grafana", "mysql"
  │         ├── CALLS → Application (应用间依赖拓扑)
  │         └── HAS_PROCESS → Process (PID 级进程)
  └── SITE_CONTAINS → Host
       └── RUNS_ON → Process
```

## 实现方案

### 新增模型

| Neo4j Label | 来源 | 用途 |
|------------|------|------|
| `:Application` | `AgentInstance.tags.registered_apps` | 应用层抽象 |
| `:Process` (已有) | Agent 采集 `ps aux` | PID 级进程 |
| `:Host` (已有) | Agent 采集 `host_info` | 主机 |

### 新增关系

| 关系 | 说明 |
|------|------|
| `(a:Application)-[:HAS_PROCESS]->(p:Process)` | 应用包含的进程 |
| `(a:Application)-[:CALLS]->(a2:Application)` | 应用间调用拓扑 |
| `(a:Application)-[:PROTECTED_BY]->(g:DrGroup)` | 应用归属 DR 组 |

### 关键代码

#### 种子数据 — `seed_dr_models.py`

新增 `APPLICATION_FIELDS` 和 `_seed_application_model()` / `_seed_application_associations()`：

```python
APPLICATION_FIELDS = [
    ("name", "应用名称", "string", True, "", None, ""),
    ("host_ip", "主机 IP", "string", True, "", None, ""),
    ("command", "启动命令", "string", False, "", None, ""),
    ("status", "应用状态", "enum", True, "running", ["running", "stopped"], ""),
    ("auto_restart", "自动重启", "boolean", False, False, None, ""),
    ("registered", "已注册", "boolean", False, True, None, ""),
]
```

Association 注册：

```python
associations = [
    (app_md, proc_md, "HAS_PROCESS", "1:n", "none"),
    (app_md, drg_md, "PROTECTED_BY", "n:1", "none"),
    (app_md, app_md, "CALLS", "n:n", "none"),
]
```

新增的 `HAS_PROCESS` AssociationType 定义为 `src_to_dest_note: "应用包含进程"`。

#### 进程同步 — `internal_views.py:_sync_applications()`

在 `_sync_processes_to_cmdb()` 末尾调用 `_sync_applications(session, agent_id, host_ip, processes, now)`：

```python
def _sync_applications(session, agent_id, host_ip, processes, now):
    agent = AgentInstance.objects.filter(agent_id=agent_id).first()
    if not agent: return
    registered_apps = (agent.tags or {}).get('registered_apps', [])
    for app in registered_apps:
        app_name = app.get('name', '')
        if not app_name: continue
        # MERGE Application 节点
        session.run(
            "MERGE (a:Application {name: $name, host_ip: $host_ip}) ...",
            name=app_name, host_ip=host_ip,
            props={'command': ..., 'auto_restart': ..., 'status': 'running'},
        )
        # 匹配进程名/命令 → 创建 HAS_PROCESS
        for proc in processes:
            if proc_name == app_name or cmd_basename in proc_cmdline:
                session.run(
                    "MATCH (a:Application {name: $aname, host_ip: $host_ip}) "
                    "MATCH (p:Process {host_ip: $host_ip, pid: $pid}) "
                    "MERGE (a)-[:HAS_PROCESS]->(p)"
                )
```

#### Application 级 CALLS — `internal_views.py:_match_calls_topology()`

在 Process 级 CALLS 建立后，通过 HAS_PROCESS 追溯 Application：

```python
# 从 connection 的 src_pid→找到 Application(src)→Process(dst)→Application(dst)
src_app = session.run(
    "MATCH (a:Application)-[:HAS_PROCESS]->(p:Process {host_ip: $host_ip, pid: $pid}) "
    "RETURN a.name, a.host_ip LIMIT 1", host_ip=host_ip, pid=src_pid,
).single()
dst_app = session.run(
    "MATCH (a:Application)-[:HAS_PROCESS]->(p:Process {host_ip: $host_ip, pid: $pid}) "
    "RETURN a.name, a.host_ip LIMIT 1", host_ip=dst['host_ip'], pid=dst['pid'],
).single()
if src_app and dst_app and (src_app['aname'] != dst_app['aname'] or src_app['ahost'] != dst_app['ahost']):
    session.run(
        "MATCH (src:Application {name: $sname, host_ip: $shost}) "
        "MATCH (dst:Application {name: $dname, host_ip: $dhost}) "
        "MERGE (src)-[:CALLS {remote_port: $port}]->(dst)"
    )
```

#### Agent 注册/注销时同步 — `agent_app/apps.py:get_registry_pids()`

修复未实现的函数，通过 Neo4j 查询已注册应用的 PID：

```python
def get_registry_pids(agent_id: str) -> set:
    agent = AgentInstance.objects.filter(agent_id=agent_id).first()
    if not agent: return set()
    apps = (agent.tags or {}).get('registered_apps', [])
    # 查询 Neo4j: MATCH (p:Process {host_ip, status:'running'})
    # WHERE p.name = app_name OR p.cmdline CONTAINS cmd_basename
    # RETURN p.pid
```

#### DR 前端拓扑视图 — `cmdb/index.vue`

DR Tab 改为「选择 DR Group 后才加载拓扑」：

```typescript
function switchDrTab() {
  store.setActiveView('dr')
  if (!drGroupList.value.length) loadDrGroups()
  drTopoNodes.value = []
  drTopoEdges.value = []
  selectedDrGroup.value = ''
}
```

`loadDrTopology()` 增加早退逻辑，边过滤新增 `PROTECTED_BY` / `HAS_PROCESS`：

```typescript
if (!selectedDrGroup.value) { drTopoNodes.value = []; drTopoEdges.value = []; return }
// PROTECTED_BY → Application
for (const e of allEdges) {
  if (e.to === gid && (e.type === 'PROTECTED_BY' || e.type === 'BELONGS_TO')) matchedIds.add(e.from)
}
// HAS_PROCESS → Process
for (const e of allEdges) {
  if (matchedIds.has(e.from) && e.type === 'HAS_PROCESS') matchedIds.add(e.to)
}
```

### 数据流

```
Agent 采集 ps aux
  → WS → Agent Server → POST /api/agent/internal/collect_reports/
  → _sync_processes_to_cmdb() 写 :Process 节点 + RUNS_ON
  → _match_calls_topology() 写 Process CALLS + Application CALLS
  → _sync_applications() 写 :Application 节点 + HAS_PROCESS

注册 App (UI)
  → POST /api/agent/internal/apps/ {action: register}
  → 存 DB AgentInstance.tags.registered_apps
  → 创建 Neo4j :Application 节点

DR Pipeline 生成
  → MATCH (g:DrGroup)<-[:PROTECTED_BY]-(a:Application)
  → 查询 Application 间 CALLS
  → LLM 生成 nodes/edges Pipeline
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | Application 模型定义、HAS_PROCESS/PROTECTED_BY 关联类型种子 |
| `backend/agent_app/internal_views.py` | `_sync_applications()` 创建 Application 节点；`_match_calls_topology()` 建立 Application 级 CALLS |
| `backend/agent_app/apps.py` | `get_registry_pids()` 修复死代码 |
| `backend/opsflow/views/mixins/template_dr.py` | 修复 LLM 客户端调用 |
| `web/src/views/apps/cmdb/index.vue` | DR 拓扑视图延迟加载、PROTECTED_BY/HAS_PROCESS 边过滤 |

## 使用方式

1. 重建种子数据: `python manage.py seed_dr_models --force; python manage.py seed_dr_models --mock`
2. 监控业务 mock: `python -X utf8 manage.py shell --command="exec(open('seed_monitor_dr.py', encoding='utf-8').read())"`
3. DR 预览: `POST /api/opsflow/templates/preview_dr_topology/ {dr_group_id}`
4. DR 生成: `POST /api/opsflow/templates/create_dr_pipeline/ {dr_group_id}`
5. 前端 CMDB → DR 拓扑 → 选择 DR Group → 查看应用拓扑

### 关联文档

- 相关功能文档: [DR 容灾 Pipeline](features/2026-06-17-dr-pipeline-adapter.md)
