# OPSflow Process & Governance Standards

## 顶层设计约束

所有设计文档（功能设计、详细设计等）和开发工作，**必须**遵守以下约束：

1. **顶层设计优先** — `docs/opsflow_target.md` 定义了 OPSflow 平台的最终目标架构、子产品定位和组件交互规范。任何功能设计或开发必须以此为准绳。
2. **冲突解决流程** — 若开发过程中发现与 `docs/opsflow_target.md` 的顶层设计存在冲突或疑问，**必须先进行头脑风暴讨论明确定案，方可改动**。不得在不经讨论的情况下偏离顶层设计。
3. **设计文档引用** — 所有 `docs/opsflow/plans/` 下的设计文档必须引用本文件作为架构依据，并在设计评审时对照 `docs/opsflow_target.md` 校验一致性。

---

## 设计文档管理规则

所有通过 Superpowers 或其他 AI 工具生成的设计文档（架构设计、功能设计、详细设计等），**必须**遵守以下规则：

1. **保存路径**：统一保存到 `docs/opsflow/plans/` 目录下
2. **文档格式**：`.md`（Markdown）格式
3. **文件命名**：`YYYY-MM-DD-<简短英文描述>.md`（如 `2026-06-03-gateway-condition-editor-design.md`）
4. **适用范围**：包括但不限于 Superpowers、SPARC 流程、Claude Code、以及其他 AI Agent 产出的设计文档

---

## Git 提交与分支规范

### 分支策略

- **禁止直接在 `main` 分支上开发。** 新功能从 `main` 切 `feat/<short-desc>` 分支，修复从 `main` 切 `fix/<short-desc>` 分支
- 分支名全小写，中划线分隔，如 `feat/gateway-condition-editor`、`fix/node-output-display`
- 合并回 `main` 后删除远程分支

### Commit Message 格式

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

---

## Docs 目录规范

### 跨 App 公共标准

所有子 App 共享的开发规范存放在 `docs/guides/` 目录下：

```
docs/
├── guides/
│   ├── frontend-style-guide.md      # 前端规范（SCSS/Vue/i18n/TS/按钮/Pinia）
│   ├── project-standards.md         # 工程规范（架构/API/后端分层/错误处理）
│   ├── process-standards.md         # 流程规范（Git/文档/设计约束）
│   ├── mock-data-guide.md           # 数据初始化指南（Django + Neo4j）
│   ├── 注意事项.md                   # 开发注意事项（Celery/Redis/WS）
│   ├── quick-start.md               # OpsFlow 快速入门（opsflow 专用）
│   └── project-status.md            # 项目状态（opsflow 专用）
├── <app-name>/              # 各 App 专有文档
├── superpowers/specs/       # 顶层设计规范
└── architecture/            # 跨 App 架构（如 Django 升级）
```

### 每个子 App 目录使用统一模板

```
docs/<app-name>/
├── README.md              # App 概述（必须）
├── architecture/          # 架构设计文档
├── api/                   # API 端点文档
├── models/                # 数据模型说明
├── guides/                # 使用指南/操作手册（App 专用）
├── plans/                 # 设计规划/提案
├── debug/                 # 调试排障笔记
├── features/              # 功能文档（新功能记录）
├── config/                # 配置变更记录
├── migration/             # 迁移指南
└── reference/             # 外部参考资料
```

**文件命名规则：**

| 文件类型 | 命名 | 示例 |
|----------|------|------|
| 总览文档 | `README.md` | `README.md` |
| 编号文档 | `NN-<英文标题>.md` | `01-architecture.md` |
| 设计规划 | `YYYY-MM-DD-<描述>.md` | `2026-06-07-docs-standard.md` |

**不允许在 `docs/<app>/` 根目录下创建新的 `.md` 文件**（仅允许 `README.md`），所有文档必须归入对应子目录。
