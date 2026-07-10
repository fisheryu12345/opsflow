# 条件运算符标准化 — BoolRule 兼容

> 最后更新: 2026-07-10
> 涉及版本: f689e639

---

## 1. 背景与现象

OpsFlow 的条件编辑器 `useGraphCanvas.ts` 中字符串类型的条件运算符列表包含 `contains`、`not contains`、`startsWith`、`endsWith`、`regex`，但这些运算符在 `BoolRule`（后端条件求值引擎）中不被支持。

ITSM 设计器引用 OpsFlow 的 `opsForType()` 函数来获取可用运算符列表，导致 ITSM 设计器中用户可选 `contains`/`startsWith` 等运算符，但保存的条件表达式在后端 `BoolRule` 求值时失败。

**BoolRule 支持的运算符：** `==`、`!=`、`>`、`<`、`>=`、`<=`、`in`、`notin`

---

## 2. 排查思路

对比 `BoolRule` 的 `evaluate()` 方法签名与 `opsForType()` 返回的运算符列表：

```
BoolRule 支持: == != > < >= <= in notin
opsForType 返回: == != contains "not contains" startsWith endsWith regex
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                不匹配的部分
```

`in`/`notin` 已覆盖 `contains` 的需求（表达 `${node.field} in ['a','b']`），而 `startsWith`/`endsWith`/`regex` 在前端条件编辑场景中使用频率极低且 BoolRule 不支持。

---

## 3. 根因分析

`opsForType()` 最初为前端的可视化条件编辑器设计，包含了面向用户友好的运算符（如 `contains`），但后端 `BoolRule` 求值器从未实现这些运算符的解析逻辑。这导致用户选择的运算符在运行时静默失败。

---

## 4. 解决方案

### 4.1 `web/src/views/apps/opsflow/composables/useGraphCanvas.ts`

- **改动：** 字符串类型运算符列表从 `['==', '!=', 'contains', 'not contains', 'startsWith', 'endsWith', 'regex']` 改为 `['==', '!=', '>', '<', '>=', '<=', 'in', 'notin']`
- **目的：** 确保前端可选运算符与后端 `BoolRule` 兼容，消除静默失败

---

## 5. 验证

- 在 OpsFlow/ITSM 设计器中创建网关条件 → 选择 `in` / `notin` 运算符 → 保存工作流 → 执行工单 → 确认条件分支正确路由

---

## 6. 涉及文件清单

- `web/src/views/apps/opsflow/composables/useGraphCanvas.ts:174` — `opsForType()` 字符串运算符列表更新
