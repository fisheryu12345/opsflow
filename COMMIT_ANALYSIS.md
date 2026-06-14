# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## `4ce858ff`

> 提交日期: 2026-06-14 | 提交信息: refactor: migrate topology tree to G6 v5 custom shapes + demo data — 拓扑视图 G6 v5 重构与演示数据

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | 前端 | G6 v4→v5 迁移：TreeGraph→Graph, compactBox→indented, 自定义 Rect+Badge 节点 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | 新增"演示"按钮 + 21 节点演示数据 + CSS 全高布局修复 |
| `web/package.json` | 前端 | `@antv/g6` 4.8.25 → 5.1.1 |
| `web/package-lock.json` | 前端 | 锁定依赖 |
| `web/yarn.lock` | 前端 | 锁定依赖 |

### 解决

- **问题/背景：** G6 v4 已废弃，不支持自定义图形组合；折叠/展开在 v4 中通过 updateChild + layout() 手动触发不稳定；拓扑视图无数据时完全空白，画布高度固定 560px
- **办法：** 迁移到 G6 v5 Graph + treeToGraphData + 自定义 Rect 扩展(Badge/状态点)；演示数据按钮填充 Biz→Set→Module→Host 层级树；CSS flex:1 全高布局

### 文档

- **生成文档：**
  - `docs/cmdb/features/2026-06-14-topology-demo-data.md`
  - `docs/cmdb/architecture/2026-06-14-topology-g6-v5-migration-refactor.md`
  - `docs/cmdb/config/2026-06-14-g6-upgrade-config.md`

### 验证

- 改动类型: refactor + feat + chore
- 清理乱码: 无
- 工作区状态: 有未跟踪文件（docs/ 与 COMMIT_ANALYSIS.md）

---

## `7434406d`

> 提交日期: 2026-06-12 | 提交信息: chore: cmdb i18n + G6 topology refactor + config tidying — CMDB 国际化、G6 拓扑重构、配置清理

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/i18n/pages/cmdb/zh-cn.ts` | 前端 | CMDB 页面全量 i18n 中文 key |
| `web/src/i18n/pages/cmdb/en.ts` | 前端 | CMDB 页面全量 i18n 英文 key |
| `web/src/views/apps/cmdb/components/DrTopologyCanvas.vue` | 前端 | 圆形节点 + fitView 高度保护 + i18n 替换 |
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | 前端 | G6 v4 TreeGraph 恢复 + i18n 右键菜单 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | v-show → v-if 修复拓扑 tab fitView 溢出 + i18n |
| `web/src/router/route.ts` | 前端 | 新增 /home 路由指向 portal/index.vue |
| `web/src/settings.ts` | 前端 | 关闭 fast-crud tableColumns 兼容警告 |
| `web/src/utils/service.ts` | 前端 | API 超时配置调整 |
| `web/package.json` | 前端 | @antv/g6 锁定 4.8.25 |
| `backend/application/celery.py` | 后端 | Celery 配置调整 |
| `backend/application/components/logging.py` | 后端 | 抑制 django_apscheduler.jobstores WARNING |
| `backend/application/components/rest_framework.py` | 后端 | 移除 SPECTACULAR_SETTINGS |
| `backend/common/management/commands/seed_reference.py` | 后端 | seed_dr_models 同步路径修正 |
| `backend/manage.py` | 后端 | 添加 warnings.filterwarnings 抑制 drf-spectacular 干扰 |
| `web/src/views/system/home/` | 前端 | 删除旧默认首页文件 |

### 解决

- **问题/背景：** CMDB 页面缺少 i18n 支持；G6 5.x 升级后不兼容回退 4.x；拓扑 tab 因 v-show 高度为 0 导致 fitView 溢出；旧首页 `/home` 指向 system/home 而非 portal
- **办法：** 创建 cmdb i18n zh-cn/en 文件并替换全部中文；G6 版本锁定 4.8.25 并恢复 TreeGraph/Graph 的 v4 API；拓扑 tab 改用 v-if 延迟渲染；route.ts 新增 /home 路由指向 portal

### 验证

- 改动类型: feat + refactor + chore
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `19e3e393`

> 提交日期: 2026-06-12 | 提交信息: feat: DR baseline — Process CMDB modeling, AI DR topology, CMDB i18n — 业务 DR 基础层建设

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | 后端 | DR 种子数据命令 — Process/DrSite/DrGroup 模型定义 + AssociationType + Host/DrSite/DrGroup Mock 数据 + BELONGS_TO/CALLS 自动建立 |
| `backend/agent/agent/process_manager.py` | 后端 | ProcessManager 类 — 定时 ss+ps 采集、CMDB API upsert、CALLS 关系自动发现、本地进程启停 |
| `backend/opsflow/plugins/process/process_start.py` | 后端 | 进程启动原子 — 从 CMDB 获取 command，通过 Tower 远程启动 |
| `backend/opsflow/plugins/process/process_stop.py` | 后端 | 进程停止原子 — 从 CMDB 获取 pid，通过 Tower 远程 kill |
| `backend/opsflow/plugins/process/process_status.py` | 后端 | 进程状态检查原子 — Tower 执行 ps + 解析输出为结构化字段 |
| `backend/opsflow/views/mixins/template_dr.py` | 后端 | DR pipeline 生成 API — AI 读取 Neo4j 拓扑生成切流 pipeline |
| `backend/opsflow/services/dr_service.py` | 后端 | DR 拓扑服务层 — Neo4j 查询 + AI Prompt + 拓扑描述构建 |
| `backend/cmdb/views/topology.py` | 后端 | AI 拓扑布局 API — LLM 分析行列 + 后端转像素坐标 |
| `backend/cmdb/services/topology_service.py` | 后端 | full_topology() 返回 attrs 字段供前端渲染 |
| `web/src/views/apps/cmdb/components/DrTopologyCanvas.vue` | 前端 | G6 力导向 DR 拓扑图 — DrSite/Host/Process 圆形节点 + SITE_CONTAINS/CALLS/FAILOVER_TO 着色边 + AI 布局按钮 |
| `web/src/views/apps/cmdb/components/DynamicTable.vue` | 前端 | i18n 替换 — 全部中文改为 t() 调用 |
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | 前端 | i18n 替换 — 右键菜单 + 属性标签 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | i18n 替换 + DR 拓扑 tab + DrGroup 下拉选择器 |
| `web/src/i18n/pages/cmdb/zh-cn.ts` | 前端 | CMDB 中文 i18n — 267 个 key |
| `web/src/i18n/pages/cmdb/en.ts` | 前端 | CMDB 英文 i18n — 267 个 key |
| `docs/guides/` (5 files) | 文档 | 跨 App 规范从 docs/opsflow/guides/ 迁移到 docs/guides/ |
| `docs/superpowers/specs/2026-06-12-process-cmdb-dr-baseline-design.md` | 文档 | DR 三阶段设计规范（Process CMDB + DrSite + AI 编排） |
| `docs/superpowers/specs/2026-06-12-ai-dr-topology-layout-design.md` | 文档 | AI 辅助 DR 拓扑布局设计 |

### 解决

- **问题/背景：** 主机进程信息缺失于 CMDB，无法在 DR 场景中感知进程拓扑和依赖关系；CMDB 无 i18n 支持；DR 拓扑无智能布局
- **办法：** ProcessManager 定时采集+上报；种子数据命令建立 DR 模型；G6 力导向图展示 DR 拓扑；AI 布局基于行列分析计算节点位置；CMDB 全页面 i18n

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-12-process-cmdb-dr-baseline-design.md`
  - `docs/superpowers/specs/2026-06-12-ai-dr-topology-layout-design.md`

