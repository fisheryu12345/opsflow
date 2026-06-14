# PropertyPanel Output Parameters 拆分为独立组件

> 提交: 7b2481de | 日期: 2026-06-14
> 类型: 重构

---

## 动机

`PropertyPanel.vue` 行数达到 839 行(超 500 行规范)，其中 Output Parameters 区块与面板核心逻辑耦合紧密，包含独立的数据展示和 Promote 操作。

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `PropertyPanel.vue` | inline template + 3 个函数 + CSS | `<OutputParamSection>` 组件引用，~70 行缩减 |
| `OutputParamSection.vue` | 不存在 | 新文件 97 行，完整独立的输出参数区块 |

### 代码对比

**重构前** — 内联在 PropertyPanel 中：
```vue
<div class="panel-section" v-if="isAtom && outputSchema.length">
  <div class="section-title">{{ $t("message.properties.outputParams") }}</div>
  <div v-for="out in outputSchema" ...>
    ...
    <el-button @click="promoteOutput(out)">Promote</el-button>
  </div>
</div>

<script>
function outputTypeTag(type) { ... }
function copyRef(ref) { ... }
async function promoteOutput(out) { ... }
</script>
```

**重构后** — 独立组件：
```vue
<OutputParamSection
  v-if="isAtom"
  :schema="outputSchema"
  :node-id="form.id || ''"
  :template-id="templateId"
/>
```

### 设计决策

- **interface 最小化**：只暴露 `schema`(输出字段定义)、`nodeId`(引用前缀)、`templateId`(Hook API) 三个 prop
- **CSS 自包含**：scoped style 确保不影响全局
- **逻辑独立**：`outputTypeTag`/`copyRef`/`promoteOutput` 移至新组件，不依赖父组件 form 状态

### 关联文档

- 相关调试记录: [node-output-variable-fixes.md](debug/2026-06-14-node-output-variable-fixes.md)
