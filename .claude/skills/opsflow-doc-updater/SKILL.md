---
name: opsflow-doc-updater
description: |
  更新 OpsFlow 项目文档。当用户说"更新opsflow文档"、"同步文档"、"刷新文档"、"更新doc"、"sync opsflow docs"、"update opsflow documentation" 时触发。
  这个技能会扫描后端 Python 代码和前端 Vue/TypeScript 代码，分析当前代码状态，然后自动更新 docs/ 下各 App 子目录的文档和 TODO.md。
  即使变更只涉及一个模块（如只改了 flow_engine.py），也要触发完整文档更新以确保所有文件保持一致。
---

# OpsFlow Doc Updater

将 OpsFlow 代码库的当前状态同步到 `docs/` 下的各 App 子目录。包括架构、代码结构、核心引擎、前端设计、功能状态、部署注意事项等文档文件。

## 工作流程

### 第 0 步：扫描各 App 对项目全局文件的修改

OpsFlow、CMDB、ITSM 等都不是完全独立的 Django app — 它们对项目有多处侵入式修改。每次更新文档时必须同步更新各 App 的部署注意事项文档。

使用 Grep 工具在以下全局目录中搜索各 App 名称（`opsflow`、`cmdb`、`itsm` 等）引用：

| 目录 | 关注点 |
|------|--------|
| `backend/application/` | settings.py (INSTALLED_APPS)、urls.py (API 路由)、routing.py (WebSocket)、__init__.py (Celery 导入)、asgi.py、celery.py |
| `backend/conf/env.py` | 各 App 的环境配置 |
| `backend/requirements.txt` | 各 App 的依赖 |
| `web/src/router/` | 各 App 前端页面路由配置 |
| `web/src/views/apps/` | 所有 App 前端页面目录 |

同时检查 `web/package.json` 中是否有各 App 所需的前端依赖。

### 第 1 步：扫描各 App 内部代码

使用 Glob 和 Grep 工具收集以下信息：

**后端** — 遍历 `backend/` 下所有 Django app 目录（如 `opsflow/`、`cmdb/`、`itsm/` 等，排除 `dvadmin/`、`application/`、`conf/` 等框架目录），对每个 App 扫描：
- `models/` — 所有模型类及其字段
- `urls.py` — 注册的 API 路由
- `views/*.py` — 所有视图集和 action 端点
- `serializers.py` — 序列化器
- `tasks.py` — Celery 任务列表
- `consumers.py` — WebSocket 消费者
- `core/*.py` — 所有核心模块
- `signals/` — 信号处理器包
- `plugins/` — 插件系统
- `apps.py` — App 启动配置

**前端** — 遍历 `web/src/views/apps/` 下所有 App 目录（如 `opsflow/`、`cmdb/`、`itsm/` 等），对每个 App 扫描：
- `index.vue` — 主页面布局和逻辑
- `components/*.vue` — 所有组件
- `composables/*.ts` — 所有 composable
- `stores/*.ts` — Pinia store

**前端 API** — 遍历 `web/src/api/` 下所有 App API 目录（如 `opsflow/`、`cmdb/`、`itsm/` 等）：
- 所有 `.ts` API 客户端文件

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

读取 `docs/` 下各 App 子目录的所有文件，了解当前文档结构和内容。

**文档目录结构：**

| 目录 | 内容 |
|------|------|
| `docs/opsflow/` | OpsFlow 相关文档 |
| `docs/cmdb/` | CMDB 相关文档 |
| `docs/itsm/` | ITSM 相关文档 |

每个 App 子目录下的文档文件命名约定（以 opsflow 为例）：

