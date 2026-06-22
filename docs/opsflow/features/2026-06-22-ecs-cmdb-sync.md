# Aliyun ECS → CMDB 实时与周期同步

> 提交: b4ce0afd | 日期: 2026-06-22
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

Pipeline 执行 aliyun_ecs_create/delete/start/stop 后，创建的 ECS 实例在 CMDB 中不可见。需要自动同步到 CMDB `:Host` 节点，使云主机可参与 CMDB 拓扑和 DR 容灾。

## 实现方案

### 架构

```
Pipeline 执行 aliyun_ecs_create
  ↓
PluginService.execute() 成功
  ↓
atom_type 以 "aliyun_" 开头?
  ├─ 是 → cloud_sync.sync_after_execution()
  │         ├─ DescribeInstances(InstanceId) 查最新状态
  │         └─ MERGE :Host {cloud_instance_id} 到 Neo4j
  └─ 否 → 跳过

⏰ APScheduler 定时任务（30min）
  ├─ AliyunSync.fetch_assets() → DescribeRegions 发现全地域
  ├─ 逐个地域 DescribeInstances 分页查询
  ├─ _map_fields() → CMDB 字段映射
  └─ ImportService.import_instances("Host", data, "create_or_update")
```

### 关键代码

#### 实时同步 — `cloud_sync.py`

```python
def sync_after_execution(atom_type, params, result, execution_id=None):
    if atom_type not in SYNC_ACTIONS:
        return
    action, needs_id = SYNC_ACTIONS[atom_type]
    if not needs_id or not result.get('success'):
        return
    instance_id = result.get('data', {}).get('instance_id', '') or params.get('instance_id', '')
    region = params.get('region', '')
    sync_ecs_instance(instance_id, region, action)
```

`SYNC_ACTIONS` 定义每个原子是否需要同步：

```python
SYNC_ACTIONS = {
    'aliyun_ecs_create': ('create', True),
    'aliyun_ecs_start': ('start', True),
    'aliyun_ecs_stop': ('stop', True),
    'aliyun_ecs_restart': ('restart', True),
    'aliyun_ecs_modify': ('modify', True),
    'aliyun_ecs_delete': ('delete', True),
    'aliyun_ecs_describe': ('describe', False),     # 跳过
    'aliyun_ecs_create_image': ('create_image', False),  # 跳过
}
```

sync_ecs_instance() 核心函数：

```python
def sync_ecs_instance(instance_id, region, action='create'):
    with graph_driver.session() as session:
        session.run("""
            MERGE (h:Host {cloud_instance_id: $cid})
            ON CREATE SET h += $props, h.__created_at = toString(datetime()),
                          h.__model_code = 'Host'
            ON MATCH SET h += $props, h.__updated_at = toString(datetime())
        """, cid=instance_id, props=props)
```

#### 全地域同步 — `sync_service.py`

```python
class AliyunSync(BaseCloudSync):
    def fetch_assets(self):
        # 用任意 region 获取全地域列表
        region = 'cn-hangzhou'
        client = get_ecs_client(region)
        regions_req = DescribeRegionsRequest()
        all_regions = client.do_action_with_exception(regions_req)  # 返回 31 个地域

        # 逐个地域循环
        instances = []
        for reg in all_regions:
            reg_client = get_ecs_client(reg)
            while True:
                req = DescribeInstancesRequest()
                req.set_PageSize(100)
                # ... 分页逻辑
```

#### 触发 hook — `plugin_service_adapter.py`

execute() 成功后自动调用：

```python
# ── 实时同步到 CMDB ──
if success and atom_type and atom_type.startswith('aliyun_'):
    from opsflow.core.cloud_sync import sync_after_execution
    sync_after_execution(atom_type, inputs_dict, result, _execution_id)
```

#### 8 个原子统一改造

所有原子改为：
- `region`: `str = ""`（无默认值），表单用 `async_select` 从 describe-regions API 加载
- `instance_id`（操作类原子）：用 `async_select` 从 CMDB 查询 `:Host {cloud_type: 'aliyun'}` 列表
- `region` 自动从 CMDB `:Host` 节点获取
- 强制选项（force_stop/force_reboot/force）改为 `type="switch"`

```python
from opsflow.plugins.aliyun_ecs._client import get_ecs_client, resolve_cmdb_region

def execute(self, instance_id: str, region: str = "", force: bool = False, **kwargs) -> dict:
    if not region:
        region = resolve_cmdb_region(instance_id)  # 从 Neo4j 查 region
```

#### 前端 TagSwitch 组件

新增 `TagSwitch.vue`，解决 `type="switch"` 在 TAG_MAP 中未注册的问题：

```vue
<el-switch
  :model-value="!!localVal"
  :active-text="activeText"
  :inactive-text="inactiveText"
  @update:model-value="onChange"
/>
```