### 验证

- 改动类型: feat + refactor + docs
- 清理乱码: 无
- 子 App index.md 更新: opsflow, cmdb（如适用）
- 工作区状态: 干净 ✅

---

## `66fa9493`

> 提交日期: 2026-06-12 | 提交信息: refactor: decouple variable registration — each app registers its own variable types — 变量注册解耦，各 app 自主注册变量类型

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/variable_types/__init__.py` | 后端 | 移除桥接导入 `from cmdb.variable_types import *`，消除 opsflow → cmdb 硬依赖 |
| `backend/cmdb/apps.py:ready()` | 后端 | 新增 `from cmdb import variable_types`，CMDB 自主注册变量类型 |

### 解决

- **问题/背景：** opsflow 通过桥接导入硬依赖 cmdb；其他子 app（itsm、monitor 等）想注册变量类型还得改 opsflow 代码
- **办法：** 改为各 app 在各自 `apps.py:ready()` 中自主注册变量类型，opsflow 只加载自身的 common 变量

### 文档

- **更新文档：**
  - `docs/cmdb/architecture/2026-06-12-variable-types-refactor.md` — 追加完整的变量注册全生命周期（启动→前端展示→模板配置→运行时解析）
  - `docs/opsflow/architecture/2026-06-12-variable-types-refactor.md` — 追加注册解耦说明及注册链对比

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 子 App index.md 更新: 无（本次不涉及新文件）
- 工作区状态: 干净 ✅

---

## `dde68d11`

> 提交日期: 2026-06-12 | 提交信息: refactor: rename variables/ to variable_types/ and migrate CMDB variables to cmdb app — 变量类型目录重构与 CMDB 变量领域拆分

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/variable_types/{query,topology,count}.py` | 后端 | CMDB 变量按功能拆分为 3 个独立文件，替代原 cmdb_variables.py 单文件 |
| `backend/opsflow/core/variables/ → variable_types/` (2 files) | 后端 | 目录重命名，variable_types 明确表达"变量类型定义"语义 |
| `backend/opsflow/core/variable_types/__init__.py` | 后端 | 桥接导入 `from cmdb.variable_types import *` |
| `backend/opsflow/plugins/registry.py` | 后端 | `discover_variables()` import 路径更新 |
| `backend/opsflow/tests/test_variable_registry.py` | 后端 | import 路径更新 |

### 解决

- **问题/背景：** `variables/` 目录名过于泛化，初看不知道是"什么变量"；`cmdb_variables.py` 在 cmdb app 内重复 cmdb 前缀；CMDB 变量类型领域错位在 opsflow 中
- **办法：** 目录名改为 `variable_types` 明确语义；CMDB 变量按功能拆分为 `query.py`/`topology.py`/`count.py` 三个文件；`opsflow/__init__.py` 通过 `from cmdb.variable_types import *` 桥接注册

### 文档

- **生成文档：**
  - `docs/opsflow/architecture/2026-06-12-variable-types-refactor.md`
  - `docs/cmdb/architecture/2026-06-12-variable-types-refactor.md`

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 子 App index.md 更新: opsflow, cmdb（已在上一轮手动更新）
- 工作区状态: 待确认 ✅

---

## `245ae88c`

