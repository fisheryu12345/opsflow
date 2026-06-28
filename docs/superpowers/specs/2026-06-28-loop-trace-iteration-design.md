# Loop/回环场景下的 Trace 迭代记录

> **版本:** v1.0  
> **日期:** 2026-06-28  
> **关联:** `NodeExecutionTrace` 模型  
> **状态:** 设计完成，待评审

---

## 1. 问题

当节点在 loop 场景下执行多次时，`NodeExecutionTrace` 只保留了**最后一次**迭代的记录。根因：

- `unique_together = (('execution', 'node_id', 'retry_count'),)` — 一个节点在一个 execution 中只能有一行 `retry_count=0` 的记录
- loop 迭代（非 retry）不改变 `retry_count`，所以第二次迭代的 FINISHED 信号会覆盖第一次的 `outputs`/`exited_at` 等字段
- 前端 Traces tab 只能看到最后一次迭代的输入输出

**涉及场景：**

| 场景 | 机制 | 说明 |
|------|------|------|
| Mechanism A | `loop_config` | 节点级批量循环，同节点连续执行 N 次 |
| Mechanism B | 排他网关回环边 | 条件驱动的轮询，节点被多次经过 |

---

## 2. 方案：`loop_iteration` 字段

### 2.1 数据模型

```python
# backend/opsflow/models/execution.py — NodeExecutionTrace

class NodeExecutionTrace(models.Model):
    # ... 现有字段不变 ...
    loop_iteration = models.IntegerField(
        default=0, verbose_name="Loop Iteration",
        help_text="Iteration index for loop/cycle scenarios. "
                  "0 = first execution, 1 = second, etc. "
                  "循环/回环场景的迭代序号 / 0=首次执行"
    )

    class Meta:
        unique_together = (('execution', 'node_id', 'retry_count', 'loop_iteration'),)
```

### 2.2 核心逻辑

```python
# backend/opsflow/signals/trace.py

def _resolve_loop_iteration(execution, node_id, retry_count) -> int:
    """确定本次信号对应的 loop_iteration

    如果 (rc, li=N) 的已有 trace 状态已经是 FINISHED/FAILED，
    说明引擎已开始新一轮执行 → 返回 N+1。
    否则返回已有 li（正常更新路径）。
    """
    existing = NodeExecutionTrace.objects.filter(
        execution=execution, node_id=node_id, retry_count=retry_count
    ).order_by('-loop_iteration').first()

    if existing and existing.status in ('FINISHED', 'FAILED'):
        return existing.loop_iteration + 1
    return existing.loop_iteration if existing else 0
```

### 2.3 数据流

```
loop iteration 1 (0):
  RUNNING → _resolve(rc=0) → 无已有行 → li=0 → get_or_create → 行(li=0)
  FINISHED → _resolve(rc=0) → 行(li=0) 正在 FINISHED → li=0 → 更新 outputs

loop iteration 2 (1):
  RUNNING → _resolve(rc=0) → 行(li=0) 状态=FINISHED → li=1 → get_or_create → 行(li=1)
  FINISHED → _resolve(rc=0) → 行(li=1) 正在 FINISHED → li=1 → 更新 outputs

loop iteration 3 (2):
  → li=2 → 新行
```

### 2.4 前端改动

```typescript
// 行 key: 加入 loop_iteration
rowKey: (row: any) => row.node_id + '-' + row.retry_count + '-' + row.loop_iteration
```

可选显示 iteration 列的代码：

```vue
<el-table-column label="Iteration" width="80" align="center">
  <template #default="{ row }">
    <el-tag v-if="row.loop_iteration > 0" size="small" type="warning">
      #{{ row.loop_iteration + 1 }}
    </el-tag>
    <span v-else>1</span>
  </template>
</el-table-column>
```

---

## 3. 改动文件清单

| 文件 | 改动 |
|------|------|
| `backend/opsflow/models/execution.py` | `NodeExecutionTrace` 新增 `loop_iteration` 字段，修改 `unique_together` |
| `backend/opsflow/signals/trace.py` | 新增 `_resolve_loop_iteration()`，修改 `_record_node_trace()` |
| `backend/opsflow/serializers.py` | `NodeExecutionTraceSerializer` 加 `loop_iteration` |
| `web/.../execution-api/types` (如有) | TypeScript 接口加 `loop_iteration` |
| `web/.../ExecutionDetail.vue` | 行 key 加入 `loop_iteration` |

---

## 4. 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 如何处理多次迭代 | 新增行 + `loop_iteration` 字段 | 不破坏现有 `retry_count` 语义，兼容已有 API |
| `unique_together` 组合 | `(execution, node_id, retry_count, loop_iteration)` | 与现有约束兼容，现有数据 `li=0` 自动兼容 |
| 迭代检测方式 | 查已有 trace 的 status | 直接、无状态、无副作用 |
| 与 retry 的关系 | 独立维度 | `loop_iteration` 和 `retry_count` 正交，互不影响 |