| 文件 | 内容 |
|------|------|
| `README.md` | 总览 — 架构图 + 功能清单 + 技术栈 |
| `01-architecture.md` | 系统架构 — 分层设计 + 执行流程 + 关键决策 |
| `02-code-structure.md` | 代码结构 — 目录树 + 模型关系 + API 端点 + 模块依赖 |
| `03-core-engine.md` | 核心引擎 — 流程引擎 / Builder / 完整执行流程 |
| `04-frontend.md` | 前端设计 — 页面结构 + 节点自定义 + 数据流 |
| `05-feature-status.md` | 功能状态 — 已完成/待实现 + 状态机 |
| `06-deployment-notes.md` | **生成环境部署注意事项** — 该 App 对项目外部文件的修改清单 |
| `TODO.md` | 待办清单 |

各 App 子目录的实际文件可能有所不同，以实际扫描到的文件为准。读取时需遍历每个子目录，获取该 App 的所有文档。

### 第 3 步：对比并更新文档

对于每份文档，对比当前代码状态和现有文档内容。按 App 逐个子目录处理：

1. **README.md** — 更新架构图是否仍准确、功能清单状态、技术栈版本
2. **01-architecture.md** — 检查分层描述、执行流程、关键决策是否仍适用
3. **02-code-structure.md** — **关键**：更新目录结构（新增/删除的文件）、API 端点变化、模块依赖关系
4. **03-core-engine.md** — 更新核心引擎方法签名、完整执行流程、校验规则
5. **04-frontend.md** — 更新节点定义、数据流
6. **05-feature-status.md** — **关键**：更新已完成/待实现功能列表，保持与 TODO.md 同步
7. **06-deployment-notes.md** — **关键**：根据第 0 步扫描结果完整更新，记录该 App 对项目外部文件的修改
8. **07-* 等对比分析文档** — 如需更新，重新扫描对比源代码

更新原则：
- 保留文档的架构图和 ASCII 图示，只修正过时的部分
- 文件行数不要超过 500 行
- 保持一致的格式和风格
- 如果某个模块增加了新文件，在目录树中补充
- 如果 API 端点有增减，更新端点表
- 如果模型字段有变化，更新模型关系图

### 第 4 步：基于顶层设计 + 代码扫描生成 TODO 清单

**数据源锚定：** 以 `docs/opsflow_target.md` 第 5 章（各子产品当前状态与路线图）为所有 TODO 任务的**权威数据源**。该文档定义了平台最终目标架构、每个子产品的定位、成熟度矩阵和 P0/P1/P2 路线图。**不可随意增删顶层设计中未定义的任务，如需新增必须先更新顶层设计文档。**

#### 4.1 加载顶层设计中的任务数据

读取 `docs/opsflow_target.md` 第 5 章，对每个子产品提取：

| 数据 | 来源 |
|------|------|
| 成熟度评分 | §5.1 成熟度矩阵 |
| P0 任务列表 | §5.2 P0 章节 |
| P1 任务列表 | §5.2 P1 章节 |
| P2 任务列表 | §5.2 P2 章节 |
| 模块职责与状态 | §3.4 各子产品定位中的模块表格 |

以 OpsFlow Core 为例，提取结果应为：

```json
{
  "app": "opsflow",
  "maturity": "⭐⭐⭐⭐⭐ (5/5)",
  "modules": [
    {"name": "FlowEngine", "status": "✅ 完整"},
    {"name": "apigw/ (已迁移)", "status": "✅ 已迁移"},
    ...
  ],
  "tasks": {
    "P0": [],
    "P1": [
      "项目级 RBAC 增强",
      "操作审计前端",
      "TemplateNode/ExecutionNode 节点同步定时任务",
      ...
    ],
    "P2": [
      "配置驱动表单架构",
      "批量删除模板/执行",
      ...
    ]
  }
}
```

#### 4.2 代码扫描验证

对每个子产品的每项任务，通过代码扫描确认真实状态：

| 扫描手段 | 确认逻辑 | 状态判定 |
|---------|---------|:--------:|
| `Grep` 搜索关键函数/类/路由 | 搜索函数定义、路由注册、类声明 | ✅ 有实现 / ❌ 不存在 |
| `Glob` 检查文件/目录 | 检查关键文件是否存在 | ✅ 存在 / ❌ 不存在 |
| `Read` 查看实现细节 | 读取关键函数确认功能完整度 | ✅ 完整 / 🔄 骨架 |
| `Grep` 搜索路由注册 | 确认端点已在 `urls.py` 或 `application/urls.py` 注册 | ✅ 已注册 / ❌ 未注册 |