> 提交日期: 2026-06-12 | 提交信息: feat: plugin hot-loading + i18n bilingual support — 插件热加载与中英文双语言支持

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/plugins/loader.py` | 后端 | PluginLoader 热加载引擎 |
| `backend/opsflow/management/commands/scan_plugins.py` | 后端 | 热加载触发管理命令 |
| `backend/opsflow/management/commands/backfill_plugin_en.py` | 后端 | 旧插件英文名自动补齐 |
| `backend/opsflow/plugins/base.py` | 后端 | BasePlugin 新增 name_en/description_en |
| `backend/opsflow/schema/form_schema.py` | 后端 | FormItem 新增 name_en |
| `backend/opsflow/models/plugin.py` | 后端 | PluginMeta 新增 name_en/description_en |
| `backend/opsflow/views/plugin_views.py` | 后端 | API 精简重构 |
| `backend/opsflow/plugins/common/send_email.py` | 后端 | 新增邮件通知原子 |
| `backend/opsflow/plugins/esxi/*.py` (6 files) | 后端 | 新增 ESXi 快照/克隆/磁盘/配置原子 |
| `web/src/i18n/pages/opsflow/*.ts` | 前端 | 扫描按钮 i18n key |
| `web/src/views/apps/opsflow/*.vue` (4 files) | 前端 | locale 驱动 name_en 显示 |

### 解决

- **问题/背景：** 新增插件必须重启服务；插件名称/描述/表单字段中文硬编码无法切换语言
- **办法：** PluginLoader 文件快照+增量注册实现热加载；后端 name_en 字段+前端 locale 判断实现中英文

### 验证

- 改动类型: feat + refactor
- 清理乱码: 有（删除 2 个 0 字节垃圾文件）
- 工作区状态: 干净 ✅

---

## `4471fe88`

> 提交日期: 2026-06-12 | 提交信息: refactor: unify ansible plugin execution through Tower REST API — Ansible 插件统一通过 Tower 异步调度执行

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/plugins/ansible/tower_backend/` (6 files) | 后端 | 新增 Tower 执行后端包：TowerService+TowerBasePlugin+自适应轮询+WS推送 |
| `backend/opsflow/plugins/ansible/shell.py` | 后端 | ShellPlugin 从 BasePlugin 改为 TowerBasePlugin 异步调度 |
| `backend/opsflow/plugins/ansible/file_copy.py` | 后端 | FileCopyPlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/script_exec.py` | 后端 | ScriptExecPlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/upload_file.py` | 后端 | UploadFilePlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/nginx_reload.py` | 后端 | NginxReloadPlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/service_control.py` | 后端 | ServiceControlPlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/backup_file.py` | 后端 | BackupFilePlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/java_deploy.py` | 后端 | JavaDeployPlugin → TowerBasePlugin |
| `backend/opsflow/plugins/ansible/docker_deploy.py` | 后端 | DockerDeployPlugin → TowerBasePlugin |
| `backend/opsflow/core/tower/` (5 files) | 后端 | 已删除，迁移至 plugins/ansible/tower_backend/ |
| `backend/opsflow/core/ansible_trigger.py` | 后端 | 已删除，逻辑合并到 TowerBasePlugin |
| `backend/opsflow/core/tower_service.py` | 后端 | 已删除，重导出 shim |
| `docs/opsflow/features/2026-06-12-tower-backend-exec-engine.md` | 文档 | Tower 后端功能文档 |
| `docs/opsflow/architecture/2026-06-12-ansible-plugin-tower-refactor.md` | 文档 | 重构架构文档 |

### 解决

- **问题/背景：** Ansible 插件存在双执行路径（本地 subprocess + Tower REST API），core/tower/ 独立于插件系统，同一原子需维护两套逻辑
- **办法：** 新增 TowerBasePlugin 基类，9 个 ansible 插件统一继承；execute() 触发 Tower Job → schedule() 自适应轮询 → rollback() 取消作业；Tower 未配置时自动降级为 mock 执行

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-12-tower-backend-exec-engine.md`
  - `docs/opsflow/architecture/2026-06-12-ansible-plugin-tower-refactor.md`

### 验证

- 改动类型: refactor + feat
- 清理乱码: 有（删除 1 个 0 字节垃圾文件 backend/dict）
- 工作区状态: 干净 ✅

---

## `f234a766`

> 提交日期: 2026-06-12 | 提交信息: feat: add AI text generation atom plugin — 新增 AI 文本生成原子插件

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/plugins/ai/ai_text_gen.py` | 后端 | AiTextGenPlugin — 新 AI 分组文本生成原子 |
| `backend/opsflow/plugins/ai/__init__.py` | 后端 | AI 插件包标记 |
| `docs/superpowers/specs/2026-06-12-ai-text-gen-atom-design.md` | 文档 | AI 原子设计规范 |

### 解决

- **问题/背景：** 流程引擎缺少 AI 文本生成能力，无法在自动化流程中调用 LLM
- **办法：** 新增 BasePlugin 子类，复用 OPSAGENT DeepSeek 配置和现有的插件发现/注册/执行链路；考虑 bamboo-engine string inputs 特性做类型安全转换

### 验证

- 改动类型: feat
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `a7d29650`

> 提交日期: 2026-06-10 | 提交信息: docs: add config governance standards — 新增配置治理规范（决策树+组件对照表）

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/superpowers/specs/2026-06-10-config-governance-design.md` | 文档 | **新建** — 配置治理设计文档，定义 4 类场景的配置变更流程（决策树+分场景规则+辅助原则） |
| `docs/opsflow/guides/project-standards.md` | 文档 | 新增「配置治理规范」章节，含配置放置决策树、9 个组件文件对照表、3 条强制规则 |

### 解决

- **问题/背景：** 配置体系重构完成后（conf/分层 + components/组件化），缺少明确的配置变更流程规则，开发者不知该改哪个文件、如何跨环境覆写
- **办法：** 定义配置放置决策树（env值→base/environments、Django结构→components、App注册→INSTALLED_APPS、新类别→新建组件），配套组件对照表和强制规则，落地到 project-standards.md

### 验证

- 改动类型: docs
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `364b6ce7`

> 提交日期: 2026-06-12 | 提交信息: feat: add node input tracing and node_type to execution traces — 节点入参追踪 + 节点类型输出

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `opsflow/signals/trace.py` | 后端 | 新增 _capture_node_inputs() 从 template_snapshot 读取 params；创建 trace 时写入 node_type/node_label |
| `opsflow/core/node_dispatcher.py` | 后端 | get_trace() 返回值新增 inputs + node_type |
| `opsflow/serializers.py` | 后端 | get_trace_summary() 返回值新增 inputs + node_type |
| `docs/superpowers/specs/2026-06-11-node-input-tracing-design.md` | 文档 | **新建** — 节点入参追踪设计文档 |
| `application/tests/test_ws_unification.py` | 后端 | WebSocket 测试改用 InMemoryChannelLayer |
| `useGraphCanvas.ts` | 前端 | 移除未使用的引用，简化 label 获取 |
| `types/index.ts` | 前端 | 移除未使用的 OutputField 接口 |

### 解决

- **问题/背景：** 前端 Data tab 的 Inputs 始终显示 "No data"，因为 trace.inputs 从未被写入；同时前端无法区分网关节点（无入参出参）和业务节点
- **办法：** 新增 _capture_node_inputs() 从 template_snapshot 读取节点 params，在 FINISHED/FAILED 时写入 trace.inputs；node_type 在创建 trace 时一并写入，API 返回时带上

### 验证

- 改动类型: feat
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `696b0e57`

> 提交日期: 2026-06-11 | 提交信息: refactor: unify variable binding and simplify pipeline builder — 变量绑定统一重写，pipeline builder 精简

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `opsflow/core/pipeline_builder/conditions.py` | 后端 | **删除** — 136 行条件预处理逻辑，内联到 _create_element() |
| `opsflow/core/pipeline_builder/__init__.py` | 后端 | 消除 node_output_specs 中间变量；Data 直写；build_bamboo_pipeline 不再返回 tuple |
| `opsflow/core/pipeline_builder/elements.py` | 后端 | 消除 (element, specs) 中间元组；conditional refs 修复白名单 bug |
| `opsflow/core/plugin_service_adapter.py` | 后端 | 删除 _promote_results 中 ContextValue 重复写入；删除 import json |
| `opsflow/core/variable_resolver.py` | 后端 | 删除 resolve_params()（不再被调用） |
| `opsflow/core/flow_engine.py` | 后端 | 不再 tuple unpack build_bamboo_pipeline 返回值 |
| `application/settings.py` | 配置 | 取消 PLUGINS_URL_PATTERNS 注释以修复配置错误 |
| `.gitignore` | 配置 | 添加 0 字节乱码文件过滤 |

### 解决

- **问题/背景：** 变量解析是"双轨制"（bamboo-engine SPLICE + 手动正则替换），重复劳动且容易不一致。conditions.py 是独立预处理阶段，增加复杂性
- **办法：** 一次性统一为 bamboo-engine SPLICE 机制：global_vars 展开为独立 key、params 按 get_var_types() 分发 SPLICE/PLAIN、条件内联生成、Data 直写消除中间变量

### 验证

- 改动类型: refactor
- 清理乱码: 有（`0` 0 字节垃圾文件）
- 工作区状态: 干净 ✅

---

## `4ca4a835`

> 提交日期: 2026-06-10 | 提交信息: refactor: extract settings.py into domain components — settings.py 按领域拆分为 9 个组件文件

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 配置 | 593 行 → 198 行（-67%），仅保留 Django 骨架 + App 注册 |
| `backend/conf/env.py` | 配置 | 重写为动态加载入口：先加载 base，再根据 DJANGO_ENV 执行环境覆写 |
| `backend/conf/env_base.py` | 配置 | **新建** — 共享变量定义 + 默认值 |
| `backend/conf/env_dev.py` | 配置 | **新建** — 开发环境覆写（当前实际值） |
| `backend/conf/env_uat.py` | 配置 | **新建** — UAT 占位 |
| `backend/conf/env_prod.py` | 配置 | **新建** — 生产占位 |
| `backend/conf/env.example.py` | 配置 | 清理为纯模板（移除默认凭据） |
| `backend/application/components/database.py` | 配置 | **新建** — DATABASES / Neo4j / CACHES |
| `backend/application/components/logging.py` | 配置 | **新建** — LOGGING 字典（97 行） |
| `backend/application/components/rest_framework.py` | 配置 | **新建** — DRF / Spectacular / JWT |
| `backend/application/components/auth.py` | 配置 | **新建** — 登录 / OAuth2 / 验证码 |
| `backend/application/components/channels.py` | 配置 | **新建** — CHANNEL_LAYERS / ASGI |
| `backend/application/components/cors_security.py` | 配置 | **新建** — CORS 跨域 |
| `backend/application/components/monitor_adapters.py` | 配置 | **新建** — Monitor SPI |
| `backend/application/components/celery.py` | 配置 | **新建** — Celery 队列 / Broker |
| `backend/application/components/pipeline.py` | 配置 | **新建** — Pipeline 引擎配置 |

### 解决

- **问题/背景：** settings.py 593 行混入 15+ 区块，新增配置不知放哪；conf/env.py 单文件无法按环境切换
- **办法：** 按 Django 领域拆分为 9 个 component 文件，conf/ 改为分层结构（base + 环境覆写），settings.py 缩为 import 聚合入口

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `80a7b575`

> 提交日期: 2026-06-10 | 提交信息: refactor: clean env.example.py — 移除默认凭据，完善多环境配置模板

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/conf/env.example.py` | 配置 | 重写 — 移除 root/123456 默认凭据（安全改进），新增 OpsFlow 调度器/LLM/Ansible/Neo4j 配置区块，补充 env_dev/uat/prod 多环境说明 |

### 解决

- **问题/背景：** env.example.py 长期未更新，使用 sqlite3 默认、root/123456 凭据硬编码，缺少 OpsFlow 特有配置（调度器/LLM/Ansible/Neo4j），新增 App 不知该配什么
- **办法：** 整体重构：移除所有默认值（仅留占位空串），按领域分组（DB/Redis/邮件/调度器/LLM/Ansible/Neo4j），补充多环境说明索引

### 验证

- 改动类型: refactor
- 清理乱码: 有（`6`、`Retry`、`**日期:**`、`**状态:**` 空文件）
- 工作区状态: 干净 ✅

---

## `4648d591`

> 提交日期: 2026-06-10 | 提交信息: refactor: unify seed commands into bootstrap + seed_reference — 统一数据初始化入口，删除 10 个分散的 seed 命令

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/common/management/commands/bootstrap.py` | 后端 | **新建** — 统一引导命令，分 3 阶段（系统核心/参考数据/演示数据），支持 --essential-only/--demo-only/--phase/--force 参数 |
| `backend/common/management/commands/seed_reference.py` | 后端 | **新建** — 聚合 9 个旧 seed 命令，562 行统一管理所有参考数据 |
| `backend/*/seed_*.py` (×7) | 后端 | **删除** — seed_template_categories, seed_knowledge, seed_sample_template, opsflow_migrate_projects, seed_cmdb_models, seed_monitor, seed_connector_definitions |
| `backend/*/add_*_menu.py` (×3) | 后端 | **删除** — add_app_menus, add_iam_menu |
| `docs/opsflow/guides/mock-data-guide.md` | 文档 | 重写 — 从仅 ORM mock 改为完整数据初始化指南，覆盖 bootstrap 统一入口、3 阶段流程、开发约束 |
| `OPSFLOW.md` | 文档 | 新增部署规范章节，引用 mock-data-guide 和数据初始化规范 |
| `docs/superpowers/specs/2026-06-10-config-architecture-design.md` | 文档 | **新建** — 配置体系重构设计文档（多环境/密钥管理/settings 拆分） |

### 解决

- **问题/背景：** 数据初始化散落在 10 个独立的 management command 中，开发者需要知道执行顺序和依赖关系；新增数据模型需新建一个 seed 命令，维护成本高
- **办法：** 统一为 bootstrap.py（入口编排）+ seed_reference.py（所有参考数据聚合）两层架构，删除全部旧命令；mock-data-guide 同步更新为完整的数据初始化指南

### 验证

- 改动类型: refactor
- 清理乱码: 有
- 工作区状态: 干净 ✅

---

## `b026452f`

> 提交日期: 2026-06-10 | 提交信息: refactor: split OPSFLOW.md and slim CLAUDE.md — OPSFLOW.md 按领域拆分，CLAUDE.md 精简

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `CLAUDE.md` | 文档 | 精简 41 行 — 移除架构/API 规范/日志等低频内容，改为指向拆分后的规范文件 |
| `OPSFLOW.md` | 文档 | 361 行 → 17 行轻量索引，原内容按领域拆分为 3 个独立文件 |
| `docs/opsflow/guides/frontend-style-guide.md` | 文档 | **新建** — 前端规范合集（SCSS/Vue/i18n/TS/按钮/Pinia，210 行） |
| `docs/opsflow/guides/project-standards.md` | 文档 | **新建** — 工程规范合集（架构/项目结构/后端分层/API/错误处理，173 行，含数据初始化规范） |
| `docs/opsflow/guides/process-standards.md` | 文档 | **新建** — 流程规范合集（Git/文档/设计约束，82 行） |

### 解决

- **问题/背景：** CLAUDE.md（99 行）含大量低频内容（架构布局、API 规范、日志约定），每次会话都注入浪费上下文；OPSFLOW.md（361 行）混合前端风格、后端工程、流程治理三类不相关内容，Claude 需完整加载才能找到所需信息
- **办法：** 按领域拆分为 3 个独立规范文件，按需加载；CLAUDE.md 仅保留高频内容（项目规则、Agent 协调、MCP 工具）和索引引用；OPSFLOW.md 改为轻量导航

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `28c16f75`

## `d2cf3d83`

> 提交日期: 2026-06-10 | 提交信息: refactor: unify SCSS architecture and standardize button styles — SCSS 架构统一 & 按钮风格规范

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `OPSFLOW.md` | 文档 | 更新 SCSS 规范（$g-*/@use styles/global）和按钮风格规范 |
| `web/src/styles/_tokens.scss` | 样式 | **新文件** — 全局设计令牌（$g-* 变量，合并 sys 和 of 两套） |
| `web/src/styles/_mixins.scss` | 样式 | **新文件** — 全局 mixin（g-hover-lift/g-dialog-header 等） |
| `web/src/styles/_components.scss` | 样式 | **新文件** — 全局 class（.g-card/.g-fade-in-up 等） |
| `web/src/styles/global.scss` | 样式 | **新文件** — 统一入口（@forward 三个 partials） |
| `web/src/styles/opsflow-*.scss` | 样式 | **删除** — 旧两套 SCSS 系统（opsflow-global/opsflow-variables） |
| `web/src/views/system/styles/system-global.scss` | 样式 | **删除** — 旧 system-global SCSS |
| `web/` (70+ .vue 文件) | 前端 | 全部 @use 路径改为 `/@/styles/global`；$sys-*/$of-* → $g-*；.sys-*/.of-* → .g-*；mixin 同步改名 |
| `web/` (44 .vue 文件) | 前端 | 按钮规范统一：行内 text type="primary" → text；弹窗移除 size="small"；primary 加图标；工具栏加图标 |

