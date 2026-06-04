# OpsFlow 前后端代码优化计划

## Context

基于全面代码审查，OpsFlow 前后端整体代码质量良好，但随着功能迭代，部分区域已出现可优化的重复模式、过长函数和可提取的共享逻辑。本计划聚焦**不改变功能/逻辑**的纯重构优化，按收益/风险比排序。

---

## 一、后端：高优先级（P0-P1）

### P0-1: 统一 `signals/handlers.py` 重复的 try/except 模式

**文件：** `backend/opsflow/signals/handlers.py:69-103`

**问题：** 7 个完全相同的 try/except 块，仅函数名不同：
```python
try:
    _update_execution_node_status(execution, node_id, to_state)
except Exception:
    logger.exception("[Signal] _update_execution_node_status error ...")
try:
    _update_state_tree(execution, node_id, to_state)
except Exception:
    logger.exception("[Signal] _update_state_tree error ...")
# ... 又 5 次
```

**改造：** 提取 `_safe_signal_handler(func, execution, node_id, to_state)` 辅助函数，将 7 个块压缩为 1 个循环。

**风险：** 低 — 纯提取，不改变行为 | **节省：** ~30 行

---

### P0-2: 消除 `states.py`↔`state.py` 间重复的状态映射

**文件：** `backend/opsflow/core/states.py`, `backend/opsflow/signals/state.py`

**问题：** bamboo-engine 状态→OpsFlow 状态映射在 2 个文件间定义了 4 次。`signals/state.py` 中的 `_update_execution_node_status`、`_update_state_tree`、`_map_bamboo_state` 各自维护独立的字典，与 `states.py` 中的 `NodeState.bamboo_label()` 重复。

**改造：** 让 state.py 各函数统一使用 `NodeState.bamboo_label().get(to_state, "").value` 和 `map_pipeline_state(to_state).value`。

**风险：** 低 — 统一调用规范映射 | **节省：** ~30 行重复映射定义

---

### P0-3: 提取 `pipeline_builder/__init__.py` 中的长函数

**文件：** `backend/opsflow/core/pipeline_builder/__init__.py:22-242`

**问题：** `build_bamboo_pipeline()` 达 220 行，内部已用注释标记了 7 个阶段。

**改造：** 将每个阶段提取为独立函数：
- `_filter_nodes_and_edges(tree, excluded)` 
- `_build_adjacency_lists(nodes, edges)`
- `_create_all_elements(...)` 
- `_topological_connect(...)` 
- `_pair_converge_gateways(...)` 
- `_build_data_inputs(...)` (同时消除与 `_empty_pipeline` 的重复)
- `_build_id_map(...)`

**风险：** 低 — 每个新函数对应一个现有注释阶段 | **节省：** 主函数降为 ~50 行编排逻辑

---

### P0-4: 统一 `template_ai.py` 响应格式

**文件：** `backend/opsflow/views/mixins/template_ai.py`

**问题：** 全文件使用原始 `Response()`，是唯一完全不使用 `DetailResponse`/`ErrorResponse` 的 mixin。同时 50 行 AI 验证逻辑在 `create_from_ai` 和 `refine` 之间重复。

**改造：** 
1. 将所有 `Response()` 替换为 `DetailResponse`/`ErrorResponse`
2. 提取共享验证函数 `_validate_ai_pipeline(pipeline, nl_input)`

**风险：** 低 — 响应格式标准化 | **节省：** ~40 行

---

### P1-1: 消除 N+1 查询（子流程引用）

**文件：** 
- `backend/opsflow/models/template.py:57-71` (publish_snapshot)
- `backend/opsflow/views/mixins/template_subprocess.py:28-39` (subprocess_status)
- `backend/opsflow/views/mixins/template_subprocess.py:66-84` (update_subprocess_refs)

**问题：** 3 个位置在 `for` 循环内逐条查询 `FlowTemplate.objects.get(id=target_id)`，构成 N+1 查询。

**改造：** 使用 `FlowTemplate.objects.filter(id__in=all_target_ids)` 批量预取后按 ID 索引。

**风险：** 低 | **节省：** 消除循环内 N 次 DB 查询

---

### P1-2: 简化 `views/base.py` 中重复的基类

