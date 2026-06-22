# Aliyun ECS → CMDB 同步设计

> 日期: 2026-06-22
> 类型: 架构设计

---

## 背景

当前 CMDB 的 `:Host` 节点仅有 Agent 上报（test123 等物理机/虚拟机），阿里云 ECS 实例创建/删除/启停后不会自动更新 CMDB。Pipeline 执行完 `aliyun_ecs_create` 后，创建的实例在 CMDB 中不可见，也无法参与 CMDB 拓扑和 DR 容灾。

## 目标

1. **实时同步** — Pipeline 执行 ECS 操作原子后，立即更新 CMDB `:Host` 节点
2. **周期同步** — 定时任务每 30 分钟全量拉取阿里云 ECS 实例列表，保证 CMDB 数据一致性
3. **统一 Host 模型** — 云主机和 Agent 上报主机共享 `:Host` 标签，用 `cloud_instance_id` 区分来源

## 架构

```
Pipeline 执行 aliyun_ecs_create
  ↓
PluginService.execute() 成功
  ↓
atom_type.startswith("aliyun_")?
  ├─ 是 → cloud_sync.sync_ecs_instance(params, result)
  │         ├─ DescribeInstances 查最新状态
  │         └─ MERGE :Host {cloud_instance_id} → 更新/创建
  └─ 否 → 跳过

⏰ 定时任务（30min 周期）
  ├─ AliyunSync.fetch_assets() → DescribeInstances 分页
  ├─ _map_fields() → CMDB 字段映射
  └─ ImportService.import_instances("Host", data, "create_or_update")
```

## Host 模型扩展

给 `:Host` 节点新增字段：

| 属性 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `cloud_instance_id` | string | DescribeInstances.InstanceId | 阿里云实例 ID，MERGE 键 |
| `cloud_type` | string | 固定 `aliyun` | 云厂商标识 |
| `instance_type` | string | DescribeInstances.InstanceType | ECS 规格 |
| `ip` | string | VpcAttributes.PrivateIpAddress | 已有字段，云主机也填充 |
| `hostname` | string | HostName | 已有字段 |
| `region` | string | RegionId | 已有字段 |
| `status` | string | Status | running/stopped/deleted |
| `os_type` | string | 固定 `linux` | 已有字段 |
| `cpu_cores` | int | Cpu | 已有字段 |
| `memory_mb` | int | Memory * 1024 | 已有字段 |

MERGE 策略：优先 `cloud_instance_id` → fallback `ip`。

## 实时同步

### 触发点

`backend/opsflow/core/plugin_service_adapter.py` 第 117 行 `instance.execute()` 成功后追加：

```python
# 实时同步到 CMDB
try:
    from opsflow.core.cloud_sync import sync_after_execution
    sync_after_execution(atom_type, resolved_params, result, _execution_id)
except Exception:
    logger.exception("cloud sync failed")
```

### 各原子行为

| 原子 | 动作 |
|------|------|
| `aliyun_ecs_create` | DescribeInstances(InstanceId) → 创建 :Host |
| `aliyun_ecs_start` | 更新 :Host.status = running |
| `aliyun_ecs_stop` | 更新 :Host.status = stopped |
| `aliyun_ecs_restart` | 更新 :Host.status = running |
| `aliyun_ecs_modify` | 更新 :Host 属性 |
| `aliyun_ecs_delete` | 标记 :Host.status = deleted 或删除节点 |
| `aliyun_ecs_describe` | 跳过（纯查询） |
| `aliyun_ecs_create_image` | 跳过（不涉及 Host） |

### 核心函数

`cloud_sync.py` 中的 `sync_ecs_instance()`：

```python
def sync_ecs_instance(instance_id: str, region: str) -> dict:
    """查询 ECS 实例详情并同步到 CMDB Host 节点"""
    client = get_ecs_client(region)
    req = DescribeInstancesRequest()
    req.set_InstanceIds(f'["{instance_id}"]')
    resp = client.do_action_with_exception(req)
    data = json.loads(resp)
    inst = data["Instances"]["Instance"][0]

    props = {
        "cloud_instance_id": inst["InstanceId"],
        "cloud_type": "aliyun",
        "instance_type": inst.get("InstanceType", ""),
        "ip": _get_private_ip(inst),
        "hostname": inst.get("InstanceName", "") or inst.get("HostName", ""),
        "region": inst.get("RegionId", ""),
        "status": inst.get("Status", ""),
        "os_type": "linux",
        "cpu_cores": inst.get("Cpu", 0),
        "memory_mb": (inst.get("Memory", 0) or 0) * 1024,
    }

    with graph_driver.session() as session:
        session.run("""
            MERGE (h:Host {cloud_instance_id: $cid})
            ON CREATE SET h += $props, h.__created_at = toString(datetime()),
                          h.__model_code = 'Host'
            ON MATCH SET h += $props, h.__updated_at = toString(datetime())
        """, cid=instance_id, props=props)
```

## 周期全量同步

### 实现 AliyunSync.fetch_assets()

在 `cmdb/services/sync_service.py` 中实现：

```python
class AliyunSync(BaseCloudSync):
    def fetch_assets(self) -> list[dict]:
        from opsflow.plugins.aliyun_ecs._client import get_ecs_client
        client = get_ecs_client()  # 从 connector 配置读默认 region
        instances = []
        page = 1
        while True:
            req = DescribeInstancesRequest()
            req.set_PageSize(100)
            req.set_PageNumber(page)
            resp = client.do_action_with_exception(req)
            data = json.loads(resp)
            page_instances = data.get("Instances", {}).get("Instance", [])
            if not page_instances:
                break
            instances.extend(page_instances)
            page += 1
        return instances
```

### 注册定时任务

在 `opsflow/core/scheduler_service.py` 中加：

```python
def sync_aliyun_ecs():
    AliyunSync().sync()

# register_plan("CloudSync", "*/30 * * * *", sync_aliyun_ecs)
```

## 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/opsflow/core/plugin_service_adapter.py` | execute 成功后调 sync_after_execution() |
| 新增 `backend/opsflow/core/cloud_sync.py` | sync_after_execution() + sync_ecs_instance() |
| `backend/cmdb/services/sync_service.py` | 实现 AliyunSync.fetch_assets() 分页查询 |
| `backend/opsflow/core/scheduler_service.py` | 注册 30 分钟周期的 cloud sync 任务 |
| `backend/cmdb/management/commands/seed_dr_models.py` | Host 模型加 cloud_instance_id, cloud_type, instance_type 字段 |

## 验证方案

1. 创建 ECS Pipeline → 执行成功后查询 Neo4j：
   ```cypher
   MATCH (h:Host {cloud_instance_id: "i-xxx"}) RETURN h
   ```

2. 检查 :Host 节点包含 `cloud_type: "aliyun"`, `status`, `instance_type`

3. 手动触发周期同步：
   ```python
   from cmdb.services.sync_service import AliyunSync
   AliyunSync().sync()
   ```

4. 停止实例后重查状态：
   ```cypher
   MATCH (h:Host {cloud_instance_id: "i-xxx"}) RETURN h.status
   ```