### 解决

- **问题/背景：** 项目有两套并行的 SCSS 系统（opsflow-* 45 文件 + sys-* 7 文件），值几乎相同但命名不同，开发者选择困难、UI 有不一致、维护需改两处。同时按钮风格不统一（大小混用、79% 无图标、行内按钮写法混乱）
- **办法：** 一次性合并为三层架构（tokens + mixins + components），前缀统一 g-；通过自动化脚本批量重命名 70+ 文件的变量/class/mixin；按 OPSFLOW.md 规范统一按钮大小/类型/图标

### 验证

- 改动类型: refactor
- 清理乱码: 有（fix_buttons.py/fix_buttons_v2.py 临时脚本）
- 工作区状态: 干净 ✅
- Vite build 零错误 ✅ (32.92s)

---

## `99c70038`

> 提交日期: 2026-06-09 | 提交信息: chore: remove deprecated USE_L10N setting — 移除 Django 5.0 已废弃的 USE_L10N

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 配置 | 删除 USE_L10N = True 死代码（Django 5.0 已移除） |

### 解决

- **问题/背景：** USE_L10N 在 Django 5.0 已被移除，当前 Django 5.2.15 中该设置不再生效，是死代码
- **办法：** 直接删除该行

### 验证

- 改动类型: chore
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `1094e415`

