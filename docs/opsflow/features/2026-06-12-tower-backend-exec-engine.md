# Tower 后端执行引擎 / Tower Backend Execution Engine

> 提交: df82a1c9 | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

Ansible 插件（shell、file_copy、docker_deploy 等）原有的 `execute()` 方法使用本地 `subprocess.run()` 执行，无法利用 Ansible Tower/AWX 的作业调度、主机管理、权限管控和审计能力。同时 `core/tower/` + `core/ansible_trigger.py` 独立于插件系统之外，存在双执行路径的问题。

## 实现方案

### 核心架构

新增 `TowerBasePlugin(BasePlugin)` 基类 + `tower_backend/` 后端包，将 Tower REST API 执行能力整合到标准插件生命周期中：

```
ansible 插件 (ShellPlugin 等)
    │ 继承 TowerBasePlugin
    ▼
TowerBasePlugin
    ├─ execute() → TowerService.launch_job() → 返回 job_id
    ├─ schedule() → TowerService.get_job_status() → 轮询直到完成
    ├─ rollback() → TowerService.cancel_job() → 取消作业
    └─ _mock_execute() → Tower 未配置时降级
        │
        ▼
    TowerService (继承自 3 个 Mixin)
        ├─ TowerClientMixin  — HTTP 客户端 (Session/重试/认证)
        ├─ TowerJobMixin     — 作业生命周期 (launch/status/cancel/artifacts)
        └─ TowerPollingMixin — 自适应轮询 + WebSocket 推送
```

### 关键代码

**TowerBasePlugin** (`plugins/ansible/tower_backend/base_plugin.py`):

```python
class TowerBasePlugin(BasePlugin):
    _need_schedule = True  # 异步调度模式

    def execute(self, **kwargs) -> dict:
        """Step 1: 通过 Tower REST API 启动作业"""
        tower = get_tower_service()
        if not tower.is_configured():
            return self._mock_execute(**kwargs)  # 开发模式降级

        extra_vars = build_extra_vars(atom_type=self.code, params=kwargs)
        launch_result = tower.launch_job(extra_vars=extra_vars)
        return {
            "success": True,
            "data": {
                "tower_job_id": launch_result["job_id"],
                "tower_status": "pending",
            },
        }

    def schedule(self, context: dict, **kwargs) -> bool | None:
        """Step 2: 轮询 Tower 作业状态"""
        tower_job_id = context.get("tower_job_id")
        status_info = tower.get_job_status(tower_job_id)
        if status_info["status"] == "successful":
            return True   # 完成
        elif status_info["status"] in ("failed", "error", "canceled"):
            return False  # 失败
        else:
            return None   # 继续等待
```

**自适应轮询** (`plugins/ansible/tower_backend/polling.py`):

```python
ADAPTIVE_POLL_SCHEDULE = [
    (30, 3),        # 前 30 秒：每 3 秒
    (300, 5),       # 30秒~5分钟：每 5 秒
    (1800, 10),     # 5分钟~30分钟：每 10 秒
    (float("inf"), 30),  # 超过 30 分钟：每 30 秒
]
```

### 设计决策

1. **`_need_schedule = True`**：bamboo-engine 原生支持异步调度模式，`execute()` 返回后自动定期调用 `schedule()`，无需自定义轮询线程
2. **Mixin 继承**：TowerService 使用 `TowerClientMixin + TowerJobMixin + TowerPollingMixin` 多继承，职责分离、可测试
3. **Tower 未配置降级**：不配置 `ANSIBLE_API_URL` 时自动返回 mock 结果，开发/演示不依赖 Tower
4. **包迁移**：`core/tower/` → `plugins/ansible/tower_backend/`，让 Tower 执行后端作为插件系统的一部分

### 数据流

```
用户创建 pipeline → ShellPlugin 节点
    → PluginService.execute() 路由到 ShellPlugin
    → ShellPlugin (继承 TowerBasePlugin).execute()
    → TowerService.launch_job(extra_vars={opsflow_atom_type: "shell", command: "..."})
    → POST /api/v2/job_templates/{id}/launch/ → job_id
    → bamboo-engine 调用 schedule()
    → TowerService.get_job_status(job_id) → 自适应轮询
    → 作业完成 → 结果写入 data.outputs
    → 下一节点执行
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `plugins/ansible/tower_backend/__init__.py` | TowerService + get_tower_service() 单例 |
| `plugins/ansible/tower_backend/base_plugin.py` | TowerBasePlugin 异步调度基类 |
| `plugins/ansible/tower_backend/client.py` | HTTP 客户端层 |
| `plugins/ansible/tower_backend/job.py` | 作业生命周期管理 |
| `plugins/ansible/tower_backend/polling.py` | 自适应轮询 + WebSocket 推送 |
| `plugins/ansible/tower_backend/base.py` | 常量、异常定义 |

## 使用方式

1. 配置环境变量 `ANSIBLE_API_URL`、`ANSIBLE_API_TOKEN`、`ANSIBLE_TEMPLATE_ID`
2. 添加 ansible 插件节点（shell、file_copy 等），配置参数
3. 执行 pipeline，节点自动通过 Tower REST API 远程执行
4. 未配置 Tower 时自动降级为本地 mock 执行
