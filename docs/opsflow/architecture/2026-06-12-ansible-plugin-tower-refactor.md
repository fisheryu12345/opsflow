# Ansible 插件 Tower 执行后端重构 / Ansible Plugin Tower Backend Refactor

> 提交: (待提交) | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 重构

---

## 动机

原有架构存在两条并行的执行路径：
1. **插件路径**：`ShellPlugin.execute()` 用本地 `subprocess.run()` 执行
2. **Tower 路径**：`ansible_trigger.execute_atom()` 通过 Tower REST API 执行

两者共用同一套 atom_type 词汇表但代码完全独立，导致：
- 同一插件需要维护两套执行逻辑
- `core/tower/` 包游离于插件系统之外
- `core/ansible_trigger.py` 的 `_mock_execute()` 与真正的执行逻辑耦合

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `plugins/ansible/shell.py` | 继承 `BasePlugin`，本地 subprocess 执行 | 继承 `TowerBasePlugin`，Tower 远程执行 |
| `plugins/ansible/file_copy.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/script_exec.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/upload_file.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/nginx_reload.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/service_control.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/backup_file.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/java_deploy.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `plugins/ansible/docker_deploy.py` | 继承 `BasePlugin`，返回 delegation 占位 | 继承 `TowerBasePlugin`，Tower 调度 |
| `core/tower/` (6 文件) | 游离于插件系统之外 | **已删除**，迁移到 `plugins/ansible/tower_backend/` |
| `core/ansible_trigger.py` | 独立的 Tower 执行触发器 | **已删除**，逻辑合并到 `TowerBasePlugin` |
| `core/tower_service.py` | 重导出 shim | **已删除** |

### 代码对比

```python
# 重构前 — 本地 subprocess 执行
class ShellPlugin(BasePlugin):
    def execute(self, command, **kwargs):
        import subprocess, shlex
        result = subprocess.run(shlex.split(command), ...)
        return {"success": result.returncode == 0, "data": {"stdout": ...}}

# 重构后 — Tower 远程执行（异步轮询）
class ShellPlugin(TowerBasePlugin):
    # 继承 execute/schedule/rollback，只需定义 get_form_config()
    @classmethod
    def get_form_config(cls):
        return [...]  # 与重构前完全相同
```

```python
# 重构前 — 旧 Tower 执行路径（已删除）
def execute_atom(node, ...):
    tower = get_tower_service()
    launch_result = tower.launch_job(...)
    result = tower.poll_job(job_id, ...)  # 阻塞式轮询
    return {"stdout": ..., "stderr": ..., ...}

# 重构后 — Tower 执行整合到插件生命周期
class TowerBasePlugin(BasePlugin):
    _need_schedule = True
    def execute(self, **kwargs):
        tower = get_tower_service()
        result = tower.launch_job(extra_vars=...)
        return {"success": True, "data": {"tower_job_id": result["job_id"]}}
    def schedule(self, context, **kwargs):
        job_id = context.get("tower_job_id")
        status = tower.get_job_status(job_id)
        if status["status"] == "successful": return True
        elif ...: return False
        else: return None  # bamboo-engine 继续轮询
```

### 设计决策

- **`_need_schedule = True`**：利用 bamboo-engine 原生异步调度，`execute()` 只负责触发，`schedule()` 负责轮询
- **TowerBasePlugin 继承而非组合**：9 个插件只需改一行父类名，form_config 完全不变
- **包路径迁移**：`core/tower/` → `plugins/ansible/tower_backend/` 使 Tower 执行后端成为插件系统的一部分，不再独立

## 迁移说明

本次重构为纯代码迁移，不涉及数据迁移。旧 `core/tower/` 包已删除，所有 import 引用已清理。
