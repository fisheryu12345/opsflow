# common — 模块索引

> 上次自动更新: 2026-06-12

---

## `common/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Common app package |
| `apps.py` | feat(frontend): add API modules and view pages for all Phase 1 apps | `CommonConfig` |

## `common\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands for common app |

## `common\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands package |
| `add_itsm_mock_data.py` | ITSM piplework workflow engine mock data generator | `Command` |
| `add_mock_data.py` | Generate comprehensive mock data for all platform models. | `Command` |
| `add_mock_neo4j.py` | Generate mock Neo4j CMDB topology data (graph nodes + relationships). | `Command` |
| `bootstrap.py` | Unified bootstrap command — one command to initialize all data for a new environment. | `Command` |
| `seed_reference.py` | Seed system reference data: categories, knowledge, sample templates, CMDB models, monitor plugins, connector definitions, menus, IAM. | `Command` |
