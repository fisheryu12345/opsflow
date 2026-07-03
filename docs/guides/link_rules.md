# 连线规则（基于源码深入梳理）

> 本文档基于 OPSflow 引擎源码（`pipeline_builder/__init__.py`、`bamboo_validator.py`、`conflict_checker.py`、`safety_guard.py`、`elements.py`、`conditions.py`、`pipeline_schema.py`）提取的完整连线约束。

---

## 一、节点类型一览

| node_type | 角色 | bamboo-engine 映射 | 备注 |
|---|---|---|---|
| `""` 或 `"atom"` | 原子节点（任务） | `ServiceActivity` | 默认类型，通过 `atom_type` 指定具体操作 |
| `"start_event"` | 开始节点 | `EmptyStartEvent` | **纯视觉**，构建时被过滤不掉入bamboo树 |
| `"end_event"` | 结束节点 | `EmptyEndEvent` | **纯视觉**，构建时被过滤 |
| `"exclusive_gateway"` | 排他网关 | `ExclusiveGateway` | 从多条出边中选择**一条**执行 |
| `"parallel_gateway"` | 并行网关 | `ParallelGateway` | **所有**出边分支**全部**同时执行 |
| `"conditional_parallel_gateway"` | 条件并行网关 | `ConditionalParallelGateway` | 执行**满足条件**的分支（可多条） |
| `"converge_gateway"` | 汇聚网关 | `ConvergeGateway` | 合并多条入边为一条出边 |
| `"approval"` | 审批节点 | `ServiceActivity` | 特殊原子，加审批流程 |
| `"subprocess"` | 子流程 | `ServiceActivity` / `SubProcess` | 引用其他模板 |

---

## 二、出入度规则（核心连线约束）

| 节点类型 | 入度(min) | 出度 | 出度特殊约束 |
|---|---|---|---|
| `atom` / `""` | ≥ 1 | 1~2 | 出度=2时，标签**必须**恰好为 `{"success", "failure"}` |
| `exclusive_gateway` | ≥ 1 | ≥ 1 | 无上限 |
| `parallel_gateway` | ≥ 1 | ≥ 1 | 无上限，**必须**配对 `converge_gateway` |
| `conditional_parallel_gateway` | ≥ 1 | ≥ 1 | 无上限，**必须**配对 `converge_gateway` |
| `converge_gateway` | ≥ 1 | **= 1** | 出度只能为1；多条出边时取第一条并告警 |
| `start_event` | — | — | 视觉节点，构建时过滤，不做校验 |
| `end_event` | — | — | 视觉节点，构建时过滤，不做校验 |

**关键源码** — `bamboo_validator.py:100-119`：

```python
if nt in ('', 'atom'):
    if oc > 2:
        errors.append(f"活动 '{name}' 出度={oc}，最多允许 2 条")
    if oc == 2:
        labels = {e.get('label', '') for e in edges if e.get('from') == n['id']}
        if labels != {'success', 'failure'}:
            errors.append(f"活动 '{name}' 两条出边标签必须是 success 和 failure")
elif nt == 'converge_gateway':
    _check_degree(n, '汇聚网关', min_in=1, max_out=1)
```

---

## 三、边标签规则

### 3.1 标签与条件的对应关系

| 边标签 | 自动生成的条件表达式 | 含义 |
|---|---|---|
| `"success"` | `${_result == True}` | 节点执行成功 |
| `"failure"` | `${_result == False}` | 节点执行失败 |
| 无标签 / 其他 | 默认 `${_result == True}` | 按success处理 |

源码 — `conditions.py:70-78`：

```python
def _get_condition(conditions, from_id, to_id, label=""):
    key = f"{from_id}->{to_id}"
    custom = conditions.get(key)
    if custom:
        return custom
    if label == 'failure':
        return '${_result == False}'
    return '${_result == True}'
```

### 3.2 标签约束速查

| 场景 | 边标签要求 | 违反后果 |
|---|---|---|
| 原子节点1条出边 | 任意/无标签 | 正常 |
| 原子节点2条出边 | **必须**恰好为 `success` + `failure` | **报错** |
| 排他网关多条出边 | 建议 `success`/`failure` | 缺少标签**告警** |
| 并行网关出边 | 任意/无标签 | 正常（无条件判断） |
| 条件并行网关出边 | 建议 `success`/`failure` | 缺少标签**告警** |
| 汇聚网关出边 | **只能有1条** | 多条出边**告警**并取第一条 |

