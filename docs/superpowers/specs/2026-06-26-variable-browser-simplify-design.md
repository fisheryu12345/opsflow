# VariableBrowser 简化 — 设计文档

> 日期: 2026-06-26 | 类型: 重构 | 涉及 App: opsflow

---

## 目标

1. VariableBrowser：移除手动 Add 和 Drawer 编辑功能，变为纯浏览 + 插入引用
2. 点击变量显示只读信息卡，引导用户去 GlobalVariablePanel 编辑
3. 信息卡展示完整的 meta 数据（apiEndpoint / dependsOn / options 等）

## 设计

### VariableBrowser 改动

**移除：**
- Add 按钮（`openAddDialog`）
- 整个 Drawer（包含 Key/Type/Value/Desc 编辑表单 + Save/Delete/Unhook）
- 所有 CRUD 函数（`openAddDialog`, `onSave`, `onDelete`, `onUnhook`, `selectVar`）
- 相关的 state：`detailVisible`, `editKey`, `editForm`

**新增：**
- 每个变量可展开/收起的内联只读信息卡
- `expandedVar` ref，跟踪当前展开的变量 key
- 信息卡内容：Type / Value / Desc / Source / Meta / Reference count
- 「Edit in Variable Panel →」按钮
- `editVariable` emit 事件

**信息卡模板（只读）：**

```vue
<div v-if="expandedVar === v.key" class="var-detail">
  <div class="detail-row"><span>Type</span><span>{{ v.type }}</span></div>
  <div class="detail-row"><span>Value</span><span>{{ v.value }}</span></div>
  <div class="detail-row"><span>Desc</span><span>{{ v.description || '-' }}</span></div>
  <div class="detail-row"><span>Source</span><span>{{ sourceLabel(v.source_type) }}</span></div>
  <div class="detail-row" v-if="v.meta?.apiEndpoint">
    <span>API</span><code>{{ v.meta.apiEndpoint }}</code>
  </div>
  <div class="detail-row" v-if="v.meta?.dependsOn">
    <span>Depends</span><span>{{ v.meta.dependsOn }}</span>
  </div>
  <div class="detail-row" v-if="v.meta?.options?.length">
    <span>Options</span><span>{{ v.meta.options.length }} items</span>
  </div>
  <el-button size="small" type="primary" text @click="emit('editVariable', v.key)">
    Edit in Variable Panel →
  </el-button>
</div>
```

**交互：**
- 点击变量 → toggle `expandedVar`
- 点击「Edit in Variable Panel」→ emit('editVariable', key) → 关闭 dialog

### GlobalVariablePanel 改动

**新增：**
- `selectedKey` prop：外部指定要选中的变量 key
- 或者新增 `openVariable(key)` 方法，通过 defineExpose 暴露给父组件
- watch `selectedKey`，变化时自动调用 `selectVar()`

### 父组件（DesignCanvas / index.vue）改动

**接收 VariableBrowser 的 `editVariable` 事件：**
```vue
<VariableBrowser @edit-variable="onEditVariable" />
```

**处理函数：**
```typescript
function onEditVariable(key: string) {
  // 关闭 VariableBrowser，触发 GlobalVariablePanel 选中该变量
  gvPanelRef.value?.openVariable(key)
}
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/.../VariableBrowser.vue` | 移除 Add + Drawer，新增信息卡 + editVariable emit |
| `web/.../GlobalVariablePanel.vue` | 新增 selectedKey prop / openVariable expose |
| `web/.../DesignCanvas.vue` | 连接两个面板的 editVariable 事件 |

## 验证

1. VariableBrowser 打开 → 不再显示 Add 按钮
2. 点击变量 → 显示只读信息卡（含 Type/Value/Desc/Source/Meta）
3. 信息卡显示 async_select 的 apiEndpoint / dependsOn
4. 信息卡显示 select 的 options 数量
5. 点击「Edit in Variable Panel」→ VariableBrowser 关闭 → GlobalVariablePanel 打开并选中该变量
6. Insert 按钮功能不受影响
