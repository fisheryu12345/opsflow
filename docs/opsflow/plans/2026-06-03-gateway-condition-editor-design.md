# 前端网关条件编辑 UI 设计

> OpsFlow 排他网关/条件并行网关的条件表达式编辑交互设计
> 更新于：2026-06-03

## 背景

OpsFlow 的 ExclusiveGateway 和 ConditionalParallelGateway 支持条件分支，但条件编辑体验原始：

- 连线时弹出 `ElMessageBox.prompt`，让用户从 `success` / `failure` / `custom` 选择
- 选 `custom` 后弹文本框手写 `${node_1.cpu} > 80` 原始表达式
- PropertyPanel 中同样是裸露的 `textarea`，无语法提示、无变量补全、无实时校验
- 自定义条件引用 `${node_id.key}` 易写错 node_id 或字段名，错误只能在运行时暴露

## 目标

提供一个结构化的条件编辑体验，降低学习成本，减少语法错误，支持复杂多条件组合。

**不改变后端格式** — `edge.data.condition` 仍为 `${...}` 字符串，不修改 `pipeline_tree` 结构，不修改 `bamboo_builder.py` 条件编译逻辑。

## 方案选择

选择 **方案 B：条件构建器**，采用 **PropertyPanel 内嵌简版 + ConditionDialog 弹窗完整编辑器** 的混合模式。

## 架构

### 组件树

```
PropertyPanel.vue (选中边时)
  ├── el-select 标签下拉 (已有, 保持不动)
  ├── 条件表达式只读显示区
  └── [编辑条件] 按钮 → 打开 ConditionDialog

ConditionDialog.vue  ← 新组件
  ├── ConditionRow.vue (单行：变量 + 运算符 + 值)
  ├── AND/OR 逻辑切换
  ├── [+ 添加条件] 按钮
  ├── VariablePicker.vue  ← 新组件 (变量选择下拉)
  ├── 表达式实时预览区
  └── 校验结果提示

useGraphCanvas.ts
  ├── updateEdgeCondition(edgeId, structuredCondition)  ← 新方法
  ├── extractOutputFields(nodeId) → Field[]  ← 新方法
  └── validateConditionExpr(expr) → ValidationResult  ← 新方法
```

### 数据流

```
用户连排他网关边
  → edge:connected 事件 → 显示 ElMessageBox (success/failure/custom)
  → 选 custom → PropertyPanel 出现
  → 点击"编辑条件" → ConditionDialog 弹窗
  → 选择变量 → 选运算符 → 输入值
  → 弹出实时生成 ${node_1.cpu} > 80
  → 校验通过 → 确定
  → useGraphCanvas.updateEdgeCondition() 写入 edge.data
  → PropertyPanel 显示只读表达式

保存模板:
  → edge.data.condition 随 pipeline_tree 写入后端
  → bamboo_builder 正常编译（无变化）
```

### 数据结构

不修改现有 `pipeline_tree` 格式。`edge.data.condition` 仍为字符串：

```
// 当前格式（不变）
edge.data.condition = "${node_1.cpu} > 80"
edge.label = "custom"

// 新增结构化数据（仅供前端二次编辑回填）
edge.data.conditionStruct = {
  logic: "AND",                    // AND | OR
  rules: [
    {
      source: "node_1",            // 上游节点 ID 或 "global"/"project"/"_system"
      field: "cpu",                // 字段名
      fieldLabel: "cpu (number)",  // 展示用
      op: ">",                     // 运算符
      value: "80",                 // 比较值
      valueType: "number"          // number | string | boolean
    },
    {
      source: "node_1",
      field: "mem",
      fieldLabel: "mem (number)",
      op: "<",
      value: "50",
      valueType: "number"
    }
  ]
}
```

## UI 设计

### ConditionDialog 弹窗

- 弹窗标题："编辑条件 - {source_node} → {target_node}"
- 宽 680px，高自适应（最多 8 条件行后滚动）
- 每个条件行三列：变量选择器 | 运算符选择器 | 值输入
- 行之间用 AND/OR 逻辑连接按钮
- 底部：表达式预览 + 校验结果 + [取消][确定]

