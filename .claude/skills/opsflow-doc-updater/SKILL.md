---
name: opsflow-doc-updater
description: |
  更新 OpsFlow 项目文档并生成 PDF。当用户说"更新opsflow文档"、"同步文档"、"刷新文档"、"更新doc"、"sync opsflow docs"、"update opsflow documentation" 时触发。
  这个技能会扫描 OpsFlow 后端 Python 代码和前端 Vue/TypeScript 代码，分析当前代码状态，然后自动更新 backend/opsflow/doc/ 下的所有文档和 TODO.md，
  并基于更新后的 markdown 源文件生成/更新对应的 PDF 文档。
  即使变更只涉及一个模块（如只改了 flow_engine.py），也要触发完整文档更新以确保所有文件保持一致。
---

# OpsFlow Doc Updater

将 OpsFlow 代码库的当前状态同步到 `backend/opsflow/doc/` 下的文档中。包括架构、代码结构、核心引擎、前端设计、功能状态、部署注意事项等文档文件，
并生成对应的 PDF 版本。同时涵盖 OpsFlow 与 bk_sops 的全方位对比分析文档及其 PDF。

## 工作流程

### 第 0 步：扫描 OpsFlow 对项目全局文件的修改

OpsFlow 不是一个完全独立的 Django app — 它对项目有多处侵入式修改。每次更新文档时必须同步更新 `生成环境部署注意事项.md`。

使用 Grep 工具在以下全局目录中搜索 `opsflow` 引用：

| 目录 | 关注点 |
|------|--------|
| `backend/application/` | settings.py (INSTALLED_APPS)、urls.py (API 路由)、routing.py (WebSocket)、__init__.py (Celery 导入)、asgi.py、celery.py |
| `backend/conf/env.py` | OPSFLOW_SCHEDULER_AUTOSTART 等环境配置 |
| `backend/requirements.txt` | bamboo-pipeline、apscheduler、django_apscheduler、pytz 等 OpsFlow 依赖 |
| `web/src/router/` | OpsFlow 前端页面路由配置 |
| `web/src/views/apps/opsflow-*/` | 所有 opsflow- 前缀的页面目录 |

同时检查 `web/package.json` 中是否有 `@antv/x6`、`@antv/x6-plugin-*` 等前端依赖。

### 第 1 步：扫描 OpsFlow 内部代码

使用 Glob 和 Grep 工具收集以下信息：

**后端** (`backend/opsflow/`):
- `models/` — 所有模型类及其字段 (template.py, execution.py, schedule.py, plugin.py, project.py 等)
- `urls.py` — 注册的 API 路由
- `views/*.py` — 所有视图集和 action 端点
- `serializers.py` — 序列化器
- `tasks.py` — Celery 任务列表
- `consumers.py` — WebSocket 消费者
- `core/*.py` — 所有核心模块（flow_engine, bamboo_builder, variable_resolver, signal 等）
- `signals/` — 信号处理器包
- `plugins/` — 插件系统
- `apps.py` — App 启动配置

**前端** (`web/src/views/apps/opsflow/`):
- `index.vue` — 主页面布局和逻辑
- `components/*.vue` — 所有组件（DesignCanvas, MonitorCanvas, PropertyPanel, DiffModal, DryRunDialog 等）
- `composables/*.ts` — 所有 composable（useDesignCanvas, useMonitor, useGraphValidator, useAutoSave 等）
- `stores/opsflowStore.ts` — Pinia store

**前端 API** (`web/src/api/opsflow/`):
- `templates.ts`, `executions.ts`, `logs.ts`, `knowledge.ts`, `schedule-plans.ts`, `dashboard.ts`, `plugins.ts`, `projects.ts`, `audit.ts` 等

**bk_sops 对比源** (`C:\Users\dell\Desktop\Vue\bk_sops\bk-sops-release_humming_bird/`):
- `gcloud/taskflow3/` — 任务执行模型、调度器、自动重试、回调、状态管理
- `gcloud/tasktmpl3/` — 模板模型、版本管理
- `gcloud/core/` — 项目模型、引擎配置、资源配置
- `gcloud/apigw/` — API 网关端点
- `gcloud/template_base/` — 基础模板抽象
- `pipeline_web/parser/` — Pipeline 格式转换、清理、验证
- `pipeline_web/drawing_new/` — Sugiyama 布局引擎
- `pipeline_web/core/` — 节点属性注册模式
- `pipeline_plugins/` — 组件和变量插件实现
- `frontend/desktop/src/` — Vue 2 前端代码（TemplateCanvas, RenderForm, store 等）

### 第 2 步：读取现有文档

读取 `backend/opsflow/doc/` 下的所有文件，了解当前文档结构和内容。这些是你需要更新的目标文件列表：

