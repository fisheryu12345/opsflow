# OPSflow Style Guide

All OPSflow Vue components should follow these conventions for visual consistency.

**后续向导对话框参考:** `SubmitWizardDialog.vue` — 多步骤弹窗的 HTML/SCSS/动画标准实现。

### SCSS

**唯一入口：** `@use 'styles/global' as *;`
```scss
<style lang="scss" scoped>
@use 'styles/global' as *;
</style>
```

**设计令牌 — 使用 `$g-*` 变量，禁止硬编码颜色/阴影/圆角**

| 常用变量 | 值 | 用途 |
|----------|-----|------|
| `$g-bg-page` | `#f0f2f5` | 页面背景 |
| `$g-color-primary` | `#409EFF` | Element 蓝色主色 |
| `$g-text-primary` | `#303133` | 主文字色 |
| `$g-text-secondary` | `#666` | 次要文字色 |
| `$g-text-muted` | `#909399` | 辅助文字/placeholder |
| `$g-border-light` | `#ebeef5` | 浅边框（分割线） |
| `$g-border-card` | `#f0f0f0` | 卡片边框 |
| `$g-radius` | `10px` | 卡片/大圆角 |
| `$g-radius-sm` | `8px` | 小组件圆角 |
| `$g-shadow-card` | `0 1px 4px rgba(0,0,0,0.06)` | 卡片阴影 |
| `$g-shadow-hover` | `0 4px 12px rgba(0,0,0,0.08)` | 悬浮阴影 |
| `$g-bg-header` | `#f5f7fa` | 表格列头背景 |
| `$g-bg-success` | `#f0f9eb` | 成功背景 |
| `$g-bg-warning` | `#fdf6ec` | 警告背景 |
| `$g-bg-danger` | `#fef0f0` | 危险背景 |
| `$g-bg-light-blue` | `#ecf5ff` | 浅蓝色背景 |

**完整变量表见** `web/src/styles/_tokens.scss`

**通用 class — 使用 `.g-*` 前缀**

| class | 用途 |
|-------|------|
| `.g-card` | 标准卡片容器（背景白、圆角、阴影） |
| `.g-card-header` | 卡片标题栏（带下分割线） |
| `.g-card-body` | 卡片内容区（内边距） |
| `.g-fade-in-up` | 入场动画（淡入上移） |
| `.g-stagger-item` | 列表交错动画 |
| `.g-status-tag` | 状态标签（active/inactive/pending） |

**Mixin — `@include g-*`**

| mixin | 用途 |
|-------|------|
| `g-hover-lift` | 悬浮上移 + 阴影加深 |
| `g-hover-shift` | 悬浮右移 |
| `g-dialog-header` | 弹窗标题栏样式 |
| `g-dialog-body` | 弹窗内容区内边距 |
| `g-dialog-footer` | 弹窗底部按钮区 |
| `g-icon-circle` | 渐变图标圆形背景 |
| `g-section-header` | 区块标题栏 |

**Dialog 规范：** 添加 class `opsflow-dialog`（header/body/footer 自动样式化）

### Vue 组件结构规范

所有 `.vue` 文件**必须**遵循以下三段式结构：

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts" name="componentName">
// 脚本内容
</script>