> 提交日期: 2026-06-09 | 提交信息: feat: enable USE_TZ=True and refactor opsflow SCSS imports — 激活时区支持及样式文件迁移

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 配置 | USE_TZ = False → True，激活 Django 时区感知 |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 删除 _naive() 时区剥离函数，4 处调用直接使用 aware datetime |
| `backend/opsflow/core/flow_engine.py` | 后端 | started_at/ended_at 赋值改用 timezone.now()（3 处） |
| `backend/opsflow/signals/handlers.py` | 后端 | ended_at 赋值改用 timezone.now()（3 处） |
| `backend/opsflow/signals/timeout.py` | 后端 | 超时 deadline 计算改用 timezone.now() + timedelta |
| `backend/opsflow/core/node_timeout_strategy.py` | 后端 | 超时 deadline 计算改用 timezone.now() + timedelta |
| `backend/opsflow/views/dashboard_views/stats.py` | 后端 | 删除 now_naive 兼容代码，直接使用 timezone.now() |
| `backend/opsagent/views/run.py` | 后端 | session_id/ended_at 改用 timezone.now()（3 处） |
| `backend/iam/views.py` | 后端 | reviewed_at 赋值改用 timezone.now()（2 处） |
| `backend/dvadmin/system/views/login.py` | 后端 | 验证码过期比较改用 timezone.now() |
| `backend/common/management/commands/add_mock_neo4j.py` | 后端 | datetime.utcnow() → timezone.now() |
| `backend/opsflow/management/commands/fix_timezone_data.py` | 后端 | **新文件** — 数据迁移命令，对现有 naive 数据减 8h 转换 |
| `web/scripts/migrate_opsflow_styles.py` | 脚本 | **新文件** — SCSS 样式迁移助手 |
| `web/src/styles/opsflow-global.scss` | 样式 | **迁移** — 从 opsflow/styles/ 移至全局 styles/ |
| `web/src/styles/opsflow-variables.scss` | 样式 | **迁移** — 从 opsflow/styles/ 移至全局 styles/ |
| `web/` (44 个 .vue 文件) | 前端 | @use 导入路径更新为 `../../../styles/` 等匹配新路径 |

