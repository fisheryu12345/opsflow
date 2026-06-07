# Docs 目录结构规范

> 日期: 2026-06-07
> 目的: 统一项目 docs/ 下所有子目录的文档存放规则

---

## 目录结构

每个 `docs/<app-name>/` 目录统一使用以下模板：

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

## 子目录职责

### README.md（必须）

每个 app 目录必须有 `README.md`，内容包含：

```markdown
# <App Name>

## 功能概述
一句话说明这个 app 做什么。

## 技术栈
后端: Django + DRF / 前端: Vue 3 + TypeScript

## 负责人
（可选）

## 关键文档索引
- [架构设计](architecture/)
- [API 文档](api/)
- [数据模型](models/)
- [使用指南](guides/)
```

### architecture/（建议）

存放架构设计文档。对于复杂 app，建议保持以下编号规则：

| 文件 | 内容 |
|------|------|
| `README.md` | 架构总览 |
| `01-overview.md` | 系统分层与模块划分 |
| `02-data-flow.md` | 核心数据流 |
| `03-<topic>.md` | 特定模块详述 |

### api/（建议）

存放 API 文档。推荐结构：

| 文件 | 内容 |
|------|------|
| `README.md` | API 总览 + Base URL + 认证方式 |
| `endpoints.md` | 端点列表（Method + Path + 说明） |
| `examples.md` | 请求/响应示例 |

### models/（建议）

存放数据模型文档。推荐结构：

| 文件 | 内容 |
|------|------|
| `README.md` | 模型总览 + ER 关系 |
| `<model-name>.md` | 具体模型字段说明 |

### guides/（建议）

存放面向用户的使用指南。按主题分文件：

| 文件 | 内容 |
|------|------|
| `quick-start.md` | 快速开始 |
| `<topic>.md` | 具体功能的使用方法 |
| `troubleshooting.md` | 常见问题排查 |

### plans/（可选）

存放设计规划/提案。文件名格式：

```
YYYY-MM-DD-<简短英文描述>.md
```

### debug/（可选）

存放调试笔记和排障记录。

### reference/（可选）

存放外部参考资料、脚本、工具说明。

## 文件命名规则

| 文件类型 | 命名规则 | 示例 |
|----------|----------|------|
| 总览文档 | `README.md` | `README.md` |
| 编号文档 | `NN-<英文标题>.md` | `01-architecture.md` |
| 设计规划 | `YYYY-MM-DD-<描述>.md` | `2026-06-07-docs-standard.md` |
| 调试笔记 | 按主题 | `node-coloring-debug.md` |

## 当前 opsflow 存量文档迁移

| 当前文件 | → 目标 | 迁移方式 |
|----------|--------|----------|
| `01-architecture.md` ~ `09-核心流程详解.md` | `architecture/` | `git mv` |
| `README.md` | 根目录保留 | 不动 |
| `TODO.md` / `TODO.html` | 根目录保留 | 不动 |
| `quick-start.md` / `mock-data-guide.md` / `project-status.md` / `注意事项.md` | `guides/` | `git mv` |
| `generate_pdf.py` / `link_rules.md` | `reference/` | `git mv` |
| `debug/` | 保持不动 | 不动 |
| `plans/` | 保持不动 | 不动 |

## 检查机制

- PR review 时检查新加的文档是否放入了正确子目录
- 不允许在 `docs/<app>/` 根目录下创建新的 `.md` 文件（仅允许 `README.md`）