| 文件 | 内容 |
|------|------|
| `README.md` | 总览 — 架构图 + 功能清单 + 技术栈 |
| `01-architecture.md` | 系统架构 — 分层设计 + 执行流程 + 关键决策 |
| `02-code-structure.md` | 代码结构 — 目录树 + 模型关系 + API 端点 + 模块依赖 |
| `03-core-engine.md` | 核心引擎 — FlowEngine / BambooBuilder / 完整执行流程 |
| `04-frontend.md` | 前端设计 — 页面结构 + X6 节点 + Stencil + 数据流 |
| `05-feature-status.md` | 功能状态 — 已完成/待实现 + Pipeline 格式 + 状态机 |
| `06-deployment-notes.md` | **生成环境部署注意事项** — OpsFlow 对项目外部文件的修改清单 |
| `07-bk_sops_opsflow.md` | OpsFlow vs bk_sops 全方位对比分析 |
| `08-模型表关系说明.md` | 模型表关系说明 — 15个模型字段/约束/FK关系/ER图 |
| `09-核心流程详解.md` | 核心流程详解 — FlowEngine/PipelineBuilder/信号/Celery/超时/回滚 |
| `TODO.md` | 待办清单 |

另外读取 `TODO.md` 了解待办状态，以及 `bk_sops.md` 了解之前对 bk_sops 的分析结论。

### 第 3 步：对比并更新文档

对于每份文档，对比当前代码状态和现有文档内容：

1. **README.md** — 更新架构图是否仍准确、功能清单状态、技术栈版本
2. **01-architecture.md** — 检查分层描述、执行流程、关键决策是否仍适用
3. **02-code-structure.md** — **关键**：更新目录结构（新增/删除的文件）、API 端点变化、模块依赖关系
4. **03-core-engine.md** — 更新核心引擎方法签名、完整执行流程、校验规则
5. **04-frontend.md** — 更新节点定义、Stencil 分组、数据流
6. **05-feature-status.md** — **关键**：更新已完成/待实现功能列表，保持与 TODO.md 同步
7. **06-deployment-notes.md** — **关键**：根据第 0 步扫描结果完整更新，记录所有 OpsFlow 对项目外部文件的修改
8. **07-bk_sops_opsflow.md** — 如需更新，重新扫描 OpsFlow 和 bk_sops 全量代码，更新对比表中新增功能/变化

更新原则：
- 保留文档的架构图和 ASCII 图示，只修正过时的部分
- 文件行数不要超过 500 行
- 保持一致的格式和风格
- 如果某个模块增加了新文件，在目录树中补充
- 如果 API 端点有增减，更新端点表
- 如果模型字段有变化，更新模型关系图

### 第 4 步：更新 TODO.md

同步更新 `backend/opsflow/TODO.md`：
- 检查已完成的 TODO 项并标记 `[x]`
- 如果有新的待办项，添加到对应优先级分组
- 不做大面积重新排版，保持原有格式

### 第 5 步：生成 TODO.html 项目看板

在 `backend/opsflow/doc/TODO.html` 生成独立的 HTML 项目看板文件。该文件以表格形式直观展示所有 Phase 的完成情况，便于在浏览器中查看。

**格式要求：**
- 使用内联 CSS 的自包含 HTML 文件（无外部依赖）
- 顶部标题 + 更新时间
- 项目符号说明：✅ = 已完成、❌ = 待实现、⚡ = 骨架/伪代码、🔄 = 进行中
- 按 Phase 分块，每块一个表格，列：任务 | 状态
- 表格交替行背景色（#f8f9fa / #ffffff），hover 高亮
- Phase 标题使用对应颜色的左侧边框（绿=已完成度高，橙=进行中，红=未开始）
- 底部加总览汇总表：分类 | 总计 | ✅ 完成 | ❌ 待办 | ⚡ 部分完成 | 完成率
- 设计风格参考 django-vue3-admin 的白卡片风格（白色背景、圆角、阴影）

**数据来源：**
- 以 `C:\Users\dell\Desktop\TODO.md` 和 `backend/opsflow/TODO.md` 为数据源
- 通过扫描代码库验证各项的真实状态（避免 TODO.md 过时）
- 计数规则：每个 checkbox `[x]` 计为 1 ✅，`[ ]` 计为 1 ❌

**CSS 样式规范：**
```css
/* 主容器 */
body { background: #f0f2f5; font-family: -apple-system, ...; }
.container { max-width: 1000px; margin: 0 auto; padding: 24px; }

/* Phase 卡片 */
.phase-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 20px; }
.phase-header { padding: 16px 20px; border-left: 4px solid #67C23A; font-size: 16px; font-weight: 600; }
.phase-header.orange { border-left-color: #E6A23C; }
.phase-header.red { border-left-color: #F56C6C; }

/* 表格 */
table { width: 100%; border-collapse: collapse; }
th { background: #fafafa; padding: 10px 16px; text-align: left; font-weight: 600; }
td { padding: 10px 16px; border-top: 1px solid #ebeef5; }
tr:nth-child(even) td { background: #f8f9fa; }
tr:hover td { background: #ecf5ff; }

/* 状态标签 */
.status-done { color: #67C23A; font-weight: 600; }
.status-pending { color: #F56C6C; }
.status-wip { color: #E6A23C; }
```