### 解决

- **问题/背景：** 项目 USE_TZ=False 导致所有 datetime 为 naive 值，Django 5.2 对 naive datetime 将触发 RuntimeWarning；多处存在 _naive() 补偿代码。同时 opsflow SCSS 文件位于 views/apps/opsflow/styles/ 下，跨组件引用路径混乱
- **办法：** 分两阶段：(1) 时区：settings.py 切换 + 删除 _naive() + 10 个文件中所有 datetime.now() 替换为 timezone.now() + 创建 fix_timezone_data.py 数据迁移命令；(2) 样式：将 SCSS 文件迁移到 web/src/styles/，全部 44 个 Vue 组件 @use 路径重写

### 验证

- 改动类型: feat
- 清理乱码: 有（`self.image_code.expiration` 0 字节 + `web/resolves` 0 字节）
- 工作区状态: 干净 ✅

---

## `a16dfd3c`

> 提交日期: 2026-06-09 | 提交信息: chore: clean up unused dependencies from requirements — 移除 tqsdk、influxdb、sqlalchemy

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/requirements.txt` | 配置 | 移除未使用的 tqsdk、tqsdk-ctpse、tqsdk-sm、influxdb、influxdb-client、sqlalchemy |
| `backend/requirements_prod.txt` | 配置 | 同步移除，修复 `<blank>` 占位符文本 |

### 解决

- **问题/背景：** requirements.txt 中残留了大量非 opsflow 项目使用的 Python 依赖（tqsdk 期货交易、influxdb 时序数据库、sqlalchemy ORM），增加部署体积和依赖冲突风险
- **办法：** 逐包核查代码引用，确认无 import 后从 requirements 移除并从 venv 卸载

### 验证

- 改动类型: chore
- 清理乱码: 有 — 修复了 Edit 操作遗留的 `<blank>` 占位符文本
- 工作区状态: 干净 ✅

---

## `77c26c51`

> 提交日期: 2026-06-08 | 提交信息: docs: add debug-doc-writer skill and exclusive gateway debug documentation

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `.claude/skills/debug-doc-writer/SKILL.md` | 配置 | 新增 debug-doc-writer 技能，自动提取调试排障过程生成结构化 MD 文档 |
| `docs/opsflow/debug/2026-06-08-exclusive-gateway-condition-output.md` | 文档 | 新增排他网关条件评估与节点输出显示调试全记录，涵盖时序竞态/数据注入/前端显示 3 个根因 |

### 解决

- **问题/背景：** 需要规范化记录调试排障过程到结构化文档；之前 commit 24691761 的调试分析需生成可复用的 debug 文档
- **办法：** 创建 debug-doc-writer 技能（含完整的工作流模板），依据提交历史重新整理排他网关条件评估与节点输出显示的根因分析、解决方案和验证方法

### 验证

- 改动类型: docs
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `24691761`

> 提交日期: 2026-06-08 | 提交信息: feat: implement exclusive gateway condition evaluation and output display

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/plugin_service_adapter.py` | 后端 | 重写 `_promote_result` → `_promote_results`，支持排他网关条件变量注入 ContextValue 表，同时将 outputs 写入 execution.context |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | build_bamboo_pipeline 返回 auto_vars 映射；传递 execution_id；修复 NodeOutput 变量注入 key 格式 |
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | `_create_element` 接收 execution_id 注入到每个节点 inputs |
| `backend/opsflow/core/flow_engine.py` | 后端 | 接收 auto_vars 并存入 execution context |
| `backend/opsflow/plugins/common/test_print_time.py` | 后端 | 添加 test1 随机输出(1-10)和 get_output_schema |
| `backend/opsflow/signals/trace.py` | 后端 | `_capture_node_outputs` 从 execution.context 读取，避开 bamboo-engine 的 ExecutionData 时序问题 |
| `backend/opsflow/serializers.py` | 后端 | get_trace_summary 包含 outputs 字段 |
| `backend/opsflow/core/node_dispatcher.py` | 后端 | get_trace 查询包含 outputs 字段 |
| `backend/application/settings.py` | 配置 | apscheduler 日志降级到 WARNING |
| `web/` (5 个文件) | 前端 | 条件下拉显示节点.变量名；PropertyPanel 通过 getGraphData 获取节点；边 label 持久化；日志/输出样式浅色主题 |

