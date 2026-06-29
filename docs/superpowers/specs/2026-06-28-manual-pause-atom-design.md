# Manual Pause Atom — 手动暂停原子设计规范

> 版本: 1.0 | 日期: 2026-06-28 | 状态: 已批准

---

## 1. 概述

在 OPSflow Pipeline 中新增一个原子节点 "手动暂停"（Manual Pause），当流程执行到该节点时自动暂停，等待用户在 ExecutionDetail 页面点击 Resume 按钮后继续执行。

### 目标

- Pipeline 设计器拖拽即可使用，零参数配置
- 原子执行完成即暂停 pipeline（复用 FlowEngine.pause() 机制）
- 前端统一用现有 Resume 按钮恢复（无需新增 UI 元素）
- 与审批暂停（approval）共存互不干扰

### 非目标

- 不引入自动唤醒/定时恢复
- 不涉及灰度发布或版本管理

---

## 2. 架构

### 2.1 执行流

```
Pipeline 执行到 manual_pause 节点
  → bamboo-engine 执行 opsflow_plugin 组件
  → ManualPausePlugin.execute() 立即返回 {success: true}
  → post_set_state 信号 FINISHED
  → 信号处理器检测到 _atom_type == 'manual_pause'
  → 写入 context._pause_reason = 'manual_pause'
  → 调用 FlowEngine(execution).pause()
  → pipeline 暂停，execution.status = 'paused'
  → 前端实时显示暂停状态 + 提示 "流程已暂停"
  → 用户点击 Resume 按钮
  → FlowEngine(execution).resume()
  → pipeline 继续执行后续节点
```

### 2.2 组件关系

```
ManualPausePlugin (plugins/common/manual_pause.py)
  │
  ├── execute() — 立即返回，无副作用
  │
  └── (信号链)
       signals/helpers.py::_is_manual_pause_node()
       signals/trace.py::_record_node_trace()  → 触发 pause
       core/flow_engine.py::FlowEngine.pause() → api.pause_pipeline()

前端 ExecutionDetail.vue
  ├── status === 'paused' → Resume 按钮（已有，无需新增）
  ├── pause_reason === 'manual_pause' → 显示手动暂停提示文案
  └── pause_reason !== 'manual_pause' → 保持现有审批/暂停提示
```

---

## 3. 详细设计

### 3.1 后端 — ManualPausePlugin

**文件:** `backend/opsflow/plugins/common/manual_pause.py`

```python
class ManualPausePlugin(BasePlugin):
    name = "手动暂停"
    name_en = "Manual Pause"
    code = "manual_pause"
    group = "通用工具"
    description = "暂停流程执行，等待用户手动恢复"
    description_en = "Pause pipeline execution and wait for manual resume"
    risk_level = "low"
    icon = "VideoPause"
    color = "#909399"

    def execute(self, **kwargs):
        """立即返回成功，暂停由信号处理器触发"""
        return {"success": True, "data": {"paused": True}}

    @classmethod
    def get_form_config(cls):
        return []  # 无参数，零配置
```

**注意:** 不定义 `get_var_types()`，所有参数按默认 `PLAIN` 处理。

### 3.2 后端 — Pipeline Builder 注册

**文件:** `backend/opsflow/core/pipeline_builder/elements.py`

在 `_create_element()` 的节点类型分支中新增 `manual_pause`：

```python
if node_type == 'manual_pause':
    act = ServiceActivity(
        component_code="opsflow_plugin",
        skippable=False, retryable=False, id=nid,
    )
    act.name = nid
    act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='manual_pause')
    return act
```

与 approval 节点相同：`skippable=False, retryable=False` 确保只能通过 Resume 继续。

### 3.3 后端 — 信号处理器检测暂停原因

**文件:** `backend/opsflow/signals/helpers.py`

新增检测函数：

```python
def _is_manual_pause_node(runtime, node_id) -> bool:
    """检测节点是否手动暂停节点"""
    try:
        inputs = pipeline_api.get_execution_data_inputs(runtime, node_id)
        return inputs.get('_atom_type', {}).get('value') == 'manual_pause'
    except Exception:
        return False
```

复用与 `_is_approval_node()` 相同的模式（`helpers.py:52-63`）。

**文件:** `backend/opsflow/signals/trace.py`

在 `_record_node_trace()` 的 FINISHED 分支中，在 approval 暂停判断之后插入：

```python
if to_state == states.FINISHED:
    # 审批节点暂停
    if _is_approval_node(runtime, node_id):
        execution.context['_approval_pending'] = node_id
        execution.save(update_fields=['context'])
        FlowEngine(execution).pause()
        return
    # ── 手动暂停节点暂停 ──
    if _is_manual_pause_node(runtime, node_id):
        execution.context['_pause_reason'] = 'manual_pause'
        execution.save(update_fields=['context'])
        FlowEngine(execution).pause()
        return
```

