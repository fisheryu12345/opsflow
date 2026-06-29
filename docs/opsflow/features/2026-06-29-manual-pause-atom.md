# 手动暂停原子 (Manual Pause)

> 提交: 13c0882d | 日期: 2026-06-29
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

Pipeline 执行过程中需要在特定节点暂停，让运维人员人工确认或等待窗口期后再继续。之前的做法只能靠"审批原子"变通（暂停后需要 Approve/Reject，语义不符）。需要一个新的原子：执行到此处就暂停，用户点击 Resume 继续，不涉及任何审批决策。

## 实现方案

### 核心架构

执行链：`ManualPausePlugin.execute() → 返回成功 → PluginService 拦截 manual_pause → FlowEngine.pause()` → 暂停 → 用户点击 Resume → 引擎继续

### 关键代码

#### ManualPausePlugin — 通用插件

`opsflow/plugins/common/manual_pause.py`

```python
class ManualPausePlugin(BasePlugin):
    code = "manual_pause"
    group = "通用工具"
    icon = "VideoPause"
    color = "#909399"

    def execute(self, **kwargs):
        return {"success": True, "data": {"paused": True}}

    @classmethod
    def get_form_config(cls):
        return []  # 零参数
```

纯标记插件，`execute()` 立即返回成功。

#### Pipeline Builder 注册

`opsflow/core/pipeline_builder/elements.py:213-218`

```python
if node_type == 'manual_pause':
    act = ServiceActivity(component_code="opsflow_plugin",
                          skippable=False, retryable=False, id=nid)
    act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='manual_pause')
```

与审批节点同样设置 `skippable=False, retryable=False`，确保只能通过 Resume 继续。

#### PluginService 中直接暂停（核心逻辑）

`opsflow/core/plugin_service_adapter.py:78-91`

```python
if atom_type == 'manual_pause':
    from opsflow.core.flow_engine import FlowEngine
    from opsflow.models import FlowExecution
    try:
        execution = FlowExecution.objects.get(id=_execution_id)
        execution.context['_pause_reason'] = 'manual_pause'
        execution.save(update_fields=['context'])
        FlowEngine(execution).pause()
        logger.info("[ManualPause] Node paused execution %s", _execution_id)
    except Exception:
        logger.exception("[ManualPause] pause failed")
    data.outputs['_result'] = True
    return True
```

选择在 `PluginService.execute()` 中直接暂停而不是走信号，因为引擎对成功的 `ServiceActivity` 会跳过 FINISHED 信号发射（`skip dispatch(node_finish)`），走信号无法触发 pause。

#### 前端 ExecutionDetail banner

`web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue`

新增 `isManualPause` computed，读取 `context._pause_reason` 判断是否手动暂停。显示蓝色提示 banner（无按钮，复用顶部 Resume 按钮）。

### 数据流

```
用户编排 Pipeline → 拖入 manual_pause 原子 → 执行
  → bamboo-engine 执行 ServiceActivity(opsflow_plugin, _atom_type=manual_pause)
  → PluginService.execute() 检测到 manual_pause
  → FlowExecution.objects.get() 获取当前执行
  → 写入 context._pause_reason = 'manual_pause'
  → FlowEngine(execution).pause()
  → bamboo-engine pause_pipeline → pipeline 状态 SUSPENDED
  → 前端轮询发现 status='paused' + pause_reason='manual_pause'
  → 显示蓝色 banner "已暂停于手动暂停节点"
  → 用户点击 Resume 按钮
  → FlowEngine(execution).resume() → 继续执行
```

### 设计决策

- **为什么不在信号处理器中触发暂停？** 引擎对 `ServiceActivity.execute()` 返回 `True` 的成功节点不发射 FINISHED 信号（`skip dispatch(node_finish)`），走信号链路 pause 永远不会触发。
- **为什么 skippable=False？** 暂停节点不允许被跳过，skip 会破坏流程语义。
- **为什么复用已有 Resume 按钮？** Resume 按钮已存在于 ExecutionDetail 顶部（`status === 'paused'` 时启用），不需要新增 UI 元素，只需区分提示文案。

### 关联文档

- 设计规范: [manual-pause-atom-design](docs/superpowers/specs/2026-06-28-manual-pause-atom-design.md)

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/plugins/common/manual_pause.py` | ManualPausePlugin 原子定义 |
| `backend/opsflow/core/pipeline_builder/elements.py` | 注册 `manual_pause` 节点类型 |
| `backend/opsflow/core/plugin_service_adapter.py` | PluginService.execute() 中直接触发 pause |
| `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 手动暂停 banner + context._pause_reason 检测 |
| `web/src/i18n/pages/opsflow/en.ts` | 英文文案 |
| `web/src/i18n/pages/opsflow/zh-cn.ts` | 中文文案 |
| `backend/opsflow/tests/test_manual_pause.py` | 5 个测试用例 |

## 使用方式

1. 在 Pipeline 设计器中，从「通用工具」分组拖入 `manual_pause` 原子
2. 零参数配置，直接保存
3. 执行流程，到达 manual_pause 后自动暂停
4. 在 ExecutionDetail 页面看到蓝色提示条
5. 点击顶部 Resume 按钮继续执行