### 第 6 步：从 Markdown 源文件生成 / 更新 PDF 文档

在 markdown 文档更新完成后，调用 `backend/opsflow/doc/generate_pdf.py` 脚本生成所有 PDF。

**生成命令：**
```bash
# 生成所有 PDF（覆盖已有文件）
python backend/opsflow/doc/generate_pdf.py

# 列出可用的文档
python backend/opsflow/doc/generate_pdf.py --list

# 生成单个 PDF
python backend/opsflow/doc/generate_pdf.py --file 01-architecture.md --force
```

**需要生成/覆盖的 PDF 目标文件：**

| # | PDF 文件 | MD 源文件 | 内容覆盖 |
|--|---------|----------|---------|
| 1 | `doc/01-architecture.pdf` | 01-architecture.md | 系统架构 — 分层设计、整体架构图、5 层描述、执行流程、关键设计决策 |
| 2 | `doc/02-code-structure.pdf` | 02-code-structure.md | 代码结构 — 后端/前端完整目录树、模型关系图(含全部 FK)、API 端点汇总(含所有 ViewSet 和 action)、核心模块依赖图 |
| 3 | `doc/03-core-engine.pdf` | 03-core-engine.md | 核心引擎 — 模板到执行完整 8 阶段流程、BambooBuilder 编译、PluginService 路由、状态追踪(信号驱动)、执行控制、并行/条件分支 |
| 4 | `doc/04-frontend.pdf` | 04-frontend.md | 前端设计 — 页面结构、9 种 X6 自定义节点定义、Stencil 10 组分组的完整原子列表、WebSocket 监控数据流 |
| 5 | `doc/05-feature-status.pdf` | 05-feature-status.md | 功能状态 — 后端/前端已完成功能详细清单、Pipeline 格式定义(节点类型/出边规则)、执行状态机图 |
| 6 | `doc/06-deployment-notes.pdf` | 06-deployment-notes.md | 部署说明 — settings.py 修改、urls.py 路由、WebSocket 路由、requirements.txt 依赖、前端 Router/Celery/Redis 等完整配置 |
| 7 | `doc/07-bk_sops_opsflow.pdf` | 07-bk_sops_opsflow.md | OpsFlow vs bk_sops 全方位对比 — 14 大维度 130+ 子项对比、关键差异总结(20+16项优势)、可相互借鉴要点(10+15项) |
| 8 | `doc/08-模型表关系说明.pdf` | 08-模型表关系说明.md | 模型表关系 — 15个数据模型全部字段/约束/级联策略/完整ER关系图 |
| 9 | `doc/09-核心流程详解.pdf` | 09-核心流程详解.md | 核心流程 — FlowEngine/PipelineBuilder/PluginService/信号/Celery/超时/回滚/Webhook 全流程源码解析 |

**PDF 生成规范：**
- 使用 SimSun(宋体) 和 SimHei(黑体) Windows 系统字体确保中文正常渲染
- 横版 (Landscape) 用于表格密集型文档（架构、代码结构、前端、功能状态、对比分析）
- 竖版 (Portrait) 用于文字密集型文档（核心引擎、部署说明、核心流程详解）
- 封面页包含标题、副标题、日期
- 页眉/页脚包含文档名称和页码
- 代码块自动检测非 ASCII 字符并使用中文字体渲染
- 表格支持自动分页、交替行背景色
- 对比分析文档使用 `ComparisonPDF` 类，优化表格渲染

**验证：**
- 生成后检查 PDF 文件大小和页数
- 使用 pypdf 验证 PDF 完整性
- 确认中文字符、表格、代码块均正确渲染

## 重要提示

- 所有文档文件都使用中文编写，但代码示例和标识符保持英文
- ASCII 图示使用 `┌─┐` 等字符，保持对齐
- 不要在文档中添加 emoji
- 文档是对当前代码状态的**快照**，不是设计文档 — 基于实际代码内容编写，不要写尚未实现的功能
- 如果发现代码和现有文档有明显不一致，以代码为准更新文档
- TODO.html 与 TODO.md 的数据必须保持一致，两者同步更新
- PDF 文件必须与对应的 markdown 源文件保持同步：更新 md 后必须重新生成 pdf
- generate_pdf.py 是 PDF 生成的唯一入口，不要手动编辑 PDF 文件
- 如果新增了 doc/*.md 文件，需要在 generate_pdf.py 的 DOC_FILES 字典中注册对应的元信息
