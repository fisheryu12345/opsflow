# AsyncSelect 支持清空选中项

> 提交: ec4bb162 | 日期: 2026-06-28
> 涉及 App: opsflow
> 类型: 修复

---

## 问题

RenderForm 中 `async_select` 类型的字段（如"实例"下拉）选中后无法清除。`el-select` 的 `clearable` 属性默认为 `false`，且插件的表单配置未显式传 `clearable: true`。

## 修复

**文件:** `web/src/components/RenderForm/tags/TagAsyncSelect.vue`

```vue
<!-- 修复前 -->
clearable: false,

<!-- 修复后 -->
clearable: true,
```

默认启用清除按钮（×），用户可随时清空已选值。