Props 使用 `active_text` / `inactive_text`（下划线，匹配后端 attrs）。

#### 前端 TagSlider 组件

新增 `TagSlider.vue`，支持自定义标签：

```vue
<el-slider v-model="sliderVal" :min="min" :max="max" :step="1" />
<span>{{ label }}</span>
<!-- label-0: "无公网", label-1: "强制释放", label-n: "{value} Mbps" -->
```

#### formData 传递修复

`FormGroup.vue` 和 `RenderForm.vue` 中 FormItem 缺失 `:form-data="formData"`，导致 async_select 的 `depends_on` 机制无法读取联动字段的值。修复后级联下拉正常工作。

### 数据流

```
创建 ECS Pipeline → aliyun_ecs_create 执行
  → PluginService.execute() 成功
  → cloud_sync.sync_ecs_instance()
  → MERGE :Host {cloud_instance_id, cloud_type: "aliyun", ...}
  → CMDB 可见

CMDB 选择实例 → describe_cmdb_instances API
  → MATCH (h:Host {cloud_type: "aliyun"})
  → 返回 [{label: "hostname (ip, status)", value: "i-xxx"}, ...]

周期同步每 30 分钟
  → DescribeRegions → 全部 31 个地域
  → 每个地域 DescribeInstances 分页
  → ImportService.import_instances() → MERGE :Host
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 全地域同步 | DescribeRegions 自动发现 | 无需配置多个连接器 |
| 实例 ID 来源 | CMDB（操作时）/ 阿里云（创建时） | 操作原子从 CMDB 下拉，创建时从阿里云返回 |
| region 获取 | 操作原子从 CMDB 自动获取 | 用户不需单独选 region |
| 强制选项 | switch 而非 slider | 二值选项，switch 语义更清晰 |
| 定时任务 | 模块级函数而非闭包 | 闭包不可序列化，APScheduler 报错 |
| ImportService 系统字段 | 手动保留 instance_id | 验证器会过滤掉模型定义中不存在的字段 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/cloud_sync.py` | 实时同步核心函数，新增 |
| `backend/opsflow/core/plugin_service_adapter.py` | execute hook 调用 cloud_sync |
| `backend/opsflow/core/scheduler_service.py` | 30 分钟周期同步注册 |
| `backend/cmdb/services/sync_service.py` | AliyunSync 全地域分页 |
| `backend/cmdb/services/import_service.py` | 系统字段保留 + instance_id 自动生成 |
| `backend/opsflow/plugins/aliyun_ecs/_client.py` | resolve_cmdb_region() 工具函数 |
| `backend/opsflow/plugins/aliyun_ecs/*.py` | 8 个原子统一改造（async_select + switch） |
| `backend/opsflow/views/aliyun_views.py` | describe_cmdb_instances API |
| `web/src/components/RenderForm/tags/TagSwitch.vue` | switch 类型组件（新增） |
| `web/src/components/RenderForm/tags/TagSlider.vue` | 滑块组件（新增） |
| `web/src/components/RenderForm/FormGroup.vue` | formData 传递修复 |
| `web/src/components/RenderForm/FormItem.vue` | TAG_MAP 注册 TagSwitch |

## 使用方式

1. 周期同步自动运行（每 30 分钟）
2. 手动触发: `AliyunSync().sync()`
3. 操作原子：从 CMDB 下拉选择实例，region 自动获取
4. 创建实例成功后自动同步到 CMDB

### 关联文档

- 相关架构文档: [design](docs/superpowers/specs/2026-06-22-ecs-cmdb-sync-design.md)
- 相关功能文档: [Application 模型层次重构](../cmdb/features/2026-06-17-application-model-hierarchy.md)

---

## 2026-06-23 Update

> 提交: 97397ecb

### 变更内容

新增 **Cloud Asset Sync 管理页面**，统一的云厂商同步状态查看与手动触发入口：

1. **CloudSyncLog 模型** — 持久化同步日志，记录每次同步的 provider/status/started_at/finished_at/total/errors/triggered_by
2. **云同步 API 视图** — 4 个端点：列出厂商、同步状态、触发同步、同步历史
3. **卡死记录自动检测** — 同步超过 15 分钟仍为 running 时自动重置为 failed（防止进程重启后永久卡死）
4. **BaseCloudSync 重构** — `sync()` 方法自动写入 CloudSyncLog，包含 try/except 兜底
5. **前端云同步组件** — 集成中心新增「云同步」标签页，包含厂商状态卡片（配置/状态/上次同步时间/手动同步按钮）+ 操作工具栏（全量同步/刷新）+ 同步历史表格
6. **前端数据路径修复** — 适配 axios interceptor 解包结构，`res?.data?.data` → `res?.data`

### 原因

之前云同步只有后端无界面，用户无法查看同步状态、触发同步或排查错误。新增管理页面使同步过程可观测、可操作。
