# Loop Config i18n + 滑块点击修复

> 提交: a5cff5d3 | 日期: 2026-06-28
> 涉及 App: opsflow
> 类型: 修复

---

## 问题

### Bug 1: Switch 滑块点击无响应（事件冒泡双重触发）

PropertyPanel 的 Loop Configuration 标题行中，`el-switch` 包裹在父 `<div @click="loopEnabled = !loopEnabled">` 内：

```html
<div @click="loopEnabled = !loopEnabled">
  <el-switch v-model="loopEnabled" />
  Loop Configuration
</div>
```

点击滑块时发生了两次翻转：
1. `el-switch` 的 `v-model` 将 `loopEnabled` 设为 `true`
2. 事件冒泡到父 `div`，`@click` 又将 `loopEnabled` 翻转为 `false`

结果：两次翻转抵消，滑块状态不变。点击文字则只触发一次，正常。

### Bug 2: 硬编码英文标签未走 i18n

5 处标签、2 处 placeholder、2 个 raido 选项为硬编码英文：
`Loop Configuration`、`Max Iterations`、`Loop Variable`、`Select parameter...`、`Values`、`comma,separated,values`、`On Failure`、`Fail`、`Skip`

## 修复

### 方案

1. 父 `div` 移除 `@click`，改为在文字上使用 `<span @click.stop>` 控制
2. 所有硬编码标签替换为 `$t()` 调用，新增 9 个 i18n 键

### 关键代码

```vue
<!-- 修复前：事件冒泡导致双重触发 -->
<div class="section-title" @click="loopEnabled = !loopEnabled">
  <el-switch v-model="loopEnabled" />
  Loop Configuration
</div>

<!-- 修复后：滑块只受 v-model 控制，文字单独 @click.stop -->
<div class="section-title">
  <el-switch v-model="loopEnabled" />
  <span @click.stop="loopEnabled = !loopEnabled">{{ $t("message.properties.loopConfig") }}</span>
</div>
```

### 新增 i18n 键

| 键 | 英文 | 中文 |
|-----|------|------|
| `loopConfig` | Loop Configuration | 循环配置 |
| `maxIterations` | Max Iterations | 最大循环次数 |
| `loopVariable` | Loop Variable | 循环变量 |
| `loopValues` | Values | 取值列表 |
| `loopValuesPlaceholder` | comma,separated,values | 逗号,分隔,取值 |
| `onFailure` | On Failure | 失败处理 |
| `fail` | Fail | 终止 |
| `skip` | Skip | 跳过 |
| `selectParameter` | Select parameter... | 选择参数... |

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 修复事件冒泡 bug + i18n 替换 |
| `web/src/i18n/pages/opsflow/en.ts` | 新增 9 个 i18n 英文键 |
| `web/src/i18n/pages/opsflow/zh-cn.ts` | 新增 9 个 i18n 中文键 |