<style scoped lang="scss">
// 样式内容
</style>
```

**规则：**

| # | 规则 | 说明 |
|---|------|------|
| 1 | **三段式顺序** | `<template>` → `<script setup>` → `<style scoped>`，禁止调换 |
| 2 | **name 属性** | `<script setup name="xxx">` 必须写 name，PascalCase（如 `DeptTreeCom`） |
| 3 | **script setup 优先** | 禁止使用 Options API（`export default { ... }`），统一 Composition API |
| 4 | **scoped 样式** | `<style>` 必须加 `scoped`，除非是全局覆写 |
| 5 | **lang="scss"** | 所有 `<style>` 使用 SCSS，禁止原始 CSS |
| 6 | **私有 class** | 组件内样式 class 以组件缩写为前缀（如 `.dtc-wrap`、`.msg-toolbar`），避免全局污染 |

**关于 `shallowRef` 和 `markRaw`：**
- 图标组件对象（如 `User`、`Male`、`Tickets`）放入 reactive container 时，必须用 `markRaw()` 包裹，避免 Vue 对 Component 对象做深层响应式代理。
- 当 ref 的值只关心整体替换（不关心深层属性变化）时，优先用 `shallowRef` 替代 `ref` 提升性能。

### 前端注释规范

**注释是解释"为什么"，不是"是什么"。**

| # | 规则 | ✅ 正确示例 | ❌ 错误示例 |
|---|------|------------|------------|
| 1 | 组件顶部写一句话职责说明 | `<!-- 部门树组件：懒加载、拖拽排序 -->` | 不写注释 |
| 2 | 非自明的逻辑写"为什么" | `// 先重置再 fetch，避免竞态` | `// 获取列表` |
| 3 | 复杂 API 调用写预期行为 | `// 返回 { code, data, total }，data 可能为 null` | 不写注释 |
| 4 | 信号/事件/发布订阅写触发条件 | `// 节点完成时触发，pipeline_builder 监听此信号` | `// 发送信号` |
| 5 | 禁止废话注释 | — | `// 设置变量`、`// 循环` |
| 6 | 中英双语可选 | 复杂的业务逻辑用中文，纯技术说明用英文 | — |
| 7 | CSS hack 必须注释 | `// 覆盖 el-table 默认内边距` | 裸 hack 代码 |

**关键原则：** 好的代码本身就能说明"是什么"——注释的唯一价值是解释代码无法表达的上下文、约束和缘由。

### Key Files
- `web/src/styles/_tokens.scss` — design tokens (`$g-*` 变量)
- `web/src/styles/_mixins.scss` — reusable mixins
- `web/src/styles/_components.scss` — reusable classes (`.g-*`)
- `web/src/styles/global.scss` — 唯一入口（forward 以上三个文件）

### 设计文档管理规则
所有通过 Superpowers 或其他 AI 工具生成的设计文档（架构设计、功能设计、详细设计等），**必须**遵守以下规则：

1. **保存路径**：统一保存到 `docs/opsflow/plans/` 目录下
2. **文档格式**：`.md`（Markdown）格式
3. **文件命名**：`YYYY-MM-DD-<简短英文描述>.md`（如 `2026-06-03-gateway-condition-editor-design.md`）
4. **适用范围**：包括但不限于 Superpowers、SPARC 流程、Claude Code、以及其他 AI Agent 产出的设计文档

### 顶层设计约束

所有设计文档（功能设计、详细设计等）和开发工作，**必须**遵守以下约束：

1. **顶层设计优先** — `docs/opsflow_target.md` 定义了 OPSflow 平台的最终目标架构、子产品定位和组件交互规范。任何功能设计或开发必须以此为准绳。
2. **冲突解决流程** — 若开发过程中发现与 `docs/opsflow_target.md` 的顶层设计存在冲突或疑问，**必须先进行头脑风暴讨论明确定案，方可改动**。不得在不经讨论的情况下偏离顶层设计。
3. **设计文档引用** — 所有 `docs/opsflow/plans/` 下的设计文档必须引用本文件作为架构依据，并在设计评审时对照 `docs/opsflow_target.md` 校验一致性。

### 项目结构规范

#### 目录职责

| 目录 | 职责 |
|------|------|
| `backend/` | Django 后端（dvaadmin，application，opsflow，cmdb，itsm 等所有 Django app） |
| `web/` | Vue 3 前端 |
| `refrence/` | 第三方蓝鲸参考源码（只读，不修改） |
| `docs/` | 统一文档，按 Django app 分子目录（opsflow/、cmdb/、itsm/ 等） |
| `deploy/` | 部署配置（docker compose、nginx、Dockerfile） |
| `scripts/` | 全局脚本（数据库维护、CI/CD、环境初始化） |
| `.claude/skills/` | 项目级 Claude 技能 |