**关键设计决策:** 使用 `context['_pause_reason'] = 'manual_pause'` 标记暂停原因，而非新增模型字段。原因：这是短暂的状态标记，resume 后不再需要，保持模型简洁。

### 3.4 前端 — ExecutionDetail.vue

**文件:** `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue`

**改动 1:** 新增读取 pause_reason 的计算属性（引号内为 i18n key 的默认值）：

```typescript
const pauseReason = computed(() => execDetail.value.context?._pause_reason || '')

const isManualPause = computed(() => 
  execDetail.value.status === 'paused' && pauseReason.value === 'manual_pause'
)
```

**改动 2:** 暂停状态提示（在 approval-banner 下方或替代位置）：

```html
<div v-if="isManualPause" class="manual-pause-banner">
  <el-alert type="info" :closable="false" show-icon>
    <template #title>
      <span>流程已暂停于「手动暂停」节点，点击</span>
      <el-button size="small" @click="onResume" :loading="resuming">Resume</el-button>
      <span>继续执行</span>
    </template>
  </el-alert>
</div>
```

**改动 3:** 调整审批 banner 条件为 `isPendingApproval && !isManualPause`（防止审批 banner 在手动暂停时误显示）：

```typescript
const showApprovalBanner = computed(() => 
  isPendingApproval.value && pauseReason.value !== 'manual_pause'
)
```

**改动 4:** 从 execution detail API 响应中获取 context：

确认 `GET /api/opsflow/executions/{id}/` 的 serializer 包含 `context` 字段。如不包含，在 `ExecutionSerializer` 的 fields 中添加 `context`。

### 3.5 前端 — 中英文文案

**文件:** `web/src/i18n/pages/opsflow/en.ts` / `zh-cn.ts`

| Key | 英文 | 中文 |
|-----|------|------|
| `manualPause.title` | Paused at Manual Pause node | 已暂停于手动暂停节点 |
| `manualPause.description` | Click Resume to continue | 点击 Resume 按钮继续执行 |

---

## 4. 文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/opsflow/plugins/common/manual_pause.py` | **新建** | ManualPausePlugin |
| `backend/opsflow/core/pipeline_builder/elements.py` | 修改 | 注册 `manual_pause` 节点类型 |
| `backend/opsflow/signals/helpers.py` | 修改 | 新增 `_is_manual_pause_node()` |
| `backend/opsflow/signals/trace.py` | 修改 | FINISHED 分支插入 manual_pause 暂停 |
| `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 修改 | 手动暂停提示、banner 条件区分 |
| `web/src/i18n/pages/opsflow/en.ts` | 修改 | 新增 2 个 i18n 键 |
| `web/src/i18n/pages/opsflow/zh-cn.ts` | 修改 | 新增 2 个 i18n 键 |

---

## 5. 测试计划

### 5.1 单元测试（新建 test_manual_pause.py）

| # | 测试 | 类型 | 断言 |
|---|------|------|------|
| 1 | `_is_manual_pause_node()` 返回 True | 单元 | `_is_manual_pause_node()` |
| 2 | `_is_manual_pause_node()` 非手动暂停返回 False | 单元 | `assertFalse` |
| 3 | `ManualPausePlugin.execute()` 返回 success | 单元 | `result['success'] is True` |
| 4 | `ManualPausePlugin` 零参数 | 单元 | `get_form_config() == []` |

### 5.2 集成测试

| # | 测试 | 方法 |
|---|------|------|
| 1 | manual_pause 节点执行后 execution 状态为 paused | mock signal → assert status |
| 2 | paused 后调用 resume → 状态变为 running | mock resume → assert status |

### 5.3 验证方式

```bash
python manage.py test opsflow.tests.test_manual_pause --failfast
```

---

## 6. 注意事项

1. **context 字段暴露:** 需要确保 execution serializers 的 `context` 字段在 GET 响应中返回，否则前端无法读取 `_pause_reason`。检查 `ExecutionSerializer` 的 fields。
2. **无参数形式 schema:** `get_form_config()` 返回空列表时，PropertyPanel 应正确渲染（不显示表单区域），验证一下前端 RenderForm 对空 schema 的处理。
3. **Resume 按钮已经存在:** 确认不重复添加 Resume 按钮，仅区分提示文案。
4. **审批 + 手动暂停混用:** 如果审批节点在前、手动暂停在后，两次暂停各自独立，不影响。