**判定标准：**

| 扫描结果 | 标记 | 说明 |
|---------|:----:|------|
| 完整实现，代码可用 | `[x]` | 任务已完成 |
| 骨架/部分实现存在 | `[ ]` 备注"进行中" | 代码已验证部分完成 |
| 顶层设计定义但代码中不存在 | `[ ]` | 待实现 |
| 顶层设计不再包含 | 删除 | 已废弃 |

#### 4.3 以子产品为维度输出

每个子产品按以下模板输出 TODO：

```markdown
# <子产品名> — 开发路线图

> 基于 `docs/opsflow_target.md` v1.0 顶层设计
> 最后代码验证: YYYY-MM-DD
> 顶层设计版本锚定: <commit SHA>

## 成熟度: ⭐⭐⭐☆☆ (3/5)

| 模块 | 职责 | 代码状态 |
|------|------|:--------:|
| ModuleA | 职责说明 | ✅ 完整 |
| ModuleB | 职责说明 | 🔄 完善中 |
| ModuleC | 职责说明 | 📅 规划 |

## P0 — 高优先级

- [x] **任务名称** — 说明（验证依据: <文件路径> 中已实现 `Xxx` 功能）
- [ ] **任务名称** — 说明（顶层设计参考: §5.2 P0）
...

## P1 — 中优先级

...

## P2 — 低优先级

...
```

### 第 5 步：生成统一的 TODO 看板（MD + HTML）

**不再更新 `docs/opsflow/TODO.md` 文件。** 改为生成两份统一汇总文件，按子产品维度全面展示各 App 的 TODO 状态。

#### 5.1 输出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| TODO 总览 Markdown | `docs/TODO.md` | 可阅读的 Markdown 汇总，便于在 IDE 和 Git 中查看 |
| TODO 总览 HTML | `docs/TODO.html` | 带交互样式的 HTML 看板，便于在浏览器中查看 |

#### 5.2 TODO.md 结构

```markdown
# OPSflow 平台开发路线图总览

> 基于 `docs/opsflow_target.md` 顶层设计 · 最后代码验证: YYYY-MM-DD
> 顶层设计锚定版本: <commit SHA>

## 总览

| 子产品 | 成熟度 | P0 | P1 | P2 | 完成率 |
|-------|:------:|:--:|:--:|:--:|:------:|
| OpsFlow Core | ⭐⭐⭐⭐⭐ (5/5) | 0/0 | 3/4 | 1/2 | xx% |
| CMDB | ⭐⭐⭐⭐☆ (4/5) | ... | ... | ... | xx% |
| ... | ... | ... | ... | ... | ... |

### OpsFlow Core (⭐⭐⭐⭐⭐)

**定位:** 整个平台的核心，所有运维自动化流程的编排与执行中枢

| 模块 | 职责 | 状态 |
|------|------|:----:|
| FlowEngine | 流程执行主入口 | ✅ 完整 |
| ... | ... | ... |

#### P0 — 高优先级
- [x] **Open API 独立化** — 已迁移至 `backend/open_api/` (`open_api/views/external.py` 中实现 `trigger_pipeline/query_execution/list_pipeline_templates`)

#### P1 — 中优先级
- [ ] **项目级 RBAC 增强** — viewer 只读权限强制（§5.2 P1）
...

---

### CMDB (⭐⭐⭐⭐)

...
```

#### 5.3 TODO.html 格式要求

- 自包含 HTML（无外部依赖，全部内联 CSS）
- 顶部：标题 + 基于顶层设计与更新时间
- 子产品分块，每块为一张白卡片：
  - 卡片标题：子产品名 + 成熟度星级 + 左侧彩色边框（绿=5星，蓝=4星，橙=3星，红≤2星）
  - 模块状态行：模块名 + 状态图标（✅/🔄/📅）
  - 任务表格：列 = 优先级 | 任务 | 状态 | 验证依据
  - 已完成行使用 ~~删除线~~ 浅灰背景