**文件：** `backend/opsflow/views/base.py:11-144`

**问题：** `ProjectFilteredViewSet` 和 `ProjectReadOnlyViewSet` 中的 `get_user_project_ids()`、`_add_public_q()`、`get_queryset()` 完全重复。

**改造：** 让 `ProjectReadOnlyViewSet(ProjectFilteredViewSet)`，只覆盖需要不同的方法。

**风险：** 低 | **节省：** ~40 行重复代码

---

### P1-3: 提取 `FlowEngine._runtime` 属性和 `_fail_execution`

**文件：** `backend/opsflow/core/flow_engine.py`

**问题：** 
- `BambooDjangoRuntime()` 在 8 个方法中重复实例化
- `run()` 中 4 次重复的失败处理模式
- `retry`/`retry_subprocess` 中重复的 5 行状态更新

**改造：** 
1. 添加 `@property def _runtime(self)` 惰性属性
2. 提取 `_fail_execution(message, do_rollback=False)` 方法
3. 提取 `_update_node_status(node_id, status)` 方法

**风险：** 低 | **节省：** ~20 行

---

### P1-4: 统一 `template_views.py` 分页响应格式

**文件：** `backend/opsflow/views/template_views.py`

**问题：** 列表接口手动构建分页元数据，与 execution_views 使用的标准 `get_paginated_response()` 不一致。

**改造：** 改用 `self.get_paginated_response()`。

**风险：** 低 | **节省：** 提高一致性

---

## 二、后端：中优先级（P2）

| # | 改进项 | 文件 | 说明 | 评估 |
|---|--------|------|------|------|
| P2-1 | 提取 PluginService 共享参数解析 | `plugin_service_adapter.py` | execute/schedule/rollback 三重提取 `_extract_params()` | ~15 行 |
| P2-2 | 抽象 `CreationTracked` 基类 | `models/template.py`, `models/execution.py` | 5 个模型共享 `created_by+created_at` | 5 模型简写 |
| P2-3 | 提取 `_post_save_cleanup` 辅助 | `template_version.py`, `template_views.py`, `template_variable.py` | `cleanup_unused_vars`+`sync_template_nodes` 重复 7 次 | ~20 行 |
| P2-4 | 统一 `template_webhook.py` 响应格式 | `views/mixins/template_webhook.py` | 混用 3 种响应类→统一 DetailResponse/ErrorResponse | ~10 行 |
| P2-5 | 批量节点操作统一 | `execution_node_command.py` | batch_retry/batch_skip 80% 重复→`_batch_node_command` | ~20 行 |
| P2-6 | 审批节点统一 | `execution_approval.py` | approve/reject 共享上下文变更→`_record_approval_decision` | ~15 行 |
| P2-7 | 简化 `execution_views.py` 权限检查 | `execution_views.py` | perform_create/dry_run 重复→复用 resolve_project_kwargs | ~10 行 |
| P2-8 | 移除死代码 | `safety_guard.py` | 删除 `BACKUP_REQUIRED_ATOMS()` 和引用的 ~10 行 | ~10 行 |

---

## 三、前端：高优先级（P0-P1）

### F-P0-1: 拆分 `SubmitWizardDialog.vue`（1488 行）

**文件：** `web/src/views/apps/opsflow/components/SubmitWizardDialog.vue`

**问题：** 全代码库最大的文件。5 个独立的向导步骤挤在一个文件中。

**改造：** 每个步骤提取为独立组件：
- `ValidationStep.vue`
- `ChangeRequestStep.vue`  
- `ParametersStep.vue`
- `RiskStep.vue`
- `ScheduleStep.vue`

父组件只编排步骤切换。CSS 跟着拆到各子组件。

**风险：** 低 — 每步骤是独立的 `v-show` 块 | **节省：** 父组件降至 ~400 行

---

### F-P0-2: 集中条件验证逻辑（当前 3 份副本）

**文件：** 
- `web/src/views/apps/opsflow/composables/useGraphCanvas.ts:269-321`
- `web/src/views/apps/opsflow/composables/useGraphValidator.ts:196-215`
- `web/src/views/apps/opsflow/components/DesignCanvas.vue:345-362`

