# common — 模块索引 + Seed 数据使用文档

> 上次更新: 2026-06-28 | 触发提交: cfc7d807

---

## Seed 数据管理

> 2026-06-28: 集中式 seed_reference.py / add_mock_data.py 已拆分到各子产品。
> 使用 `python manage.py seed_all` 一键运行全部，也可单独运行各子产品命令。

### Seed 命令清单

| 命令 | 所属 APP | 用途 |
|------|---------|------|
| `seed_all` | common | **总调度器**：按依赖顺序运行所有子产品 seed 命令 |
| `seed_opsflow` | opsflow | 模板分类、知识库、项目迁移、样例模板、Mock 数据 |
| `seed_template_presets` | opsflow | AI 模板预设提示词 (10 个场景) |
| `seed_cmdb` | cmdb | CMDB 模型定义 (ModelDefinition + ModelField) |
| `seed_cmdb_mock` | cmdb | CMDB Neo4j 实例 Mock 数据 |
| `seed_dr_models` | cmdb | DR 容灾模型定义 |
| `seed_monitor` | monitor | Monitor 告警动作插件 (7 个) |
| `seed_integration` | integration | 连接器定义 (20+ 个) |
| `seed_itsm` | itsm | ITSM Mock 数据 (SLA/事件/变更/请求/问题) |
| `seed_opsagent` | opsagent | OpsAgent Mock 数据 (会话/环境/记忆) |
| `seed_deploy_environments` | iam | 部署环境种子 (dev/staging/prod) |

### 使用示例

```bash
# 全量初始化（新环境）
python manage.py seed_all

# 仅初始化特定子产品
python manage.py seed_opsflow
python manage.py seed_cmdb

# 跳过某些命令
python manage.py seed_all --skip itsm.seed_itsm opsagent.seed_opsagent

# 单独初始化 IAM 环境
python manage.py seed_deploy_environments
python manage.py grant_default_env_permissions
```

---

## `common/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Common app package | — |
| `apps.py` | Common app config | `CommonConfig` |

## `common\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | Management commands package | — |
| `seed_all.py` | Master seed orchestrator，按依赖顺序调用所有子 APP 的 seed 命令 | `Command` |
| `bootstrap.py` | 一键初始化新环境 | `Command` |
| `add_itsm_mock_data.py` | ITSM pipeline workflow engine mock data | `Command` |
| `add_mock_neo4j.py` | Neo4j CMDB 拓扑 mock 数据 | `Command` |