---

## 四、网关自动配对规则（易错点）

源码 — `pipeline_builder/__init__.py:129-165`。

`parallel_gateway` 和 `conditional_parallel_gateway` 的汇聚配对逻辑：

1. 构建器会从并行网关出发，沿出边**BFS遍历**下游所有路径
2. 如果所有分支的**最终下游**都是 `end_event`（即没有明确汇聚网关），则不配对
3. 只要**有任何一条**分支的最终下游不是 `end_event`，构建器就自动查找 `converge_gateway` 并配对

**BFS查找汇聚网关**：

```python
def _find_converge(gw_id: str):
    visited = {gw_id}
    q = deque()
    for e in out_edges.get(gw_id, []):
        q.append(e['to'])
    while q:
        nid = q.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        node = next((n for n in effective_nodes if n['id'] == nid), None)
        if node.get('node_type') == 'converge_gateway':
            return nid
        for e in out_edges.get(nid, []):
            if e['to'] not in visited:
                q.append(e['to'])
    return None
```

**配对触发条件**：并行网关的任意一条出边最终不指向 `end_event` 时触发。

**配对约束**：
- 所有并行的分支都汇聚到**同一个** `converge_gateway`
- 汇聚网关的入度建议 ≥ 2（小于2会告警，但可以运行）

---

## 五、构建器自动插入规则（LLM常忽略）

源码 — `pipeline_builder/__init__.py:73-121`。

### 5.1 多根节点自动并行

如果多个节点都是入度为0的根节点，构建器**自动插入**一个 `ParallelGateway`：

```python
if len(queue) == 1:
    start.extend(elem_map[queue[0]])
elif len(queue) > 1:
    pg = ParallelGateway()
    start.extend(pg)
    for rid in queue:
        pg.connect(elem_map[rid])
```

### 5.2 原子节点2条出边自动排他网关

原子节点有2条出边且标签为 `success/failure` 时，构建器**自动插入**一个 `ExclusiveGateway`：

```python
if has_success and has_failure and labels <= {'success', 'failure'}:
    gw = ExclusiveGateway()
    for i, s in enumerate(successors):
        cond = _get_condition(edge_conditions, nid, s['to'], s.get('label', ''))
        gw.add_condition(i, cond)
    elem.extend(gw)
    for s in successors:
        gw.connect(elem_map[s['to']])
```

> **重要**：这意味着LLM在原子节点后面**不需要**手动插 `exclusive_gateway`，构建器会自动处理。

### 5.3 原子节点非标准标签自动并行

如果原子节点有2条以上出边，或标签不是标准的 `success/failure`，构建器**自动插入** `ParallelGateway`：

```python
else:
    pg = ParallelGateway()
    elem.extend(pg)
    for s in successors:
        pg.connect(elem_map[s['to']])
```

### 5.4 无后继节点自动连结束

任何节点如果没有出边，构建器自动连接 `EmptyEndEvent`。

---

## 六、条件表达式规则

源码 — `bamboo_validator.py:141-153`。

条件表达式格式：`${node_id.key}`，其中 `node_id` 必须是已存在的节点ID，`key` 是该节点输出中的字段。

```python
# 检查 ${node_id.key} 中 node_id 的合法性
for var_match in _VAR_REF_PATTERN.finditer(expr):
    ref_node_id = var_match.group(1)
    if ref_node_id not in effective_ids:
        errors.append(f"引用不存在的节点 '{ref_node_id}'")
```

---

## 七、安全规则补充

源码 — `safety_guard.py:67-75`。

- **高危原子节点**（`risk_level="high"`）必须有回滚路径：出边中必须有一条标签为 `"failure"` 或 `"rollback"` 的边
- **孤儿节点检测**：非开始节点的节点如果没有入边，会告警

---

## 八、大模型生成流程图的常见错误清单