**不允许在根目录创建新的顶层目录或文件。** 所有新增内容必须归入以上已有目录。

#### 后端 App 规范

每个 Django app（opsflow，cmdb，itsm，monitor，opsagent 等）内部统一使用以下目录结构：

```
opsflow/
├── models/           # 数据模型
├── views/            # API 视图
├── services/         # 业务逻辑层
├── signals/          # 信号处理（如果存在）
├── tests/            # 测试
├── migrations/
├── serializers.py
├── urls.py
└── apps.py
```

- `dvadmin/` 和 `application/` 保持原名，不改动
- 命名规范：app 名全小写，下划线分隔

#### 后端模块分层规范

每个 Django app 内部按 **views → services → models** 三层分层，职责单向依赖：

```
请求 → views（参数校验 + 序列化）→ services（业务逻辑）→ models（数据访问）
                        ↕ (可选，异步)
                     signals（事件通知）
```

| 层 | 职责 | 允许做的事 | 禁止做的事 |
|----|------|-----------|-----------|
| **views** | 参数校验、权限检查、调用 services、序列化输出 | 调 services、调 serializer、校验 request.data | 直接操作 model、写业务逻辑、触发 signal |
| **services** | 业务编排、跨 model 协调、事务管理、触发 signal | 调 models、触发 signal、管理事务 `atomic()` | 直接返回 `Response`、调另一个 services（用 signal 解耦） |
| **models** | 数据访问、属性计算、简单验证 | 定义字段、`property`、`clean()`、`classmethod` 查询 | 调 services、触发 signal、引用 views |
| **signals** | 异步解耦（如缓存更新、WebSocket 推送、日志记录） | 收 signal 后执行副作用 | 返回数据给发送方、修改触发方状态 |

**例外情况：** 对极其简单的 CRUD（一个 model + 一个 viewset），可以跳过 services 层，views 直接调 models。但一旦涉及多数据源、跨表事务、或第三方 API，就必须引入 services。

#### 后端 API 命名规范

| # | 规则 | 说明 |
|---|------|------|
| 1 | **RESTful 资源路径** | URL 用**复数名词**表示资源，如 `/api/system/users/`、`/api/opsflow/templates/`。避免 URL 中出现动词（如 `/all_dept/` 应为 `/depts/`） |
| 2 | **HTTP Method 表达操作** | GET=查询、POST=创建、PUT/PATCH=更新、DELETE=删除。不要在 GET 路径中加 `create_` 或 `delete_` |
| 3 | **viewset 优先** | 优先使用 DRF `ModelViewSet`，配合 `router.register()`。只有非 CRUD 操作才使用 `APIView` + 自定义 URL |
| 4 | **查询参数命名** | `snake_case`，如 `?page=1&limit=20&search=foo` |
| 5 | **自定义动作** | 对 `ViewSet` 中的非 CRUD 动作，用 `@action(detail=True, methods=['post'])` 装饰器 |

#### 错误处理规范

| 层 | 规范 | 说明 |
|----|------|------|
| **前端 catch** | `warningNotification()` / `ElMessage.error()` | 所有 `try-catch` 必须向用户展示反馈，禁止空 catch 或仅 `console.error()` |
| **前端 API 调用** | `ElMessage.success(msg || '操作成功')` | 成功后统一使用 `successMessage()` / `successNotification()` |
| **后端视图** | 抛异常，不要返回 `ErrorResponse` | 继承 `APIException`，由 DRF exception handler 统一处理。仅在**确实需要返回特定 HTTP status** 时用 `ErrorResponse` |
| **后端服务层** | 抛自定义 Exception | 在 `services/` 层中抛 `Raise(APIException)`，不要在 services 里 return `ErrorResponse` |
| **全局异常** | `application/exception.py` | 所有未捕获异常统一走配置文件中的 `EXCEPTION_HANDLER`，确保返回 `{"code": 5000, "msg": ...}` 格式 |

#### 前端规范