- 底部汇总表：子产品 | 总任务 | ✅ 完成 | 🔄 进行中 | ❌ 待办 | 完成率
- 设计风格：白卡片、圆角 8px、box-shadow、字体系统 12px/14px、交替行背景

#### 5.4 数据来源优先级

```
顶层设计 (docs/opsflow_target.md §5) + 代码扫描验证
    → 生成统一的 TODO.md + TODO.html
    → 不再依赖或更新各 App 子目录下的 TODO.md
```

**覆盖范围：** 以下子产品全部纳入统一看板，按 `docs/opsflow_target.md` 第 5 章成熟度矩阵的顺序排列：

1. OpsFlow Core
2. dvadmin (RBAC)
3. CMDB
4. ITSM
5. Monitor
6. Open API
7. Portal
8. Integration Hub
9. Job Platform
10. OpsAgent
11. Agent (远程)
12. CI/CD + K8s

### 第 6 步：全量对比 OpsFlow vs 蓝鲸系参考源码

全量扫描 opsflow 自身实现与 reference/ 中蓝鲸参考源码的代码结构和功能，生成两份对比分析文档，合并输出到统一的 MD 文件。

**对比目标：**

| 对比项 | OpsFlow 实现 | 蓝鲸参考源码 | 参考源码类型 |
|--------|------------|-------------|------------|
| 流程引擎 vs bk-sops | `backend/opsflow/` (Python/Django) | `reference/bk-sops-release_humming_bird/` (Python/Django) | Python，架构可对照 |
| CMDB vs bk-cmdb | `backend/cmdb/` (Python/Django) | `reference/bk-cmdb/` (Go) | Go，功能可对照，语言不同 |

**扫描要点：**

**OpsFlow vs bk-sops**（Python vs Python，可深入代码级比较）：
- 模板/流程定义模型及版本管理
- 任务执行引擎（状态机、生命周期、回调）
- 节点/插件系统架构（注册、参数解析、输入输出）
- 布局引擎（Sugiyama vs 自定义）
- 前端设计（X6 自定义节点 vs bk 的 Vue 2 方案）
- API 设计风格
- 调度器、超时、重试、Webhook 机制

**OpsFlow CMDB vs bk-cmdb**（Python vs Go，侧重功能对位比较）：
- 模型定义管理（模型、属性、分组、唯一约束）
- 实例管理（CRUD、关联、拓扑）
- 关联类型及管理
- 事件/变更追踪机制
- 导入导出能力
- 鉴权模型（IAM vs 内置 RBAC）
- bk-cmdb 有但 opsflow-cmdb 尚未实现的关键能力

**输出文件：**

生成 `docs/opsflow_vs_bk.md`，结构要求：
1. **概述** — 对比目标和范围说明
2. **OpsFlow vs bk-sops 对比** — 分层对比表（架构层、引擎层、插件层、前端层、API 层、部署层），每层含：
   - OpsFlow 实现概述
   - bk-sops 实现概述
   - 关键差异分析
   - 可相互借鉴要点
3. **OpsFlow CMDB vs bk-cmdb 对比** — 功能维度对比表，含：
   - 功能对位矩阵（有/无/部分）
   - 实现差异说明
   - bk-cmdb 可借鉴的关键能力清单
4. **结论** — 总体优劣势总结、下一步建议

## 重要提示

- 所有文档文件都使用中文编写，但代码示例和标识符保持英文
- ASCII 图示使用 `┌─┐` 等字符，保持对齐
- 不要在文档中添加 emoji
- 文档是对当前代码状态的**快照**，不是设计文档 — 基于实际代码内容编写，不要写尚未实现的功能
- 如果发现代码和现有文档有明显不一致，以代码为准更新文档
- TODO.html 与各 TODO.md 的数据必须保持一致，两者同步更新
