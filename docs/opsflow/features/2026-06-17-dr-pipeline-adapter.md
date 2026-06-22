# DR Pipeline 服务适配 Application 层级

> 提交: df82a1c9 | 日期: 2026-06-17
> 涉及 App: opsflow
> 类型: 功能新增+修复

---

## 背景

DR Pipeline 生成原基于 Process 级拓扑查询（BELONGS_TO → Process → CALLS），层次重构后 DrGroup 通过 Application 关联。DR 服务需要适配新的 Application 层级查询和 Pipeline 生成。

## 实现方案

### 1. 修复 LLM 客户端调用

`template_dr.py` 中 `create_dr_pipeline()` 原先使用 `_get_llm_client()` 错误地以 `client, model` 解包方式调用，但集成中心的 AI 连接器返回单对象 `connector`：

**前：**
```python
client, model = _get_llm_client()
response = client.chat.completions.create(model=model, ...)
```

**后：**
```python
connector = _get_llm_client()
result = connector.chat(messages=messages, response_format={"type": "json_object"}, temperature=0.1)
```

### 2. DR 服务适配 Application 级

`dr_service.py:get_dr_group_topology()` 查询改为：

```cypher
MATCH (g:DrGroup {instance_id: $gid})
MATCH (g)<-[:PROTECTED_BY]-(a:Application)
OPTIONAL MATCH (a)-[:HAS_PROCESS]->(p:Process)
OPTIONAL MATCH (p)-[:RUNS_ON]->(h:Host)
RETURN a, collect(DISTINCT p) as processes, collect(DISTINCT h) as hosts
```

替代原 Process→BELONGS_TO→DrGroup 的查询方式。

### 3. Pipeline 生成节点

`neighbors_to_pipeline()` 使用 Application 的 `name` 作为 `service_name`，`host_ip` 作为 `target_host`：

```python
nodes.append({
    "id": nid,
    "label": f"关闭 {app_name} ({host_ip})",
    "node_type": "",
    "atom_type": "agent_process_stop",
    "params": {"service_name": app_name, "target_host": host_ip}
})
```

### 4. DR 拓扑预览

`preview_dr_topology()` 前端返回格式改为 Application 级：

```json
{
  "primary": [{"id": "...", "name": "monitor_service", "host": "192.168.1.60", "status": "running"}],
  "standby": [{"id": "...", "name": "monitor_service_cont", "host": "192.168.2.60", "status": "stopped"}],
  "calls": [{"from": "monitor_service(60)", "to": "monitor_service_cont(60)"}]
}
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/views/mixins/template_dr.py` | 修复 LLM 客户端调用 |
| `backend/opsflow/services/dr_service.py` | `get_dr_group_topology()` Application 级查询；`neighbors_to_pipeline()` 使用 Application 名 |

## 使用方式

1. DR 拓扑预览: `POST /api/opsflow/templates/preview_dr_topology/` 带 `dr_group_id`
2. DR Pipeline 生成: `POST /api/opsflow/templates/create_dr_pipeline/` 带 `dr_group_id`

### 关联文档

- 相关功能文档: [CMDB 层次重构](features/2026-06-17-application-model-hierarchy.md)