- `views/` 下按 app 分目录（`opsflow/`，`system/`，`cmdb/` 等）
- `views/apps/opsflow/components/` 下按功能拆分子目录（`canvas/`，`dialogs/`，`panels/` 等）
- 组件使用 PascalCase 命名（如 `DesignCanvas.vue`）
- 新增 opsflow 独立页面必须在 `views/apps/opsflow-*/` 下创建独立目录

### TypeScript 类型规范

**禁止滥用 `any`。** 所有跨组件/跨模块的数据接口必须定义明确类型。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **Props 接口** | 组件 Props 必须在 `<script setup>` 上方用 `interface` 定义，配合 `defineProps<Props>()` 使用 |
| 2 | **API 响应类型** | 每个 api.ts 必须导出对应实体类型，禁止 inline 声明 `res.data as any` |
| 3 | **ref 泛型** | `ref()` 必须加泛型（如 `ref<UserRecord[]>([])`），禁止裸 `ref([])` 或 `ref<any[]>([])` |
| 4 | **computed 类型** | 复杂 computed 必须显式标注返回类型 |
| 5 | **emit 类型** | `defineEmits<{ (e: 'eventName', payload: Type): void }>()`，禁止不加类型 |
| 6 | **后端序列化器** | DRF Serializer 必须对应 `data`、`results` 等字段定义明确的 `serializers.py` 输出类型 |

### 国际化规范（i18n First）

**所有新页面、新组件、新对话框，从第一行代码开始就必须使用 i18n，禁止硬编码中文。**

| # | 规则 | 说明 |
|---|------|------|
| 1 | **先写翻译键** | 新建页面时，先同时改 `web/src/i18n/lang/en.ts` 和 `zh-cn.ts`，加 `xxxPage` 命名空间段 |
| 2 | **模板用 `$t()`** | `{{ $t('message.pageName.key') }}`，禁止裸中文 |
| 3 | **脚本用 `t()`** | `t('message.pageName.key')`，从 `useI18n()` 取实例 |
| 4 | **不用字典 label 代替翻译** | `statusDict` 的 `item.label` 不会随语言切换，直接用 `$t` |
| 5 | **所有消息走 i18n** | `ElMessage`、`ElMessageBox.confirm`、`successMessage` 全要走翻译 |
| 6 | **动态参数用插值** | `t('xxx', { name: row.name })`，翻译文件用 `{name}` 占位 |

**Code Review 检查三样：** ① 翻译段有无添加到 en.ts/zh-cn.ts ② 模板有无裸中文 ③ 脚本有无裸中文

**命名规范：** `message.<pageName>.<camelCaseKey>`，如 `message.rolePage.statTotal`。

### 按钮使用规范（Button Style Guide）

所有 `el-button` **必须**遵循以下规范，确保全系统视觉统一：

| 场景 | size | type | icon | 示例 |
|------|------|------|------|------|
| 页面级操作（新增/创建/发布/保存） | `default` | `primary` | **必须** | `<el-button type="primary" :icon="Plus">新增</el-button>` |
| 工具栏次要（刷新/重置/导出） | `default` | 缺省 | **必须** | `<el-button :icon="Refresh">刷新</el-button>` |
| 搜索/查询 | `default` | `primary` | 无 | `<el-button type="primary">搜索</el-button>` |
| 表格行内操作（编辑/删除/查看） | `small` | `text` | 无 | `<el-button text size="small">编辑</el-button>` |
| 弹窗底部按钮 | `default` | 取消→缺省, 确认→`primary` | 无 | `<el-button @click="...">取消</el-button>` + `<el-button type="primary">确定</el-button>` |
| 树/图表区小操作 | `small` | `text` + `circle` | **必须** | `<el-button text circle :icon="Plus" size="small" />` |

**Icon 自动映射规则：**

| 按钮文本关键词 | Icon |
|---|---|
| 新增/添加/Add/Create | `Plus` |
| 编辑/Edit/Modify | `Edit` |
| 删除/Delete/Remove | `Delete` |
| 保存/Save | `Check` |
| 刷新/Refresh/Sync | `Refresh` |
| 发布/Publish/Deploy | `Promotion` / `Upload` |
| 导出/Export | `Download` |
| 导入/Import | `Upload` |
| 重置/Reset/Clear | `Refresh` |
| 查看/View/Detail | 无（行内操作，用 `text` 即可） |