### 变量选择器 (VariablePicker)

分组下拉：

```
上游节点
  ├── node_1 (Disk Check)
  │   ├── _result (boolean)
  │   ├── cpu (number)
  │   ├── mem (number)
  │   └── stdout (string)
  └── node_2 (Ping Test)
      ├── _result (boolean)
      └── latency (number)
全局变量
  ├── env (string)
  └── threshold (number)
项目环境变量
  ├── alert_email (string)
  └── notify_url (string)
系统变量
  ├── _system.timestamp (string)
  └── _system.current_user (string)
```

数据来源：
- 上游节点输出 → 遍历画布中 DAG 的上游节点，从 `shapes.ts` 的 `outputSchemaMap` 读取
- 全局变量 → `globalVariables` (Pinia store)
- 项目环境变量 → `ProjectEnvVarPanel` 数据
- 系统变量 → 常量列表 `_system.timestamp`, `_system.current_user`

### 运算符列表

| 运算符 | 说明 |
|--------|------|
| `==` | 等于 |
| `!=` | 不等于 |
| `>` | 大于 |
| `<` | 小于 |
| `>=` | 大于等于 |
| `<=` | 小于等于 |
| `contains` | 包含子串 |
| `not contains` | 不包含子串 |
| `startsWith` | 以...开头 |
| `endsWith` | 以...结尾 |
| `regex` | 正则匹配 |

运算符根据变量类型自动筛选：
- `boolean` 类型只显示 `==` 和 `!=`
- `number` 类型显示所有比较运算符
- `string` 类型显示所有运算符

### PropertyPanel 边选中变化

**当前：** `el-input type="textarea"` 裸文本框

**改进后：** 只读显示的表达式 + `[编辑]` 按钮 + 变量标签列表

```
┌─────────────────────────────┐
│ 边标签: [success ▼]          │
│                              │
│ 条件:                        │
│ ┌─────────────────────┬────┐ │
│ │ ${node_1.cpu} > 80  │编辑│ │
│ └─────────────────────┴────┘ │
│                              │
│ 引用变量:                    │
│ node_1.cpu  node_1.mem       │
└─────────────────────────────┘
```

## 表达式生成规则

结构化的条件行 → `${...}` 字符串生成：

```
单条件:
  {source: "node_1", field: "cpu", op: ">", value: "80"}
  → "${node_1.cpu} > 80"

多条件 AND:
  [{source: "node_1", field: "cpu", op: ">", value: "80"},
   {source: "node_1", field: "mem", op: "<", value: "50"}]
  → "${node_1.cpu} > 80 AND ${node_1.mem} < 50"

多条件 OR:
  [{source: "node_1", field: "_result", op: "==", value: "True"},
   {source: "node_2", field: "_result", op: "==", value: "False"}]
  → "${node_1._result} == True OR ${node_2._result} == False"

**限制：所有条件行使用同一逻辑运算符（全 AND 或全 OR）。**
不支持 AND/OR 混合分组（无括号优先级支持）。3+ 条件如 `A AND B OR C` 语义模糊，当前阶段不做。如果需要，用户可以将复杂条件合并到一个条件行中用 `regex` 运算符处理。
```

全局/项目/系统变量引用：

```
{source: "global", field: "env", op: "==", value: "prod"}
→ "${global.env} == prod"

{source: "_system", field: "timestamp", op: ">", value: "2026-06-01"}
→ "${_system.timestamp} > 2026-06-01"
```

字符串值自动加引号：

```
{source: "node_1", field: "stdout", op: "contains", value: "error"}
→ "${node_1.stdout} contains \"error\""
```

## 校验规则

### 前端校验（实时）

| 检查项 | 时机 | 说明 |
|--------|------|------|
| 变量引用 | 变量选择后 | 引用的 node_id 存在于画布中 |
| 字段存在 | 选择 field 后 | 字段名在 outputSchema 中 |
| 类型匹配 | 输入值后 | 数字字段值可解析为数字 |
| 表达式语法 | 实时 | `${...}` 括号匹配，无非法字符 |
| 引用完整 | 确定前 | conditionStruct → 字符串转换正确 |