### 解决

- **问题/背景：** 排他网关条件表达式 `${_gwcond_node_1_test1} > 5` 评估失败（context 为空），节点 outputs 无法显示（No outputs）。根因：1) auto_vars 映射未被返回和持久化；2) bamboo-engine 的 ExecutionData 时序问题（信号在持久化前触发）
- **办法：** pipeline builder 返回 auto_vars 映射存入 execution.context；_promote_results 写入 ContextValue 表（格式化 ${} 匹配引擎 ref）和 execution.context['_node_outputs']；trace 从后者读取 outputs；前端的边 label 持久化修复、条件变量下拉显示节点名

### 验证

- 改动类型: feat
- 清理乱码: 有（`backend/None` 0 字节垃圾文件）
- 工作区状态: 干净 ✅

---

## `3b3666ba`

> 提交日期: 2026-06-07 | 提交信息: fix: correct remaining cross-subdirectory component imports in Vue components

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue` | 前端 | 修复 5 个跨子目录组件引用（./ → ../panels/, ../badges/, ../common/, ../dialogs/） |
| `web/src/views/apps/opsflow/components/gates/ConditionRow.vue` | 前端 | VariablePicker 引用路径 ./ → ../panels/ |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 前端 | ConditionDialog 引用路径 ./ → ../gates/ |

### 解决

- **问题/背景：** 上一轮修复（../ → ../../）遗漏了 components/canvas/、components/gates/ 和 components/panels/ 中跨子目录引用的本地组件（./PropertyPanel 实际在 panels/、./ConditionDialog 实际在 gates/ 等）
- **办法：** 对 3 个文件中 7 处 ./ 跨子目录引用修正为正确的相对路径

### 验证

- 改动类型: fix
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `f01b6b1c`

> 提交日期: 2026-06-07 | 提交信息: fix: correct Vue component import paths and simplify DB_HOST config

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 后端 | DB_HOST 固定为 127.0.0.1，去掉动态 IP 检测逻辑 |
| `web/src/views/apps/opsflow/components/*/` (20 个 .vue 文件) | 前端 | 修复组件子目录中的相对导入路径（`../` → `../../`），涉及 js import（api/stores/composables/utils）和 scss @use（styles/） |

### 解决

- **问题/背景：** 前端组件目录结构拆分为二级子目录（如 `components/canvas/`、`components/dialogs/` 等）后，`../` 路径错误地指向了 `components/` 而非 `opsflow/`
- **办法：** 将所有 `components/*/` 子目录中的 `from '../xxx/'` 和 `@use '../styles/'` 改为 `from '../../xxx/'` 和 `@use '../../styles/'`

### 验证

- 改动类型: fix
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `53363292`

> 提交日期: 2026-06-07 | 提交信息: refactor: complete project restructure cleanup

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/doc/*` (已删除) | 文档 | 旧文档已迁移到 `docs/architecture/`，清理残留 |
| `tools` (git 索引条目) | 杂项 | 移除残留的 `tools` 空条目（`backend/scripts/` → `backend/tools/` 重命名产生的） |
| 10 个 `.vue` 文件 | 前端 | 更新 import 路径以匹配组件子目录拆分 |
| `.vite/` | 缓存 | 删除 Vite 缓存目录 |

### 解决

- 完成项目结构重构的收尾清理，消除所有残留文件和索引异常

### 验证

- 改动类型: refactor
- 清理乱码: 有（`tools` 索引条目 + `.vite/` 缓存）
- 工作区状态: 干净 ✅

---

## `592db305` — `3030afef` — `70199fa7` — `99432840` — `de01d17c`

> 提交日期: 2026-06-07 | 项目全面代码结构重构

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `reference/` | 目录 | bk-cmdb, bk-itsm, bk-job, bk-sops, bamboo-engine 移入（.gitignore 排除） |
| `deploy/` | 目录 | docker-compose.yml, Dockerfile, nginx.conf 集中管理 |
| `backend/tools/` | 目录 | 原 `backend/scripts/` 重命名，避免与根目录 `scripts/` 冲突 |
| `docs/` | 目录 | 合并 5 处分散文档（`architecture/`、`design/`、`knowledge/`） |
| `.claude/skills/` | 配置 | 47 个技能从用户级迁移到项目级 |
| `.claude/.gitignore` | 配置 | 仅 `skills/` 可推送，`plans/`、`worktrees/`、`settings.local.json` 排除 |
| `CLAUDE.md` | 文档 | 路径更新（reference/、docs/、deploy/） |
| `OPSFLOW.md` | 文档 | 新增完整项目结构规范（目录职责、后端模板、前端拆分） |
| `opsflow/components/` | 前端 | 21 个组件拆入 8 个子目录（canvas/、dialogs/、panels/ 等） |
| 13 个 `.vue` / `.ts` 文件 | 前端 | 更新组件 import 路径 |