**禁止项：**
- 禁止在弹窗底部按钮上使用 `size="small"`
- 禁止在表格行内使用 `type="primary" link` → 统一用 `text`
- 禁止 `text` 与 `type="primary"` 同时使用 → 去掉 `type="primary"`
- 禁止搜索按钮带图标

#### Skills 规范

- 所有 Claude 技能放在项目级 `.claude/skills/` 目录
- 新技能创建后立即放入项目级目录
- 保持用户级 `.claude/skills/` 与项目级同步（或项目级优先）

#### 其他规范

- 运行脚本放在 `scripts/`，后端内部脚本放在 `backend/tools/`
- 参考源码放在 `refrence/` 目录，内容通过 `.gitignore` 忽略
- 任何生成运行时目录（`logs/`，`media/`，`static/`）在 `.gitignore` 中声明

### Git 提交与分支规范

#### 分支策略

- **禁止直接在 `main` 分支上开发。** 新功能从 `main` 切 `feat/<short-desc>` 分支，修复从 `main` 切 `fix/<short-desc>` 分支
- 分支名全小写，中划线分隔，如 `feat/gateway-condition-editor`、`fix/node-output-display`
- 合并回 `main` 后删除远程分支

#### Commit Message 格式

```
<类型>: <英文概要> — <中文描述>

## Changes (中文)

- <文件>: <具体改动说明>
- <文件>: <具体改动说明>
```

| 类型 | 何时使用 |
|------|----------|
| `feat` | 新功能 |
| `fix` | 问题修复 |
| `refactor` | 重构（不改变外部行为） |
| `perf` | 性能优化 |
| `docs` | 文档 |
| `chore` | 配置/依赖/杂项 |
| `style` | 仅样式改动（CSS 非功能） |
| `revert` | 回退 |

**禁止项：** 不要添加 `Co-Authored-By` 尾部标记，除非团队明确要求。

### Pinia Store 规范

**哪些状态放 Store：** 只有**跨组件共享**或**跨路由持久**的数据才放 Pinia Store。组件私有状态保持 local `ref()`。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **store 文件路径** | 全局共享的 store 放 `stores/modules/`（如 `stores/modules/dept.ts`），页面私有 store 放 `stores/`（如 `stores/messageCenter.ts`） |
| 2 | **命名** | store 文件名 + export 名统一：`messageCenter.ts` → `export const useMessageCenterStore` |
| 3 | **持久化** | 需要 localStorage 持久化的 store，使用 `pinia-persist` 插件，在 `state` 中声明持久化 key |
| 4 | **action vs function** | 简单的 API 调用+赋值直接在组件中用 `await fetchData()`，不要封装到 store action 里。只有**多组件共享的状态变更**才用 store action |
| 5 | **getter 简化** | 能用 `computed()` 实现的派生数据就不要写 store getter |

### Docs 目录规范

每个 `docs/<app>/` 目录使用统一模板：

```
docs/<app-name>/
├── README.md              # App 概述（必须）
├── architecture/          # 架构设计文档
├── api/                   # API 端点文档
├── models/                # 数据模型说明
├── guides/                # 使用指南/操作手册
├── plans/                 # 设计规划/提案
├── debug/                 # 调试排障笔记
└── reference/             # 外部参考资料
```

**文件命名规则：**

| 文件类型 | 命名 | 示例 |
|----------|------|------|
| 总览文档 | `README.md` | `README.md` |
| 编号文档 | `NN-<英文标题>.md` | `01-architecture.md` |
| 设计规划 | `YYYY-MM-DD-<描述>.md` | `2026-06-07-docs-standard.md` |

**不允许在 `docs/<app>/` 根目录下创建新的 `.md` 文件**（仅允许 `README.md`），所有文档必须归入对应子目录。