**问题：** `${...}` 括号匹配、引号匹配、节点引用校验逻辑在 3 个不同文件中重复，正则模式定义 3 份。

**改造：** 提取共享验证函数到 `utils/shapes.ts`，各调用点统一引用。

**风险：** 低 — 纯函数提取 | **节省：** ~80 行重复，消除 bug 源

---

### F-P1-1: 拆分 `PropertyPanel.vue`（734 行）

**文件：** `web/src/views/apps/opsflow/components/PropertyPanel.vue`

**问题：** 4 种节点类型（atom/subprocess/approval/edge）+ 4 层 `v-if` 嵌套链。

**改造：** 提取子组件：`AtomConfigPanel.vue`、`SubprocessConfigPanel.vue`、`ApprovalConfigPanel.vue`、`EdgeConfigPanel.vue`

**风险：** 低 | **节省：** 主组件降 ~70%

---

### F-P1-2: 前端 API CRUD 工厂化

**文件：** `web/src/api/opsflow/*.ts`

**问题：** 12 个 API 文件各自声明 `const prefix = '/api/opsflow/'`；4+ 个文件重复 CRUD 模式。

**改造：** 
1. 将 `prefix` 从 `request.ts` 导出并复用
2. 添加 `createCrudApi(resource)` 工厂函数

**风险：** 低 | **节省：** ~60 行

---

### F-P1-3: 集中 TypeScript 类型定义

**文件：** `utils/shapes.ts` + `stores/opsflowStore.ts` + `composables/useGraphCanvas.ts` + `composables/useGraphValidator.ts` + `MonitorCanvas.vue`

**问题：** `FlowTemplate`、`FlowExecution`、`ValidationResult`、`MonitorAttrs` 等类型分散在 5 个文件。

**改造：** 新建 `types/index.ts`，集中所有共享接口。

**风险：** 低 — 纯类型迁移 | **节省：** 统一维护点

---

## 四、前端：中优先级（P2-P3）

| # | 改进项 | 文件 | 说明 |
|---|--------|------|------|
| F-P2-1 | Edge attrs 常量集中 | `useDesignCanvas.ts` + `useGraphCanvas.ts` + `MonitorCanvas.vue` | 6 处重复 `{line:{stroke:'#DCDFE6', strokeWidth:1.5, targetMarker:'classic'}}` → 单常量 |
| F-P2-2 | 纯函数移出 composable | `useGraphCanvas.ts` | `layoutNodes`、`generateConditionExpr`、`opsForType` 等→移入 `utils/graph-utils.ts` |
| F-P2-3 | 抽取 WizardSteps 组件 | `SubmitWizardDialog.vue` + `CreateTemplateWizard.vue` | 步骤指示器 HTML+CSS 完全重复 |
| F-P2-4 | 抽取 ZoomControls 组件 | `DesignCanvas.vue` + `MonitorCanvas.vue` | 缩放控件重复 |
| F-P2-5 | 抽取 PanelHero 组件 | `SubmitWizardDialog.vue` + `CreateTemplateWizard.vue` | 面板头部模式重复 7+ 次 |
| F-P2-6 | 抽取 ModeCard 组件 | `SubmitWizardDialog.vue` + `CreateTemplateWizard.vue` | 模式选择卡片重复 |
| F-P2-7 | index.vue 拆分 | `index.vue` | AI 聊天浮窗 (~250 行)→`AiChatPanel.vue` |
| F-P3-1 | 统一 v-model 模式 | 多对话框 | `computed get/set` → `useVModel()` 或抽 composable |
| F-P3-2 | DesignCanvas emits→props | `DesignCanvas.vue` | 简单回调事件改用 callback props |
| F-P3-3 | 简化 `executions.ts` 可选字段构建 | `api/opsflow/executions.ts` | `const data:any={}; if(x) data.x=x` → `compactData()` 辅助函数 |

---

## 五、验证方案

1. **后端：** 运行 `python manage.py test opsflow.tests` 确保全部测试通过
2. **前端：** 运行 `cd web && npm run build` 确保构建通过
3. **响应格式：** 通过 `curl` 或 Postman 对比重构前后的 API 响应 JSON
4. **状态映射：** 对 `states.py` 修改后，确认现有信号处理流程状态映射不变
