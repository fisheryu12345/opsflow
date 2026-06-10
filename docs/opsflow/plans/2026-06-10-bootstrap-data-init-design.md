# Bootstrap Data Initialization Design

## 背景

开发过程中产生了大量 seed 命令和 mock 数据，分散在 13 个 Django app 中，共 **15+ 个 management commands**。新环境部署需要按特定顺序逐个执行，缺少统一入口，容易遗漏或顺序错误。

## 目标

一条命令完成新环境的数据初始化（参考数据 + 演示数据），并自动集成到 Docker Compose 部署流程中。

## 架构

### 1. Bootstrap 命令

创建 `backend/common/management/commands/bootstrap.py`，内部按阶段链式调用现有 seed 命令。

#### 执行阶段与依赖顺序

```
Phase 0: 系统核心 ── python manage.py init
  init (dept → role → user → menu → dictionary → system_config → api_whitelist)

Phase 1: 参考数据 ── 系统运行必需的配置数据，无交叉依赖
  add_app_menus           注册前端 App 菜单树
  seed_cmdb_models        内置 CMDB 模型定义
  seed_monitor            内置监控 ActionPlugin
  seed_connector_definitions  连接器定义（云厂商/通知/AI 供应商）
  seed_template_categories    18 个标准模板分类
  add_iam_menu            IAM 权限管理菜单
  opsflow_migrate_projects   默认项目创建 + 孤儿数据迁移
  seed_knowledge          知识库条目（17 篇）

Phase 2: 依赖参考数据 ── 需要 Phase 1 就绪
  seed_sample_template    示例模板（依赖 template_categories）

Phase 3: 演示数据 ── 开发和展示用
  add_mock_data           全量演示数据（16 个域）
  add_itsm_mock_data      ITSM 演示数据
  add_mock_neo4j          Neo4j 拓扑演示数据
```

#### 命令接口

```bash
python manage.py bootstrap                      # 全量：Phase 0+1+2+3
python manage.py bootstrap --essential-only     # 仅系统必需：Phase 0+1+2
python manage.py bootstrap --demo-only          # 仅演示数据：Phase 3
python manage.py bootstrap --phase 0            # 仅指定阶段
python manage.py bootstrap --force              # 强制重新生成演示数据
```

#### 实现方式

bootstrap 命令不重复实现 seed 逻辑，而是通过 `call_command()` 调用现有 management commands：

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Phase 0
        call_command('init')
        # Phase 1
        call_command('add_app_menus')
        call_command('seed_cmdb_models')
        ...
        # Phase 2
        call_command('seed_sample_template')
        # Phase 3 (if not --essential-only)
        call_command('add_mock_data', force=options['force'])
        call_command('add_itsm_mock_data', force=options['force'])
        call_command('add_mock_neo4j', scale='small')
```

#### 幂等性改进

给 `add_mock_data`、`add_itsm_mock_data` 添加 `--force` 参数：
- 默认模式：检查关键演示数据是否存在（如"示例项目"），存在则跳过
- `--force` 模式：先清空再重建

### 2. Docker Compose 集成

在 `deploy/docker/docker-compose.yml` 中新增 `init` service：

```yaml
services:
  init:
    build:
      context: ../../
      dockerfile: deploy/docker/Dockerfile
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      - SKIP_BOOTSTRAP=${SKIP_BOOTSTRAP:-false}
    command: >
      sh -c "
        python manage.py migrate &&
        python manage.py bootstrap
      "
    restart: "no"
```

#### 说明

- `depends_on.condition: service_healthy`：等待 MySQL 就绪后才执行
- `restart: "no"`：执行一次即退出，后续 `docker-compose up` 不会重复执行
- `SKIP_BOOTSTRAP=true docker-compose up`：通过环境变量跳过
- 手动重新初始化：`docker-compose run --rm init`

### 3. MySQL healthcheck

Docker Compose 中的 MySQL service 需要添加 healthcheck 以支持 bootstrap 的依赖等待：

```yaml
services:
  mysql:
    image: mysql:8.0
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 3s
      retries: 10
```

## 涉及文件

### 新建
- `backend/common/management/commands/bootstrap.py` — 统一引导命令

### 修改
- `backend/common/management/commands/add_mock_data.py` — 添加 `--force` 参数
- `backend/common/management/commands/add_itsm_mock_data.py` — 添加 `--force` 参数
- `deploy/docker/docker-compose.yml` — 新增 init service + MySQL healthcheck

### 无需改动（直接复用）
- `dvadmin/system/management/commands/init.py`
- `opsflow/management/commands/seed_template_categories.py`
- `opsflow/management/commands/seed_knowledge.py`
- `opsflow/management/commands/seed_sample_template.py`
- `opsflow/management/commands/opsflow_migrate_projects.py`
- `monitor/management/commands/seed_monitor.py`
- `integration/management/commands/seed_connector_definitions.py`
- `cmdb/management/commands/seed_cmdb_models.py`
- `common/management/commands/add_app_menus.py`
- `iam/management/commands/add_iam_menu.py`
- `common/management/commands/add_mock_neo4j.py`

## 验证

1. **本地验证：** `python manage.py bootstrap --demo-only` 仅插入演示数据
2. **全量验证：** `python manage.py bootstrap` 完整流程不报错
3. **幂等验证：** 重复执行 `bootstrap` 不报错、不产生重复数据
4. **Docker 验证：** `docker-compose up` 后 init service 成功退出，应用正常启动
5. **跳过验证：** `SKIP_BOOTSTRAP=true docker-compose up` 跳过数据初始化