### 解决

- **问题：** 根目录杂乱（蓝鲸源码、部署配置混在一起）；文档分散；技能在用户级，其他开发者用不了；组件平铺 21 个文件
- **办法：** 5 阶段全量规范化，`git mv` 保持历史，分步提交逐步验证

### 验证

- 改动类型: refactor
- 后端测试: 264 passed ✅
- TypeScript: 无类型错误 ✅
- Vite: 241ms 启动，零 Sass 警告 ✅

---

## `a8a0805a`

> 提交日期: 2026-06-07 | 提交信息: fix: silence Sass legacy-js-api deprecation warning on Vite 8

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/vite.config.ts` | 配置 | `api: 'modern-compiler'` → `silenceDeprecations: ['legacy-js-api']` |

### 解决

- **问题/背景：** `api: 'modern-compiler'` 选项在 Vite 8 中被忽略，Sass legacy-js-api 警告依然出现。
- **办法：** 改用 sass 原生 `silenceDeprecations` 选项，兼容所有 Vite 版本的 Sass 警告静默。

### 验证

- 改动类型: fix
- 清理乱码: 有（`提交日期` 空文件 + `.vite/` 缓存目录）
- 工作区状态: 干净 ✅
- Vite 启动零 Sass 警告 ✅

---

## `8c2c3fa7`

> 提交日期: 2026-06-07 | 提交信息: refactor: migrate from Sass @import to @use — 消除全部 Sass 弃用警告

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/vite.config.ts` | 配置 | 添加 `scss.api: 'modern-compiler'` 消除 legacy-js-api 警告 |
| `web/src/**/*.scss` (18 文件) | 样式 | `@import` → `@use ... as *` 迁移 |
| `web/src/**/*.vue` (31 文件) | 样式 | `@import` → `@use ... as *` 迁移 |
| `opsflow-global.scss` | 样式 | 添加 `@forward` 确保变量穿透到 .vue `<style>` |

### 解决

- **问题/背景：** Dart Sass 2.0.0 将移除 `@import`，3.0.0 将移除 legacy JS API。开发服务器启动时产生约 50 行弃用警告，干扰正常日志查看。
- **办法：** 全局批量替换 `@import` → `@use ... as *`，同时配置 Vite 使用 `modern-compiler` API。

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 工作区状态: 干净 ✅
- Vite 启动零 Sass 警告 ✅

---

## `f74f9ed8` — `deee0667` — `7277bf0b`

> 提交日期: 2026-06-07

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/signals/handlers.py` | 后端 | 新增 `_push_node_status_via_ws()` 函数；信号中调用 WS 推送 |
| `backend/opsflow/signals/state.py` | 后端 | 移除 `id_map` 查找，直接使用 `node_id` |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | 删除 `_build_id_map()`；Start/End 事件传入 X6 ID；合成网关使用可识别 ID |
| `backend/opsflow/core/flow_engine.py` | 后端 | 移除 `node_id_map` context 字段 |
| `backend/opsflow/core/layout/layout_adapter.py` | 后端 | 移除残留的 `node_id_map` 死代码 |
| `backend/opsflow/tests/test_gateway_signal.py` | 后端 | 新增 `TestWsNodeStatusPush` 测试类 |
| `backend/opsflow/tests/test_bamboo_builder.py` | 后端 | 更新测试，直接断言原始 ID |
| `backend/opsflow/tests/test_gateway_execution.py` | 后端 | 更新测试 |
| `backend/opsflow/tests/test_parallel_gateway.py` | 后端 | 更新测试 |
| `backend/opsflow/doc/debug/node-coloring-debug.md` | 文档 | 新增详细的节点着色全过程文档 |
| `web/package.json` | 前端 | X6 v3.1.7 + 移除全部插件包 |
| `web/src/utils/websocket.ts` | 前端 | `onmessage` 中自动分发 NODE_STATUS 到 mittBus |
| `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 前端 | 订阅 `nodeStatusChange`；修复日志 limit 参数名 |
| `web/src/views/apps/opsflow/components/MonitorCanvas.vue` | 前端 | 新增 `updateNodeStatus`；running 闪烁动画；边动画改为 animate API |
| `web/src/views/apps/opsflow/composables/useDesignCanvas.ts` | 前端 | 插件导入合并；修复 Selection rubberband 冲突 |
| `web/src/views/apps/opsflow/components/DesignCanvas.vue` | 前端 | 移除 3 行 CSS 导入 |
| `web/src/types/mitt.d.ts` | 前端 | 新增 `nodeStatusChange` 事件类型 |

### 解决

- **X6 版本废弃 (v2.19.1 → v3.1.7):** 合并 7 个插件包到核心包；移除外部 CSS 导入（v3 自动注入）；边动画改用 `animate()` + `iterations: Infinity`
- **画布无法拖拽:** `Selection` 配置加 `modifiers: 'shift'`，解冲突
- **节点着色滞后:** 新增 WebSocket 实时推送 `NODE_STATUS` 消息；websocket.ts 自动分发到 mittBus；10s 轮询保留为回退
- **Running 无反馈:** 0.6s CSS 快速闪烁动画（`ops-blink`）
- **冗余 ID 映射:** 删除 `_build_id_map()` 和 `node_id_map`；X6 ID 直接穿透
- **`layout_adapter.py` 残留:** 移除未使用的 `node_id_map` 局部变量

### 验证

- 后端 111 个测试全部通过 ✅
- 前端 TypeScript 类型检查无错误 ✅
- Vite 开发服务器正常启动 ✅