| # | 错误类型 | 错误表现 | 正确做法 |
|---|---------|---------|---------|
| 1 | **汇聚网关出度>1** | 给 `converge_gateway` 连了多条出边 | 汇聚网关出度**必须=1** |
| 2 | **原子节点出度>2** | 给原子节点连了3条以上出边 | 原子节点最多2条出边 |
| 3 | **原子节点2条出边标签不对** | 用了 `"ok"/"fail"` 等非标准标签 | 必须用 `"success"` 和 `"failure"` |
| 4 | **并行网关无汇聚网关** | `parallel_gateway` 分支没汇聚或汇聚到不同的网关 | 所有并行分支必须汇聚到**同一个** `converge_gateway` |
| 5 | **汇聚网关入度<2** | 汇聚网关只连了1条入边 | 汇聚网关至少汇聚2个分支，入度≥2 |
| 6 | **排他网关缺少条件** | 排他网关多条出边没有条件表达式 | 多条出边应设置 `condition` 或至少标 `success/failure` |
| 7 | **环依赖** | 流程中存在循环引用 | bamboo-engine必须DAG（有向无环图） |
| 8 | **边引用不存在的节点** | `from` 或 `to` 指向不存在的ID | 边必须引用已声明的节点ID |
| 9 | **节点ID不唯一** | 重复的节点ID | 所有节点ID必须唯一 |
| 10 | **独占网关自动插入误解** | LLM在原子节点后面手动插 `exclusive_gateway` | 原子节点的 `success/failure` 出边会在构建器**自动**插入排他网关，不需要手动加 |
| 11 | **遗漏高危回滚路径** | 高危原子节点没有回滚边 | 高危节点至少有一条 `failure` 或 `rollback` 出边 |

---

## 九、完整连线规则速查表

| 连线类型 | 入度 | 出度 | 标签要求 | 条件要求 | 特殊约束 |
|---------|------|------|---------|---------|---------|
| 原子节点→后继 | ≥1 | 1~2 | 2条出边必须 `success`+`failure` | 自动生成(或自定义) | 出度=2时构建器自动插入 `ExclusiveGateway` |
| 排他网关→分支 | ≥1 | ≥1 | 建议 `success`/`failure` | 建议设置，否则告警 | 只执行一条满足条件的分支 |
| 并行网关→分支 | ≥1 | ≥1 | 不重要（无条件） | 不需要 | 所有分支全执行，必须配对汇聚网关 |
| 条件并行网关→分支 | ≥1 | ≥1 | 建议 `success`/`failure` | 需要条件表达式 | 执行满足条件的分支，必须配对汇聚网关 |
| 汇聚网关→后继 | ≥1 | **=1** | 不重要 | 不需要 | 出度只能为1；入度建议≥2 |
| 开始节点→首个节点 | — | — | — | — | 纯视觉，构建时过滤；多根时自动插ParallelGateway |
| 末节点→结束节点 | — | — | — | — | 无后继节点自动连EmptyEndEvent |
| 审批节点→后继 | ≥1 | 1~2 | 同原子节点 | — | 同原子节点规则 |
| 子流程→后继 | ≥1 | 1~2 | 同原子节点 | — | 同原子节点规则 |

---

## 十、典型正确结构示例

### 串行
```
atom1 → atom2 → atom3
```

### 分支（atom→2出边）
```
atom1 --success--> atom2
atom1 --failure--> atom3
```
> 构建器自动在atom1和atom2/atom3之间插入 ExclusiveGateway

### 排他网关分支
```
atom1 → exclusive_gw --success--> atom2
                  \--failure--> atom3
```

### 并行汇聚
```
parallel_gw → (branch1, branch2, branch3) → converge_gw → next_node
```

### 条件并行汇聚
```
cond_parallel_gw --条件A--> branch1
                --条件B--> branch2
                        → converge_gw
```

### 组合
```
atom1 → exclusive_gw → (branch A: atom2)
                     → (branch B: parallel_gw → ... → converge_gw)
                      → atom3
```

---

## 十一、相关源码文件索引

| 文件 | 内容 |
|------|------|
| [pipeline_builder/__init__.py](../core/pipeline_builder/__init__.py) | 完整构建流程，含自动插入网关、配对逻辑 |
| [pipeline_builder/elements.py](../core/pipeline_builder/elements.py) | 节点元素工厂，按 node_type 创建对应 bamboo 元素 |
| [pipeline_builder/conditions.py](../core/pipeline_builder/conditions.py) | 边条件解析与自动变量映射 |
| [bamboo_validator.py](../core/bamboo_validator.py) | 出入度校验、环检测、条件引用校验 |
| [conflict_checker.py](../core/conflict_checker.py) | 6条语义冲突检测规则 |
| [safety_guard.py](../core/safety_guard.py) | 原子白名单、高危回滚、孤儿节点 |
| [pipeline_schema.py](../core/pipeline_schema.py) | JSON Schema 层节点类型枚举 |
| [llm_service.py](../core/llm_service.py) | LLM生成提示词中的连线规则定义 |
