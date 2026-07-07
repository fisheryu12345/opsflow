# ITSM Hero 搜索框 Teleport

> 提交: f1179192 | 日期: 2026-07-07
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

ITSM 的 Service Market 和 Service Admin 两个 Tab 各自的搜索框原本在 body 内，与 OPSflow 的 Project/Execution Tab 形成视觉不一致。用户期望搜索框出现在 Hero 暗色区域，与标题和统计项在同一行。

## 实现方案

### 核心架构

利用 `useHeroProvider`/`useHeroConsumer` 的 `searchRef` Teleport 机制：

```
itsm/index.vue（父页面）
  └─ useHeroProvider() → searchRef → <div ref="heroSearchRef" class="itsm-hero-search" />
       │
       ├── ServiceMarket.vue
       │     └─ useHeroConsumer() → searchEl
       │           └─ <Teleport v-if="active && searchEl" :to="searchEl">
       │                 <el-input v-model="searchQuery" class="sm-search-input" />
       │               </Teleport>
       │
       └── ServiceAdmin.vue
             └─ useHeroConsumer() → searchEl
                   └─ <Teleport v-if="active && searchEl" :to="searchEl">
                         <el-input v-model="searchQuery" class="sa-search-input" />
                       </Teleport>
```

### 关键代码

**父页面 Hero 模板添加 Teleport 接收槽位：**
```html
<div class="itsm-hero-inner">
  <div class="itsm-hero-left">...</div>
  <div ref="heroSearchRef" class="itsm-hero-search" />   <!-- 搜索框目标 -->
  <div class="itsm-hero-stats">...</div>
</div>
```

**Hero CSS — glass effect 统一处理：**
```scss
.itsm-hero-search {
  margin-left: auto; margin-right: 20px;
  display: flex; align-items: center;
  :deep(.sm-search-input),
  :deep(.sa-search-input) { width: 280px; }
  :deep(.el-input__wrapper) {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
  }
  :deep(.el-input__inner) { color: #fff; }
  :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
}
```

**子组件 Teleport 守卫：**
```html
<Teleport v-if="active && searchEl" :to="searchEl">
  <el-input v-model="searchQuery" :placeholder="..." size="default" class="sm-search-input" />
</Teleport>
```

`v-if="active && searchEl"` 双重守卫：
- `active` — 防止多 Tab 的 Teleport 同时写入同一 DOM 节点
- `searchEl` — 防止父页面 DOM 未挂载时 Teleport 报错

### 设计决策

- **为什么两个搜索框共享一个 `heroSearchRef`** — Hero 同一时刻只显示一个 Tab 的搜索框，`active` prop 保证只有一个 Teleport 激活
- **为什么用 `:deep()` 而非组件内 style** — Teleport 将 DOM 移动到父页面，但 scoped style 的 `data-v-xxx` 属性随元素移动。`:deep()` 确保 Hero CSS 能覆盖 Teleported 元素的 input wrapper 样式
- **为什么搜索框 size 从 `large`/`small` 改为 `default`** — Hero 区高度有限，统一 `default` size 与 OPSflow Hero 搜索框一致

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/itsm/index.vue` | 添加 `heroSearchRef` Teleport 目标 + CSS |
| `web/src/views/apps/itsm/catalog/ServiceMarket.vue` | 搜索框 Teleport + `active` prop |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 同上 |

### 关联文档

- 相关架构文档: [2026-07-07-unified-hero-communication-refactor.md](../../opsflow/architecture/2026-07-07-unified-hero-communication-refactor.md)
- 相关架构文档: [2026-07-07-tab-lazy-loading-refactor.md](../architecture/2026-07-07-tab-lazy-loading-refactor.md)
