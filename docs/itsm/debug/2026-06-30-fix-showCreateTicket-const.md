# ITSM showCreateTicket const ref 赋值错误

> 提交: 80f9ed95 | 日期: 2026-06-30
> 涉及 App: itsm
> 类型: Bug 修复

---

## 问题

`web/src/views/apps/itsm/index.vue` 中 `onOpenCreateTicket` 函数内，`showCreateTicket` 通过 `const showCreateTicket = ref(false)` 声明为常量。在 `<script>` 中直接赋值 `showCreateTicket = true` 会触发 `TypeError: Assignment to constant variable`。

浏览器控制台报错:
```
Uncaught TypeError: Assignment to constant variable.
    at onOpenCreateTicket (index.vue:172:24)
```

## 修复

**文件:** `web/src/views/apps/itsm/index.vue:645`

```ts
// 修复前 — 错误: 直接对 const ref 赋值
function onOpenCreateTicket() {
  if (!categoryOptions.value.length) loadCategories()
  showCreateTicket = true    // ❌ TypeError
}

// 修复后 — 正确: 通过 .value 修改 ref 内部值
function onOpenCreateTicket() {
  if (!categoryOptions.value.length) loadCategories()
  showCreateTicket.value = true  // ✅
}
```

## 原因

Vue 3 的 `ref()` 返回一个响应式对象。在 `<template>` 中的内联表达式（如 `@click="showCreateTicket = false"`）Vue 模板编译器会自动解包 ref，所以写法正确。但在 `<script setup>` 的 JavaScript 代码中，`ref` 不会自动解包，必须通过 `.value` 访问和修改。

## 影响范围

- 影响操作: ITSM 页面"我的工单"和"事件工单"两个 tab 中的"新建工单"按钮
- 用户影响: 点击按钮无响应，控制台报错
- 修复后: 正常弹出创建工单对话框
