# Aliyun ECS 原子插件设计

> 日期: 2026-06-14 | 状态: 设计阶段
> 涉及 App: opsflow
> 类型: 功能新增

---

## 1. 背景

当前 opsflow 流程引擎已支持 ESXi、Redfish、NetApp 等多种基础设施原子，但缺少阿里云 ECS 的运维原子。用户无法在自动化流程中直接管理阿里云 ECS 实例的生命周期（启动、停止、创建、销毁等）。

集成中心已存在 `aliyun_ecs` 连接器定义和 `AliyunConnector` 适配器，但存在两个缺口：
1. **`AliyunConnector.get_client()` 缺少 Secret Key 传参** — 当前只传了 `AccessKey ID`，`Secret` 传空字符串
2. **无 opsflow 原子** — 流程画布中无任何阿里云 ECS 的可拖拽节点

## 2. 目标

**8 个原子 + 1 条依赖修复：**

| 原子 | code | risk_level | 描述 |
|------|------|------------|------|
| 查询实例 | `aliyun_ecs_describe` | low | 查询 ECS 实例详情 |
| 启动实例 | `aliyun_ecs_start` | medium | StartInstance |
| 停止实例 | `aliyun_ecs_stop` | medium | StopInstance（可选强制） |
| 重启实例 | `aliyun_ecs_restart` | medium | RebootInstance |
| 创建实例 | `aliyun_ecs_create` | high | CreateInstance + 可选分配公网 IP |
| 释放实例 | `aliyun_ecs_delete` | high | DeleteInstance |
| 创建镜像 | `aliyun_ecs_create_image` | medium | CreateImage |
| 修改属性 | `aliyun_ecs_modify` | medium | ModifyInstanceAttribute |

**前置修复：** `AliyunConnector` 凭证传递修复 + 新增 `aliyun-python-sdk-ecs` 依赖

---

## 3. 架构方案

### 3.1 凭证设计：两条 Credential 记录

集成中心的 `ConnectorInstance` 通过 `credentials` 关联多条 `ConnectorCredential`，每条有一个 `cred_type` 字段。

对于阿里云 AK/SK，拆为**两条记录**（而不是冒号分隔合存在一条）：

| cred_type | name | encrypted_value |
|-----------|------|-----------------|
| `access_key` | `access_key_id` | 加密后的 AccessKey ID |
| `access_key` | `access_key_secret` | 加密后的 AccessKey Secret |

**对应 `_client.py` 的获取逻辑：**

```python
def get_ecs_client(region="cn-hangzhou"):
    """获取阿里云 ECS SDK 客户端"""
    from aliyunsdkcore.client import AcsClient
    from integration.models.connector import ConnectorDefinition, ConnectorInstance
    from integration.services.credential_service import decrypt_credential

    # 查找 aliyun_ecs 连接器实例（取第一个启用的）
    try:
        aliyun_def = ConnectorDefinition.objects.get(code="aliyun_ecs")
        instance = aliyun_def.instances.filter(is_active=True).first()
        if not instance:
            raise ValueError("未找到启用的阿里云连接器实例")
    except ConnectorDefinition.DoesNotExist:
        raise ValueError("未找到 aliyun_ecs 连接器定义，请先执行 seed_reference")

    # 读取两条 credential 记录
    creds = {c.name: decrypt_credential(c.encrypted_value) for c in instance.credentials.all()}
    ak = creds.get("access_key_id", "")
    sk = creds.get("access_key_secret", "")
    if not ak or not sk:
        raise ValueError("阿里云连接器未配置完整的 AccessKey (access_key_id + access_key_secret)")

    return AcsClient(ak, sk, region)
```

**同时修复 `AliyunConnector.get_client()`（`backend/integration/adapters/cloud/aliyun.py`）：**

```python
def get_client(self):
    """获取阿里云 SDK 客户端（自动读取 sk 记录）"""
    from integration.services.credential_service import decrypt_credential
    creds = {c.name: decrypt_credential(c.encrypted_value) for c in self.instance.credentials.all()}
    ak = creds.get("access_key_id", "")
    sk = creds.get("access_key_secret", "")
    region = self.config.get("region", "cn-hangzhou")
    return self._make_client(ak, sk, region)
```

### 3.2 _client.py 统一工厂

所有 ECS 原子不直接操作凭证，统一通过 `aliyun_ecs/_client.py` 获取 `AcsClient`：

```python
# backend/opsflow/plugins/aliyun_ecs/_client.py
"""阿里云 ECS SDK 客户端工厂"""

def get_ecs_client(region: str = "cn-hangzhou"):
    """返回 AcsClient，从集成中心读取 AK/SK（支持即时降级到 mock）"""
    try:
        from aliyunsdkcore.client import AcsClient
    except ImportError:
        raise ImportError("请安装 aliyun-python-sdk-core 和 aliyun-python-sdk-ecs")
    # ... 上述凭证读取逻辑 ...


class EcsClientFactory:
    """带缓存的工厂，避免每次执行都查询数据库"""
    _client_cache = {}
    # ...
```

**降级策略：** 如果没有配置阿里云连接器，原子不报错崩溃，而是返回清晰的错误提示"请先在集成中心配置阿里云 ECS 连接器"。

### 3.3 新增依赖

```python
# requirements.txt
aliyun-python-sdk-core>=2.13.0
aliyun-python-sdk-ecs>=4.23.0
```

---

## 4. 原子详细设计

### 4.1 通用模式

每个原子遵循 `BasePlugin` 标准模式：