### 后端校验（已有）

不新增。`bamboo_validator.py` 中的 `checkConditionRefs()` 和 `build_bamboo_pipeline()` 中的条件编译逻辑保持不变。

## 实现计划

### Phase 1: 基础设施（2 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| `extractOutputFields()` | `useGraphCanvas.ts` | 遍历 DAG 提取上游节点的输出字段 |
| `extractAvailableVariables()` | `useGraphCanvas.ts` | 合并节点输出 + 全局变量 + 项目变量 + 系统变量 |
| `updateEdgeCondition()` | `useGraphCanvas.ts` | 结构化条件 → condition 字符串 → 写入 edge.data |
| `generateConditionExpr()` | `useGraphCanvas.ts` | rules[] + logic → `${...}` 表达式 |
| `validateConditionExpr()` | `useGraphCanvas.ts` | 实时校验表达式合法性 |

### Phase 2: VariablePicker 组件（1 天）

| 任务 | 说明 |
|------|------|
| 创建 `VariablePicker.vue` | 分组 el-select + 搜索过滤 |
| 接入 `extractAvailableVariables()` | 数据源对接 |
| 类型标注显示 | 每个选项显示 `(number)`/`(string)`/`(boolean)` |

### Phase 3: ConditionDialog 组件（2 天）

| 任务 | 说明 |
|------|------|
| 创建 `ConditionDialog.vue` | 弹窗框架 + 条件行列表 |
| 创建 `ConditionRow.vue` | 单行：变量选择器 + 运算符 + 值输入 |
| AND/OR 逻辑切换 | 行间连接按钮 |
| 表达式实时预览 | rules 变化时自动生成 `${...}` |
| 校验提示 | 实时显示通过/错误 |

### Phase 4: PropertyPanel 集成（1 天）

| 任务 | 说明 |
|------|------|
| 替换文本区域 | 改为只读预览 + 编辑按钮 |
| 引用变量标签 | 显示当前条件引用的变量列表 |
| 编辑按钮 → ConditionDialog | 打开弹窗并回填已有条件 |

### Phase 5: 校验 + 边标签优化（1 天）

| 任务 | 说明 |
|------|------|
| 画布边标签显示 | 显示表达式摘要而非 "custom" |
| 保存模板前校验 | 校验所有自定义条件的合法性 |

## 文件清单

### 新增

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/opsflow/components/ConditionDialog.vue` | 条件编辑器弹窗 |
| `web/src/views/apps/opsflow/components/ConditionRow.vue` | 单条件行 |
| `web/src/views/apps/opsflow/components/VariablePicker.vue` | 变量选择器 |

### 修改

| 文件 | 修改内容 |
|------|----------|
| `web/src/views/apps/opsflow/components/PropertyPanel.vue` | 边选中态条件区域：文本框 → 只读预览 + 编辑按钮 |
| `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | 新增 4 个方法（extractOutputFields, extractAvailableVariables, updateEdgeCondition, generateConditionExpr） |
| `web/src/views/apps/opsflow/composables/useGraphValidator.ts` | 增强 checkConditionRefs 校验 |
| `web/src/views/apps/opsflow/utils/shapes.ts` | 导出 outputSchemaMap 供变量选择器读取 |
| `web/src/views/apps/opsflow/stores/opsflowStore.ts` | 可选：存储可用变量列表的缓存 |

### 后端无改动

| 文件 | 理由 |
|------|------|
| `backend/opsflow/core/pipeline_builder/` | 条件字符串格式不变，编译逻辑不变 |
| `backend/opsflow/core/bamboo_validator.py` | 校验逻辑不变 |
| `backend/opsflow/serializers.py` | 序列化格式不变 |
| 所有其他后端文件 | 不涉及 |

## 不做的内容

- 不在 Pinia 中维护条件编辑的中间状态（条件直接读写 X6 edge.data）
- 不添加画布上的内联条件编辑（双击边标签编辑）
- 不添加条件模板/预设（如 "磁盘 > 80%" 快捷按钮）
- 不修改后端条件表达式语法或编译逻辑
- 不和变更现有连线交互（edge:connected 的 ElMessageBox 保留不动）
