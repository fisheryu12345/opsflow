# 全线 App Hero-tab 左对齐修复

> 最后更新: 2026-07-05

---

## 1. 背景与现象

用户反馈所有 App（ITSM、OpsFlow、IAM、OpsAgent、CMDB 等）的 hero 区域中，tab 文字起点与上方的标题/副标题没有对齐——tab 内容整体偏右。

**现象对比（修复前）：**
- `hero-inner` 内标题 "ITSM" 起点 = `padding-left: 24px`
- `hero-tabs` 容器起点 = `padding-left: 24px`（正确，与标题对齐）
- 但每个 `hero-tab` 自身的 `padding: 10px 20px` 或 `padding: 10px 16px` 中的 `padding-left` 导致 tab 内容额外缩进 16-20px
- 最终效果：第一个 tab 的图标/文字从 24+20=44px（或 40px）开始，比标题的 24px 偏移了 16-20px

## 2. 排查思路

### 2.1 初步分析

从 ITSM app 的用户反馈入手，检查 `index.vue` 中 hero 区域的 CSS 结构：

```scss
.itsm-hero-inner { padding: 14px 24px; }        // 标题从 24px 开始
.itsm-hero-tabs { padding: 0 24px; }             // tabs 容器从 24px 开始
.itsm-hero-tab  { padding: 10px 20px; }          // tab 内容从 24+20=44px 开始 ❌
```

### 2.2 全面扫描

发现这是一个全项目共性问题，需要在所有 app 中统一修复。

排查了以下所有包含 hero-tab 的 app 文件：
- `web/src/styles/_mixins.scss` — 全局 mixin `g-hero-tab`
- `web/src/views/apps/itsm/index.vue`
- `web/src/views/apps/opsflow/index.vue`
- `web/src/views/apps/opsagent/index.vue`
- `web/src/views/apps/cmdb/index.vue`
- `web/src/views/apps/iam/index.vue`
- `web/src/views/apps/integration/index.vue`
- `web/src/views/apps/job-platform/index.vue`
- `web/src/views/apps/open-api/index.vue`

## 3. 根因分析

**根因：** 全局 `g-hero-tab` mixin 定义了 `padding: 10px 16px`，其中 `padding-left` 导致 tab 内容相对于父容器（`g-hero-tabs`，`padding: 0 24px`）额外偏移。父容器的 `padding-left: 24px` 已经与 `hero-inner` 对齐，因此 tab 自身不应再添加左侧 padding。

```
hero-inner  padding: 14px 24px
           ┌─────────────────────────────────────┐
           │  ITSM                                │  ← 标题起点 = 24px
           └─────────────────────────────────────┘
hero-tabs  padding: 0 24px
           ┌─────────────────────────────────────┐
           │  [tab1] [tab2] [tab3]               │
           └─────────────────────────────────────┘
                        ↑
              tab padding-left: 16px 导致偏移
              tab 内容实际起点 = 24+16 = 40px ❌
```

**为什么历史问题没有被发现：** 之前 `iam` app 使用了一个临时 hack（`:first-child { padding-left: 0 }`）来修复第一个 tab，但其他 app 没有，而且该方案也没有在全局 mixin 中落地。

## 4. 解决方案

### 核心方案

所有 hero-tab 的 `padding-left` 统一移除。tabs 容器自身的 `padding-left` 足以让内容与标题对齐。

### 4.1 全局 mixin `web/src/styles/_mixins.scss`

```scss
// 修复前
@mixin g-hero-tab {
  padding: 10px 16px;  // ← left: 16px 导致偏移
}

// 修复后
@mixin g-hero-tab {
  padding: 10px 16px 10px 0;  // left: 0，与容器对齐
}
```

### 4.2 各 app index.vue 文件（共 7 处）

每个文件都修复了 hero-tab 的 `padding`，移除左侧 padding：

| 文件 | 修复前 | 修复后 |
|------|--------|--------|
| `web/src/views/apps/cmdb/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/iam/index.vue` | `padding: 10px 16px` | `padding: 10px 16px 10px 0` |
| `web/src/views/apps/integration/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/itsm/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/job-platform/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/open-api/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/opsagent/index.vue` | `padding: 10px 20px` | `padding: 10px 20px 10px 0` |
| `web/src/views/apps/opsflow/index.vue` | `padding: 10px 16px` | `padding: 10px 16px 10px 0` |

### 4.3 IAM 移除旧 hack

`web/src/views/apps/iam/index.vue` 中原有的 `:first-child { padding-left: 0 }` 不再需要，因为所有 tab 都已无 left-padding，该规则已移除。

### 4.4 ITSM Tab 排序优化

同时调整了 ITSM 的 tab 顺序，将"服务市场"设为默认首页：

```python
# 排序变化
sort: 10  service-market  ← 新设为默认 (is_default=True)
sort: 20  tickets
sort: 30  dashboard
sort: 40  workflows
sort: 50  service-admin
sort: 60  sla
...
sort:120  incidents  ← 下移（低频率）
sort:130  changes    ← 下移（低频率）
```

对应文件 `backend/iam/management/commands/seed_iam_page_configs.py`，并执行 Python 脚本更新了数据库中的 `PageTab` 记录。

### 4.5 规范更新

`docs/guides/frontend-style-guide.md` 新增约束规则 #5：

> **tab 内容左对齐** — `g-hero-tab` mixin 使用 `padding: 10px 16px 10px 0`（无左侧 padding），禁止给 hero-tab 加左侧 padding。

## 5. 引入的方法 / 函数 / 设计模式

无新增函数或设计模式，仅 CSS 属性修正。

## 6. 验证

1. 浏览器刷新后所有 app hero-tab 内容与标题视觉左对齐
2. tab 之间的间距保持正常（通过 `gap: 6px` 和 `padding-right` 维持）
3. IAM 的 `:first-child` hack 移除后无回归（因为所有 tab 统一了 `padding-left: 0`）
4. seed 命令执行成功，数据库记录已更新

## 7. 涉及文件清单

- `web/src/styles/_mixins.scss` — 全局 `g-hero-tab` mixin padding 修复
- `web/src/views/apps/cmdb/index.vue` — hero-tab padding 修复
- `web/src/views/apps/iam/index.vue` — hero-tab padding 修复 + 移除旧 hack
- `web/src/views/apps/integration/index.vue` — hero-tab padding 修复
- `web/src/views/apps/itsm/index.vue` — hero-tab padding 修复
- `web/src/views/apps/job-platform/index.vue` — hero-tab padding 修复
- `web/src/views/apps/open-api/index.vue` — hero-tab padding 修复
- `web/src/views/apps/opsagent/index.vue` — hero-tab padding 修复
- `web/src/views/apps/opsflow/index.vue` — hero-tab padding 修复
- `backend/iam/management/commands/seed_iam_page_configs.py` — ITSM tab 排序优化
- `docs/guides/frontend-style-guide.md` — 新增约束规则 #5