```python
class AliyunEcsXxxPlugin(BasePlugin):
    name = "xxx"
    name_en = "Xxx"
    code = "aliyun_ecs_xxx"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "xxx"
    description_en = "Xxx an Alibaba Cloud ECS instance"
    risk_level = "low|medium|high"

    @classmethod
    def get_form_config(cls): ...

    def execute(self, **kwargs) -> dict: ...

    @classmethod
    def get_output_schema(cls):
        return [{"name": "instance_id", ...}, {"name": "status", ...}]
```

### 4.2 查询实例 — `describe_instance.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 实例 ID，必填 |
| `region` | input | 地域，默认 cn-hangzhou |

**输出：** `instance_id`, `status`, `instance_name`, `private_ip`, `public_ip`, `os_name`, `instance_type`, `creation_time`

**SDK 调用：** `DescribeInstancesRequest`

### 4.3 启动实例 — `start_instance.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 实例 ID，必填 |
| `region` | input | 地域，默认 cn-hangzhou |

**输出：** `instance_id`, `status`

**SDK 调用：** `StartInstanceRequest`
**Rollback：** 调用 `StopInstance`

### 4.4 停止实例 — `stop_instance.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 实例 ID，必填 |
| `region` | input | 地域 |
| `force_stop` | switch | 是否强制停止，默认 false |

**输出：** `instance_id`, `status`

**SDK 调用：** `StopInstanceRequest`
**Rollback：** 调用 `StartInstance`

### 4.5 重启实例 — `restart_instance.py`

**表单：** instance_id + region（同启动）

**SDK 调用：** `RebootInstanceRequest`
**Rollback：** 无（重启本身就是一次性操作）

### 4.6 创建实例 — `create_instance.py`

**表单（FormGroup 分区）：**

```
┌─ 基础配置 (FormGroup: "基础配置") ──────┐
│  instance_name | region                  │
│  image_id      | instance_type           │
│  zone_id                                │
└─────────────────────────────────────────┘
┌─ 网络配置 (FormGroup: "网络配置") ──────┐
│  security_group_id | vswitch_id         │
│  internet_max_bandwidth_out (int 默认0)  │
│  allocate_public_ip (switch 默认 true)   │
└─────────────────────────────────────────┘
┌─ 存储配置 (FormGroup: "存储配置") ──────┐
│  system_disk_size (int 默认40)           │
│  system_disk_category (select)           │
└─────────────────────────────────────────┘
```

**SDK 调用：** `CreateInstanceRequest` + `AllocatePublicIpAddressRequest`（如选择分配公网 IP）

**输出：** `instance_id`, `private_ip`, `public_ip`

**Rollback：** 调用 `DeleteInstance`（仅在创建成功后 5 分钟内的 rollback 有效）

**风险控制：** `risk_level = "high"`，且默认购买数量 `amount = 1`（不允许批量创建）

### 4.7 释放实例 — `delete_instance.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 实例 ID，必填 |
| `region` | input | 地域 |
| `force` | switch | 是否强制释放，默认 false |

**SDK 调用：** `DeleteInstanceRequest`

**输出：** `instance_id`, `status: "deleted"`

### 4.8 创建镜像 — `create_image.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 源实例 ID，必填 |
| `image_name` | input | 镜像名称，必填 |
| `description` | textarea | 描述，可选 |
| `region` | input | 地域 |

**SDK 调用：** `CreateImageRequest`

**输出：** `image_id`, `image_name`

### 4.9 修改属性 — `modify_instance.py`

**表单：**
| tag_code | type | 说明 |
|----------|------|------|
| `instance_id` | input | 实例 ID，必填 |
| `instance_name` | input | 新名称（可选） |
| `description` | textarea | 新描述（可选） |
| `region` | input | 地域 |

**SDK 调用：** `ModifyInstanceAttributeRequest`

**输出：** `instance_id`, `instance_name`

---

## 5. 目录结构

```python
backend/opsflow/plugins/aliyun_ecs/
    __init__.py              # __group_name__ = "阿里云 ECS"
    _client.py               # 共享 EcsClientFactory
    describe_instance.py     # 查询实例
    start_instance.py        # 启动实例
    stop_instance.py         # 停止实例
    restart_instance.py      # 重启实例
    create_instance.py       # 创建实例
    delete_instance.py       # 释放实例
    create_image.py          # 创建镜像
    modify_instance.py       # 修改属性
```

## 6. 修复文件

| 文件 | 改动 |
|------|------|
| `backend/integration/adapters/cloud/aliyun.py` | `get_client()` 改为读取两条 credential 记录，传入完整 ak+sk |
| `backend/requirements.txt` | 新增 `aliyun-python-sdk-core` + `aliyun-python-sdk-ecs` |

## 7. 测试策略

- 每个原子独立单测：mock `EcsClientFactory` 返回 mock AcsClient
- 覆盖 execute 成功分支和异常分支（连接超时、鉴权失败、实例不存在等）
- 覆盖 rollback 逻辑
- 集成测试需真实阿里云 AK/SK（非必选，留空则跳过）

## 8. 部署注意事项

1. `pip install aliyun-python-sdk-core aliyun-python-sdk-ecs`
2. 在集成中心配置 `aliyun_ecs` 连接器（需执行 `bootstrap` 或 `seed_reference` 建立连接器定义）
3. 添加两条 credential：`access_key_id` + `access_key_secret`
4. 执行 `python manage.py scan_plugins` 热加载新原子
5. 刷新页面，画布插件面板中出现"阿里云 ECS"分组
