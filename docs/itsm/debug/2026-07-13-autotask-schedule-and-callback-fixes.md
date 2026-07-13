# ITSM 自动任务节点调度与回调修复

> 提交: af55af09 | 日期: 2026-07-13
> 涉及 App: itsm, opsflow
> 类型: Bug 修复

---

## 背景

ITSM 自动任务(TASK)节点接入 OpsFlow 后，实测出现节点卡死 / 被误判 FAILED / 表单字段渲染错误等一系列问题。经代码审查(含 bamboo 源码核对)定位到多处缺陷。

## 问题与修复

### 1. `schedule()` 返回 `False` 会把节点判 FAILED(而非"继续等待")

- **背景**:bamboo `service_activity.py` 中 `schedule_success = service.schedule(...)`，若返回假值且节点非 `error_ignorable`，直接 `set_state(to_state=FAILED)`。原代码在 Phase 2 的 `running/pending`、execution 不存在、Phase 1 无 callback 三处 `return False` 注释写着"继续等待"，实际会把节点判失败。
- **办法**:所有"继续等待"路径改为 `return True`(且不调 `finish_schedule()`)。MULTIPLE_CALLBACK 节点返回 True 且未 finish → bamboo 保持挂起等下次回调。

```python
# 修复前 — 实际会把节点判 FAILED
if execution.status in ('running', 'pending'):
    return False  # spurious/early callback — keep waiting  ← 谎言
# 修复后
if execution.status in ('running', 'pending'):
    return True   # keep waiting, don't fail
```

### 2. 未绑定 OpsFlow 模板的 TASK 节点永久卡死

- **背景**:改为 `__need_schedule__=True` 后，无模板的 TASK 节点在 `schedule()` 里因无 callback 一直等待一个永远不会到来的回调(无 UI 提交入口)，且旧版 WorkflowVersion 快照里没有 `extras` → template_id 恒空 → 全部卡死。
- **办法**:`execute()` 中检测无 `opsflow_template_id` 时恢复旧的同步 pass-through(`do_in_state({auto_executed}) + do_before_exit_state`)并置 `self._auto_completed`;覆写 `need_schedule()` 在自动完成时返回 False，节点不进调度。

```python
def need_schedule(self):
    if getattr(self, '_auto_completed', False):
        return False   # 无模板已同步完成，别等回调
    return super().need_schedule()
```

### 3. OpsFlow 提前失败/取消时 ITSM 节点挂死

- **背景**:`flow_execution_finished` 只在 bamboo root 状态变为 COMPLETED/FAILED 时由 `_handle_root_state_change` 发出。`FlowEngine._fail_execution`(校验失败/空 pipeline)和 `cancel()` 直接改状态、绕过该路径 → 信号不发 → 等待中的 ITSM 节点永远收不到回调。
- **办法**:在 `_fail_execution` 和 `cancel()` 里显式 `flow_execution_finished.send(status='FAILED'/'CANCELLED')`。

### 4. 完成回调无法解析到 ITSM 节点(`_pipeline_id_map` 键是 node_key 非 state_id)

- **背景**:`on_opsflow_finished` 原用 `state_id` 去匹配 `_pipeline_id_map`，但该 map 的 key 是 `node_85` 这类 node_key，匹配不到 → 节点永不唤醒。
- **办法**:复用与填单/审批回调同一套 `resolve_activity_id(ticket, state_id)`(state_id → node_key → 加盐 element id)。

### 5. `FlowExecution.objects.create` 两处崩溃

- **背景**:`created_by=ticket.creator` 把 int 赋给外键(应为 `created_by_id`);`global_vars=` 不是 FlowExecution 字段(运行时全局变量在 `template_snapshot`)。
- **办法**:改 `created_by_id=ticket.creator`;删除 `global_vars=` 入参，把解析值注入 `snapshot['global_vars']`。

### 6. `_resolve_vars` 崩溃 + 变量取值错误

- **背景**:`re.sub` 假设 mapping 值都是字符串，遇 int/list/dict 抛 TypeError;`${field.X}` 只读陈旧的 `ticket.meta.form_data`，取不到用户刚提交的值。
- **办法**:非字符串 mapping 值原样透传;把 `form_fields` 也并入 `${field.X}` 上下文(提交值优先)。

### 7. GlobalVarInput 字段类型渲染回归

- **背景**:SubmitWizard 内联的约 200 行按类型渲染被替换为 `<GlobalVarInput>`，但后者缺失 `host_selector/ip_selector`(退化为纯文本)、`select` 无 `multiple/filterable`、`date` 被当 `datetime` 渲染且无 `value-format`(吐 Date 对象)、`switch` 忽略 `meta.activeValue/inactiveValue`。此组件同时被提交向导和 TASK 表单使用。
- **办法**:补齐上述所有类型与属性;`date/datetime/time` 均加 `value-format`。

### 8. 输出同名冲突 + TicketDetail coerce 不一致

- **背景**:`_collect_execution_outputs` 用 `merged.update()` 扁平化，多节点同名输出后者覆盖前者;TicketDetail 调 `loadTemplateVars` 未传 `coerce:true`，checkbox/cascader 初值不转数组。
- **办法**:保留 `opsflow_<key>`(兼容网关引用)的同时新增 `opsflow_<node>_<key>` 节点作用域输出并对冲突打 warning;TicketDetail(现 TaskNodeForm)补 `coerce:true`。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/pipeline_plugins/components.py` | 调度返回值、need_schedule 覆写、变量解析、输出聚合修复 |
| `backend/opsflow/core/flow_engine.py` | fail/cancel 显式发 `flow_execution_finished` |
| `backend/itsm/signals.py` | 完成回调复用 `resolve_activity_id` |
| `web/src/components/GlobalVarInput.vue` | 补齐字段类型与 value-format |
| `web/src/composables/useTemplateVars.ts` | 标量→数组 coerce 兜底 |

## 验证

- bamboo `service_activity.py:639-658` 已确认 `return False → set_state(FAILED)`。
- 后端 `need_schedule()` 默认 True、自动完成 → False;三个后端文件 py_compile 通过。
- 手工回调复现:state_id 384 → `node_85_18707f`，节点由挂起→FINISHED，流程推进到下一审批节点(工单 242 实测恢复)。

### 关联文档

- 相关功能文档: [2026-07-13-itsm-autotask-opsflow-integration.md](../features/2026-07-13-itsm-autotask-opsflow-integration.md)
