# Optional 节点失败自动跳过 (Skip-on-Fail)

> 提交: bae59bcc | 日期: 2026-06-28
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

PropertyPanel 的 Execution Control 区域中有一个 `Optional`（可选）开关，标记节点为"可选的"——执行失败时不阻塞流程，自动跳过让流程继续。此前这个开关只在冲突检测（`conflict_checker.py`）中被读取，执行阶段没有任何实际作用。

## 实现方案

### 核心架构

执行链：`节点失败 → FAILED信号 → dispatch_auto_retry() 无重试 → _check_optional_skip() → FlowEngine.skip()` → 流程继续

### 关键代码

#### `_check_optional_skip()` — 检测节点是否标记为 Optional

`signals/handlers.py:57-90`

```python
def _check_optional_skip(execution, node_id: str) -> bool:
    # 从 template_snapshot 中查找节点
    tree = execution.template_snapshot.get('pipeline_tree')
    # fallback 到 template.pipeline_tree
    for node in tree.get('nodes', []):
        if node.get('id') == node_id:
            return bool(node.get('optional', False))
    return False
```

- 优先使用执行时的冻结快照（`template_snapshot`），确保版本隔离
- 无 snapshot 时回退到模板当前 `pipeline_tree`
- 异常捕获为 `warning` + `return False`，不阻塞信号处理

#### FAILED 信号分支集成 — `on_post_set_state()`

`signals/handlers.py:125-133`

```python
if to_state == states.FAILED:
    if dispatch_auto_retry(execution, node_id):
        return
    # ── Optional 节点失败自动跳过 ──
    if _check_optional_skip(execution, node_id):
        FlowEngine(execution).skip(node_id)
        return
```

优先级：**auto_retry > optional** — 有重试配置时先走重试，重试耗尽或没有重试时才检查 optional。

#### 前端互斥

`PropertyPanel.vue:123-141`

| 控件 | 禁用条件 |
|------|----------|
| Optional switch | `max_retries > 0` 时禁用 |
| Max Retries input | `optional = true` 时禁用 |
| Retry Delay input | `optional = true` 时禁用 |

### 数据流

```
用户设置节点 Optional=True
  → 节点在 pipeline_tree 中 persistent optional=True
  → 执行时 bamboo-engine 检测到节点 FAILED
  → post_set_state 信号触发 on_post_set_state()
  → dispatch_auto_retry() 失败或不存在
  → _check_optional_skip() 读取 template_snapshot → 找到 optional=True
  → FlowEngine(execution).skip(node_id)
  → pipeline_api.skip_node() 跳过节点
  → 流程继续执行后续节点
```

### 设计决策

- **为什么 signal 中实现而不是 engine.run() 中？** 因为节点失败是异步事件（通过 bamboo-engine signal 上报），engine.run() 不会阻塞等待节点结果。信号处理器是唯一能拦截 FAILED 状态的地方。
- **为什么 auto_retry 优先？** 业务语义：如果用户同时设置了重试和 optional，说明用户希望先尝试恢复，恢复不了再跳过。两者不矛盾。
- **为什么用 template_snapshot 而不是 template.pipeline_tree？** 执行期间模板可能被编辑发布新版本，snapshot 保证了使用执行时的节点配置。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/signals/handlers.py` | 新增 `_check_optional_skip()` + FAILED 分支集成 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 前端互斥（max_retries/optional 相互 disabled） |
| `backend/opsflow/tests/test_optional_skip.py` | 10 个测试用例（7 单元 + 3 集成）|

## 使用方式

1. 在 PropertyPanel 中找到 `Execution Control` → `Optional` 开关
2. 打开 Optional 开关（如果已设置重试次数，开关被禁用）
3. 执行流程，该节点失败时自动跳过，流程继续
