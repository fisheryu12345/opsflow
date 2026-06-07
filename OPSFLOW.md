# OPSflow Style Guide

All OPSflow Vue components should follow these conventions for visual consistency.

**后续向导对话框参考:** `SubmitWizardDialog.vue` — 多步骤弹窗的 HTML/SCSS/动画标准实现。

### SCSS
- Use `<style lang="scss" scoped>` and `@use '../styles/opsflow-global' as *;`
- Card containers: use `.of-card` class for standard card backgrounds/borders
- Dialogs: add class `opsflow-dialog` — header/body/footer styled automatically
- Animations: `.of-fade-in-up` for sections, `.of-stagger-item` for list items (keep inline `animation-delay`)
- Colors/gradients: use `$of-*` variables from `styles/opsflow-variables.scss`, never hardcode
- Hover effects: `@include of-hover-lift` (lift up) or `@include of-hover-shift` (shift right)

### HTML
- Class naming: kebab-case, component-prefixed (e.g. `mycomp-header`)
- Empty state: `<el-empty :image-size="40" />`

### Key Files
- `web/src/views/apps/opsflow/styles/opsflow-variables.scss` — design tokens
- `web/src/views/apps/opsflow/styles/opsflow-global.scss` — reusable classes & mixins

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

#### 前端规范

- `views/` 下按 app 分目录（`opsflow/`，`system/`，`cmdb/` 等）
- `views/apps/opsflow/components/` 下按功能拆分子目录（`canvas/`，`dialogs/`，`panels/` 等）
- 组件使用 PascalCase 命名（如 `DesignCanvas.vue`）
- 新增 opsflow 独立页面必须在 `views/apps/opsflow-*/` 下创建独立目录

#### Skills 规范

- 所有 Claude 技能放在项目级 `.claude/skills/` 目录
- 新技能创建后立即放入项目级目录
- 保持用户级 `.claude/skills/` 与项目级同步（或项目级优先）

#### 其他规范

- 运行脚本放在 `scripts/`，后端内部脚本放在 `backend/tools/`
- 参考源码放在 `refrence/` 目录，内容通过 `.gitignore` 忽略
- 任何生成运行时目录（`logs/`，`media/`，`static/`）在 `.gitignore` 中声明

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
