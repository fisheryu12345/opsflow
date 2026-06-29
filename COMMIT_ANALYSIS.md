# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## cfd91ce2

> 提交日期: 2026-06-29 | 提交信息: feat: complete i18n fields for agent/aliyun/ansible plugins

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| plugins/agent/*.py (5 files) | 后端 | FormItem 添加 name_en + placeholder_en |
| plugins/aliyun_ecs/*.py (8 files) | 后端 | FormItem 添加 name_en + placeholder_en，类补齐 icon + color |
| plugins/ansible/*.py (9 files) | 后端 | 类补齐 name_en + icon + color，FormItem 添加 name_en + placeholder_en |

### 解决

- **问题/背景：** Agent/Aliyun/Aliyun ECS/Ansible 三类插件共 22 个文件缺少英文标签（name_en/placeholder_en）和前端展示图标（icon/color），导致英文模式下标签缺失、节点图标空白
- **办法：** 逐文件补齐 FormItem 的 name_en 和 placeholder_en；类级别补齐 name_en、icon、color

### 文档

- **生成文档：** 无（非功能新增，跳过）

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## 8716aefe

> 提交日期: 2026-06-28 | 提交信息: docs: fix placeholder hash in optional-skip feature doc

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| docs/opsflow/features/2026-06-28-optional-skip-on-fail.md | 文档 | `(待提交)` → `bae59bcc` |

### 解决

- **问题/背景：** feature 文档中有未替换的 `(待提交)` 占位符
- **办法：** 替换为实际 commit hash bae59bcc

### 验证

- 改动类型: docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## bae59bcc

> 提交日期: 2026-06-28 | 提交信息: test: add optional skip unit + integration tests — Optional 节点跳过测试 + 功能文档

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| backend/opsflow/tests/test_optional_skip.py | 测试 | 10 个测试覆盖 _check_optional_skip（7 单元）+ 信号集成（3） |
| docs/opsflow/features/2026-06-28-optional-skip-on-fail.md | 文档 | Optional 节点失败自动跳过功能文档 |
| docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md | 文档 | 修复 merge conflict 残留 |
| COMMIT_ANALYSIS.md | 文档 | 更新 8e58d2cb 条目补全改动描述 |

### 解决

- **问题/背景：** Optional skip-on-fail 代码已提交（8e58d2cb），但配套测试和功能文档缺失
- **办法：** 补齐 10 个测试 + feature 文档

### 文档

- **生成文档：**
  - docs/opsflow/features/2026-06-28-optional-skip-on-fail.md

### 验证

- 改动类型: test + docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 8e58d2cb

> 提交日期: 2026-06-28 | 提交信息: fix: enable clearable for async_select dropdown

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| web/src/components/RenderForm/tags/TagAsyncSelect.vue | 前端 | clearable 默认值 false→true |
| backend/opsflow/signals/handlers.py | 后端 | 新增 _check_optional_skip() + FAILED 分支集成，Optional 节点失败自动跳过 |
| web/src/views/apps/opsflow/components/panels/PropertyPanel.vue | 前端 | Optional/max_retries 互斥，retry 开启时 optional 禁用，反之亦然 |
| docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md | 文档 | 新建调试文档 |

### 解决

- **问题/背景：** async_select 下拉选中后无法清除；Optional 开关只在冲突检测中有效，实际执行无 skip-on-fail 功能；前端 Optional 和 Retry 同时启用语义矛盾
- **办法：** TagAsyncSelect clearable=true；signal handler 中拦截 FAILED 检查 optional 标志自动调 FlowEngine.skip()；前端 :disabled 双向互斥

### 文档

- **生成文档：**
  - docs/opsflow/debug/2026-06-28-async-select-clearable-fix.md

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端组件 + 文档）
- 工作区状态: 干净 ✅

---

## 4fbb2c87

> 提交日期: 2026-06-28 | 提交信息: refactor: remove execution rollback functionality — 移除所有执行回滚代码

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| core/flow_engine.py | 后端 | 删除 rollback_failed_nodes()、_trigger_plugin_rollback()，简化 _fail_execution() |
| core/plugin_service_adapter.py | 后端 | 删除 PluginService.rollback() 方法 |
| signals/handlers.py | 后端 | 删除 FAILED 分支中的 rollback 触发 |
| plugins/base.py | 后端 | 删除 BasePlugin.rollback() 默认实现 |
| plugins/esxi/*.py (8个) | 后端 | 删除各插件 rollback() 方法 |
| plugins/aliyun_ecs/*.py (4个) | 后端 | 删除各插件 rollback() 方法 |
| plugins/ansible/tower_backend/base_plugin.py | 后端 | 删除 rollback() 方法及 docstring 引用 |
| tests/test_flow_engine.py | 后端 | 删除 3 个 rollback 测试用例；修复 mock 路径 |
| tests/test_node_timeout_strategy.py | 后端 | 修复 mock 导入路径 |
| apps.py | 后端 | 插件注册异常捕获改为 debug 日志 |
| docs/architecture/2026-06-28-remove-execution-rollback-refactor.md | 文档 | 新建架构重构文档 |
| docs/superpowers/specs/2026-06-28-remove-execution-rollback-design.md | 文档 | 新建设计规范文档 |

### 解决

- **问题/背景：** 执行回滚功能（节点失败后的补偿操作）不再需要，涉及 FlowEngine、PluginService、信号处理器和所有插件共计 18 个文件中的 rollback 代码
- **办法：** 删除所有执行回滚相关代码：核心引擎 rollback 调度、服务适配器 PluginService.rollback()、插件基类和所有子类的 rollback() 方法、信号处理器中的 rollback 触发、对应的测试用例。保留模板版本回滚和安全校验中的 rollback 路径检查

### 文档

- **生成文档：**
  - docs/opsflow/architecture/2026-06-28-remove-execution-rollback-refactor.md
  - docs/superpowers/specs/2026-06-28-remove-execution-rollback-design.md

### 验证

- 改动类型: refactor + fix (test mock paths)
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 待提交 ✅

---

## e345baa5

> 提交日期: 2026-06-28 | 提交信息: fix: loop config i18n + switch click event bubble fix — Loop Configuration 区域 i18n 替换 + 滑块点击无响应修复

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| PropertyPanel.vue | 前端 | 9 处硬编码标签/placeholder/radio 替换为 $t()；移除父 div @click 改为 span @click.stop 修复事件冒泡 |
| en.ts | 前端 | 新增 9 个 i18n keys (loopConfig/maxIterations/loopVariable/loopValues/...) |
| zh-cn.ts | 前端 | 新增对应 9 个中文翻译 |
| docs/opsflow/debug/2026-06-28-loop-config-i18n-switch-fix.md | 文档 | 新建调试文档 |

### 解决

- **问题/背景：** Loop Configuration 区域所有标签为硬编码英文，el-switch 滑块因事件冒泡双重触发导致点击无响应
- **办法：** 父 div 移除 @click，文字改为 span @click.stop 单独控制；全部标签替换为 $t()

### 文档

- **生成文档：**
  - docs/opsflow/debug/2026-06-28-loop-config-i18n-switch-fix.md

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端改动）
- 工作区状态: 待提交 ✅

---

## 8145f0fb

> 提交日期: 2026-06-28 | 提交信息: docs: fix commit hash references in analysis log and arch doc — 修正 COMMIT_ANALYSIS.md 和架构文档中的 commit hash 引用

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| COMMIT_ANALYSIS.md | 文档 | 修正上条记录中的 commit hash 为 4fbb2c87 |
| docs/opsflow/architecture/2026-06-28-remove-execution-rollback-refactor.md | 文档 | 修正文档中 commit hash 为 4fbb2c87 |

### 解决

- **问题/背景：** 上轮 amend 后 commit hash 变更，遗留的 COMMIT_ANALYSIS.md 和架构文档中仍引用旧 hash 4852cbce，导致链接失效
- **办法：** 将两处引用更新为实际的 commit hash 4fbb2c87

### 文档

- **生成文档：** 无（docs 类型跳过）

### 验证

- 改动类型: docs
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 待提交 ✅

---

## d7c0716c

> 提交日期: 2026-06-28 | 提交信息: fix: add aiSuggestions i18n key + widen AI dialog

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| web/src/i18n/pages/opsflow/zh-cn.ts | 前端 | 新增 opsflowPage.aiSuggestions 键 |
| web/src/i18n/pages/opsflow/en.ts | 前端 | 新增 opsflowPage.aiSuggestions 键 |
| web/src/views/apps/opsflow/index.vue | 前端 | AI 分析弹窗宽度 740px->960px |

### 解决

- **问题/背景：** aiSuggestions 在 index.vue 中被引用，但 i18n 文件中缺少该键；AI 分析弹窗内容太多放不下
- **办法：** 补齐中英文键；弹窗宽度扩大 1/3

### 验证

- 改动类型: fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 5ea3fd8e

> 提交日期: 2026-06-28 | 提交信息: fix: correct i18n key references in opsflow sub-pages

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/api/opsflow/dashboard.ts` | 前端 | API 路径修正 |
| `web/src/views/apps/{integration,itsm,open-api}/index.vue` | 前端 | i18n 键引用修正 (3 files) |
| `web/src/views/apps/opsflow-{approval,dashboard,execution,log,template}/index.vue` | 前端 | i18n 键引用修正 (5 files) |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue` | 前端 | 条件标签修正 |

### 解决

- **问题/背景：** 多个子页面 i18n 键引用使用错误的前缀格式
- **办法：** 统一修正为正确的 i18n 键路径

### 验证

- 改动类型: fix
- 清理乱码: 有（1 个 garbled file）
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 28122657

> 提交日期: 2026-06-28 | 提交信息: feat: unify IAM as identity management center + portal i18n

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/views/apps/iam/index.vue` | 前端 | 新增 5 个 dvadmin 系统管理 tab（Users/Roles/Menus/Depts/OperationLog） |
| `web/i18n/pages/iam/en.ts` | 前端 | 新增 users/roles/menus/depts/operationLog 标签 |
| `web/i18n/pages/iam/zh-cn.ts` | 前端 | 同上中文翻译 |
| `web/views/apps/portal/index.vue` | 前端 | 28+ 处硬编码替换为 message.portal.* i18n |
| `web/i18n/pages/portal/en.ts` | 前端 | 新建 30+ key 英文翻译 |
| `web/i18n/pages/portal/zh-cn.ts` | 前端 | 新建 30+ key 中文翻译 |

### 解决

- **问题/背景：** dvadmin 和 IAM 各管一方，IAM 缺少用户/角色/菜单管理入口；Portal 全部硬编码中文无法国际化
- **办法：** Phase 1 前端入口统一：IAM 直接嵌入 dvadmin 组件无需后端改动；Portal 全量 i18n 替换

### 文档

- **生成文档：** 无（纯前端改动）

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 5124f0b0

> 提交日期: 2026-06-28 | 提交信息: feat: add loop_iteration to NodeExecutionTrace for loop/cycle iteration tracking

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/models/execution.py` | 后端 | NodeExecutionTrace 新增 loop_iteration 字段，unique_together 改为 (execution, node_id, retry_count, loop_iteration) |
| `backend/opsflow/serializers.py` | 后端 | trace_summary 返回 loop_iteration |
| `backend/opsflow/signals/trace.py` | 后端 | 新增 _resolve_loop_iteration() — 检查上次迭代状态为 completed/failed 时自动递增 |
| `web/.../ExecutionDetail.vue` | 前端 | 行 key + Iteration 列 + tab 区域 overflow 滚动修复 |
| `docs/superpowers/specs/2026-06-28-loop-trace-iteration-design.md` | 文档 | 设计规范 |

### 解决

- **问题/背景：** loop 场景下节点执行多次，但 NodeExecutionTrace 只有一行(retry_count=0,loop_iteration=0)，后续迭代的 outputs 被覆盖
- **办法：** 新增 loop_iteration 字段 + _resolve_loop_iteration 按 DB 状态自动递增；Django migration 更新 unique_together

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-28-loop-trace-iteration-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## beabfcbb

> 提交日期: 2026-06-28 | 提交信息: fix: pipeline execution bugs + PropertyPanel condition editor overhaul

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | _find_predecessor_activity 处理 dict edge；_gwcond_ → {node_id}_{key} 修复 whitelist |
| `backend/opsflow/core/flow_engine.py` | 后端 | _has_loop_edges 传入原始 frozen_tree |
| `web/.../PropertyPanel.vue` | 前端 | Loop Config 修复（onLoopChange + v-if+v-for crash）；条件预览多行显示+Delete按钮+反解析Edit |
| `web/.../useDesignCanvas.ts` | 前端 | 边 label 保留；label 仅网关边显示；aiLayout 循环边恢复 label |
| `web/.../useGraphCanvas.ts` | 前端 | getGraphData 优先读 edgeData.label |
| `web/.../index.vue` | 前端 | onSelectTemplate 自动跑 AI layout |

### 解决

- **问题/背景：** Pipeline 执行因回环检测格式错误、自定义条件 whitelist 拒绝、前驱查找类型错误而失败；PropertyPanel Loop Config/条件编辑器因 Vue3 v-if+v-for 顺序、conditionStruct 状态管理不当而崩溃/无法编辑
- **办法：** 统一用 frozen_tree 格式检测回环；去掉 _gwcond_ 前缀；兼容 dict edge 前驱查找；loopVarOptions computed 替代 v-if+v-for；_parseConditionExpr 从字符串反解析；边 label 全线修复。共修复 5 个 bug

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-28-pipeline-bugfix-condition-editor.md`

### 验证

- 改动类型: fix+refactor
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 64fcc336

> 提交日期: 2026-06-28 | 提交信息: feat: implement multi-tenant architecture with Business/Environment isolation

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/iam/models/{tenant,project,membership,rbac}.py` | 后端 | iam app 重构为 models/ 包，新增 Business/BusinessGroup/DeployEnvironment/Project/ProjectMember/BusinessMember/DeployEnvironmentPermission 7 个模型 |
| `backend/iam/resolvers.py` | 后端 | 权限解析核心：get_visible_projects/has_project_role/can_execute_in_environment，Business 角色向下继承 |
| `backend/iam/permissions.py` | 后端 | TenantPermission/EnvironmentGatePermission DRF Backend |
| `backend/iam/routers.py` | 后端 | TenantDatabaseRouter 物理隔离扩展点（当前返回 default） |
| `backend/iam/views.py` | 后端 | BusinessViewSet/DeployEnvironmentViewSet/IamProjectViewSet 管理 API |
| `backend/iam/serializers.py` | 后端 | 全部 tenant 序列化器 |
| `backend/iam/urls.py` | 后端 | /api/iam/businesses/ /api/iam/environments/ /api/iam/projects/ 路由 |
| `backend/iam/management/commands/` | 后端 | seed_deploy_environments + grant_default_env_permissions 命令 |
| `backend/opsflow/models/` | 后端 | 6 模型 FK('iam.Project')，OperationRecord+ApiToken 增强，FlowExecution.environment FK，旧 OpsProject/ProjectMember 删除 |
| `backend/opsflow/views/base.py` | 后端 | ProjectFilteredViewSet 接入 iam.resolvers（get_visible_projects 含 Business 继承） |
| `backend/opsflow/views/{template,execution,project,schedule,knowledge,scheme}_views.py` | 后端 | 6 ViewSet 添加 TenantPermission，执行 ViewSet 添加 EnvironmentGatePermission |
| `backend/{cmdb,itsm,monitor,job_platform,integration,opsagent}/models/` | 后端 | 6 个子产品核心模型各添加 Business FK |
| `web/src/views/apps/iam/index.vue` | 前端 | 全新 hero + tabs 布局，Business 和 Environment 管理 tab |
| `web/src/views/apps/iam/{BusinessManage,EnvironmentManage}.vue` | 前端 | 业务线 CRUD + 成员管理，部署环境 CRUD + 权限管理 |
| `web/src/views/apps/iam/{MyRequests,ApprovalDashboard}/index.vue` | 前端 | 全部硬编码英文改为 i18n，统一 opsflow 卡片+表格+弹窗样式 |
| `web/src/i18n/pages/iam/{en,zh-cn}.ts` | 前端 | 90+ 中英文翻译 key |
| `docs/superpowers/specs/2026-06-28-multi-tenant-design.md` | 文档 | 17 条设计决策 + 完整实现方案 |

### 解决

- **问题/背景：** OPSflow 仅支持 OpsProject 级别隔离，无法满足企业按业务线和部署环境细粒度控制权限的需求，且 CMDB/ITSM/Monitor 等子产品缺少统一的权限底座
- **办法：** 新建 iam app 作为多租户基础设施；Project 从 opsflow 迁入 iam 避免循环依赖；权限解析分三层叠加；5 阶段渐进迁移不破坏现有功能；18/18 tests 全程通过

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-28-multi-tenant-design.md`
  - `docs/iam/features/2026-06-28-multi-tenant-implementation.md`

### 验证

- 改动类型: feat
- 清理乱码: 有（.bak 残留清理）
- 子 App index.md 更新: iam, opsflow, cmdb, itsm, monitor, job_platform, integration, opsagent
- 工作区状态: 干净 ✅
- 测试: opsflow.tests 18/18 OK ✅

---

## 4e0cbf74

> 提交日期: 2026-06-26 | 提交信息: feat: add template presets for AI quick-start

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/models/template.py` | 后端 | 新增 TemplatePreset 模型 |
| `backend/opsflow/views/template_views.py` | 后端 | GET /templates/presets/ 端点 |
| `backend/opsflow/management/commands/seed_template_presets.py` | 后端 | 10 个中英双语预设提示词 seed |
| `web/.../CreateTemplateWizard.vue` | 前端 | AI 输入框下方预设标签 |
| `web/.../api/templates.ts` | 前端 | GetTemplatePresets API |

### 解决

- **问题/背景：** 新用户不知道怎么写 AI 提示词，需要预制常见 IT 运维场景快速上手
- **办法：** TemplatePreset 模型存储中英双语提示词 + API 返回 + 前端预设标签 10 个场景覆盖串行/并行/网关/循环全部机制

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-template-presets-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 有
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## aecd282b

> 提交日期: 2026-06-26 | 提交信息: feat: implement pipeline loop mechanism A+B

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/bamboo_validator.py` | 后端 | 新增回环边检测，环检测跳过合法回环边 |
| `backend/opsflow/core/flow_engine.py` | 后端 | run() 传递 cycle_tolerate |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | 拓扑排序容忍回环边 + loop_config 注入 |
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | ServiceActivity loop_var SPLICE 绑定 |
| `backend/opsflow/core/layout/layout_adapter.py` | 后端 | canvas_width 自适应 + 每行最多 8 节点 |
| `backend/opsflow/core/llm_service.py` | 后端 | LLM 提示词追加 Loop Mechanisms |
| `web/.../PropertyPanel.vue` | 前端 | Loop Configuration UI |
| `web/.../useDesignCanvas.ts` | 前端 | AI Layout 去环-布局-恢复 + 回环边样式 |
| `web/.../useGraphCanvas.ts` | 前端 | layoutNodes 排除回环边 + orth 路由 |
| `web/.../useGraphValidator.ts` | 前端 | checkCycle 容忍排他网关回环边 |
| `backend/opsflow/tests/test_bamboo_builder.py` | 测试 | 8 个循环机制测试 |

### 解决

- **问题/背景：** OpsFlow 基于 DAG 引擎，不支持循环。IT 运维场景需要两种循环：批量执行（同操作不同参数）和条件轮询（等待状态满足）
- **办法：** 机制 A（节点级 loop_config）实现批量循环；机制 B（排他网关回环边）实现条件驱动轮询；前后端+校验+布局+AI 提示词全链路支持

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-loop-mechanism-design.md`

### 验证

- 改动类型: feat
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 26699e30

> 提交日期: 2026-06-26 | 提交信息: feat: template public conversion + VariableBrowser simplify + remove output promote

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/views/template_views.py` | 后端 | 新增 make_public action + project admin is_public 权限 |
| `web/.../opsflow-template/index.vue` | 前端 | Make Public 按钮 + 项目选择弹窗 |
| `web/.../api/templates.ts` | 前端 | MakeTemplatePublic API 函数 |
| `web/.../PropertyPanel.vue` | 前端 | 全局 Vars 按钮 + VariableBrowser + focus 焦点跟踪插入 |
| `web/.../VariableBrowser.vue` | 前端 | 移除 Add/Drawer/CRUD；新增只读信息卡 + Delete + DOM 光标插入 |
| `web/.../TagInput.vue, TagTextarea.vue` | 前端 | 移除内置 VariableBrowser（精简） |
| `web/.../OutputParamSection.vue` | 前端 | 移除 Output Promote 按钮 |

### 解决

- **问题/背景：** 模板无法转为公共模板供跨项目使用；VariableBrowser 功能混乱（手动 Add + Drawer 编辑与 Promote 入口冲突）；Output Promote 创建别名变量无实际价值
- **办法：** 新增 make_public API + 前端按钮弹窗；VariableBrowser 变为纯浏览/插入引用/删除工具；移除 Output Promote

### 文档

- **生成文档：**
  - `docs/superpowers/specs/2026-06-26-template-public-conversion-design.md`
  - `docs/superpowers/specs/2026-06-26-variable-browser-simplify-design.md`

### 验证

- 改动类型: feat+refactor
- 清理乱码: 无
- 子 App index.md 更新: 无（纯前端+少量后端改动）
- 工作区状态: 干净 ✅

---

## 3f8184af

> 提交日期: 2026-06-26 | 提交信息: feat: add 7 more SubmitWizard types + doc

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/.../SubmitWizardDialog.vue` | 前端 | 新增 switch/checkbox/radio/cascader/slider/host_selector/ip_selector 渲染 |
| `web/.../SubmitWizardDialog.vue` | 前端 | 修复多选下拉初始值类型（string->array） |
| `web/.../SubmitWizardDialog.vue` | 前端 | 修复 slider 初始值为数字类型 |
| `docs/.../2026-06-26-...md` | 文档 | 追加 FormItem 类型全景分析章节 + 更新记录 |

### 解决

- **问题/背景：** SubmitWizard Step 3 只覆盖了 9 种变量类型，缺少 switch/checkbox/radio/cascader/slider/host_selector/ip_selector 等 IT 运维常用类型；多选下拉和 slider 的初始值类型错误
- **办法：** Template 中为每种类型添加 v-else-if 分支渲染对应的 Element Plus 组件；loadVars() 中根据 meta.multiple 和 type 做类型转换

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md`（追加更新）

### 验证

- 改动类型: feat+docs+fix
- 清理乱码: 有（鎻愪氦 0字节）
- 子 App index.md 更新: 无（纯前端+文档改动）
- 工作区状态: 干净 ✅

---

## b67fff40

> 提交日期: 2026-06-26 | 提交信息: feat: node input promote + type-aware SubmitWizard — 原子节点输入参数提权全局变量 + SubmitWizard 类型感知渲染

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/variable_resolver.py` | 后端 | normalize_global_vars 添加 meta 字段 |
| `backend/opsflow/serializers.py` | 后端 | get_global_variable_list 返回 meta |
| `backend/opsflow/views/aliyun_views.py` | 后端 | _is_template_ref 拦截模板引用透传 + describe_disk_categories 修复 error code |
| `backend/opsflow/views/mixins/template_variable.py` | 后端 | hook_variable 增加 promote_type=input 支持 |
| `web/src/components/RenderForm/FormItem.vue` | 前端 | 输入框右侧添加 Promote 按钮 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 前端 | promoteInput 提权函数 + context.onPromote |
| `web/src/views/apps/opsflow/api/templates.ts` | 前端 | HookVariable 接口扩展 |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue` | 前端 | 类型感知渲染 + async_select 级联加载 + flex 2 列布局 |
| `web/src/views/apps/opsflow/components/panels/GlobalVariablePanel.vue` | 前端 | select 选项编辑器 + show_type 保留 + 代码重构 |
| `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md` | 文档 | 功能实现详细文档 |

### 解决

- **问题/背景：** 原子节点 input 参数无法一键提权为全局变量；SubmitWizard Step 3 所有变量统一渲染为 `<el-input>`，丢失 UI 类型信息；提权后的 async_select 变量没有级联下拉加载功能
- **办法：** FormItem 添加 Promote 按钮 → promoteInput 提权函数 → HookVariable(promote_type=input) 存储 type/meta；SubmitWizard 根据 templateVars.type 渲染对应组件（select/async_select/int/float/datetime/date/time）；async_select 实时 API 加载 + watch 级联依赖

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-26-node-input-promote-type-aware-submitwizard.md`

### 验证

- 改动类型: feat+fix+refactor
- 清理乱码: 无
- 子 App index.md 更新: opsflow
- 工作区状态: 干净 ✅

---

## b4ce0afd

> 提交日期: 2026-06-22 | 提交信息: feat: implement Aliyun ECS CMDB sync + refactor all 8 atoms

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/cloud_sync.py` | 后端 | 实时同步模块，Pipeline 执行后自动同步 ECS 到 CMDB |
| `backend/opsflow/core/plugin_service_adapter.py` | 后端 | execute 成功后调用 cloud_sync hook |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 30 分钟周期全量同步，修复闭包序列化 |
| `backend/cmdb/services/sync_service.py` | 后端 | AliyunSync 全地域分页查询 + 状态映射 |
| `backend/cmdb/services/import_service.py` | 后端 | 保留 instance_id 系统字段，修复 null MERGE |
| `backend/opsflow/plugins/aliyun_ecs/_client.py` | 后端 | resolve_cmdb_region() 工具函数 |
| `backend/opsflow/plugins/aliyun_ecs/*.py` | 后端 | 8 个原子统一改造：region async_select + instance_id CMDB 选择 + switch |
| `backend/opsflow/views/aliyun_views.py` | 后端 | 新增 describe_cmdb_instances API + 页面视图 |
| `backend/opsflow/urls.py` | 后端 | 注册 cmdb-instances 等 8 个路由 |
| `backend/common/management/commands/seed_reference.py` | 后端 | Host 模型加 cloud_instance_id 等 3 个字段 |
| `web/src/components/RenderForm/FormGroup.vue` | 前端 | formData 传递修复 |
| `web/src/components/RenderForm/FormItem.vue` | 前端 | TAG_MAP 注册 TagSwitch + formData |
| `web/src/components/RenderForm/RenderForm.vue` | 前端 | formData 传递修复 |
| `web/src/components/RenderForm/tags/TagSwitch.vue` | 前端 | 新增 switch 类型组件 |
| `web/src/components/RenderForm/tags/TagSlider.vue` | 前端 | 新增滑块组件（自定义标签） |
| `web/src/components/RenderForm/tags/index.ts` | 前端 | 导出 TagSwitch |
| `web/src/views/apps/integration/index.vue` | 前端 | 集成中心页面优化 |
| `docs/opsflow/features/` | 文档 | ECS CMDB 同步功能文档 |
| `docs/superpowers/specs/` | 文档 | ECS CMDB 同步设计文档 |

### 解决

- **问题/背景：** 阿里云 ECS 实例创建/删除/启停后不会更新 CMDB，Pipeline 执行完操作后实例在 CMDB 不可见；8 个原子 region 硬编码、instance_id 手动输入、无级联选择
- **办法：** 实时同步（cloud_sync.sync_after_execution）+ 周期同步（AliyunSync 全地域 30min）；所有原子改用 async_select 级联表单 + CMDB 实例选择 + switch 开关

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md`
  - `docs/superpowers/specs/2026-06-22-ecs-cmdb-sync-design.md`

### 验证

- 改动类型: feat+refactor+fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## 97397ecb

> 提交日期: 2026-06-23 | 提交信息: feat: implement Cloud Asset Sync management UI and sync logging — 云资产同步管理

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/models/cloud_sync_log.py` | 后端 | CloudSyncLog 同步日志持久化模型（provider/status/errors/triggered_by） |
| `backend/cmdb/views/cloud_sync_views.py` | 后端 | 云同步 API 4 端点 + 卡死记录自动检测（15min 超时重置） |
| `backend/cmdb/services/sync_service.py` | 后端 | BaseCloudSync 重构，sync() 自动写入 CloudSyncLog + try/except 兜底 |
| `backend/cmdb/urls.py` | 后端 | 注册 cloud-sync/providers/status/trigger/history 路由 |
| `backend/cmdb/models/__init__.py` | 后端 | 导出 CloudSyncLog |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 定时同步传入 triggered_by="schedule" |
| `web/src/views/apps/integration/cloud-sync.vue` | 前端 | 云同步管理组件（厂商卡片+操作工具栏+同步历史表格） |
| `web/src/views/apps/integration/index.vue` | 前端 | 集成中心新增云同步标签页 |
| `web/src/i18n/pages/integration/en.ts` | 前端 | 云同步英文文案（18 个 key） |
| `web/src/i18n/pages/integration/zh-cn.ts` | 前端 | 云同步中文文案（18 个 key） |
| `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md` | 文档 | 追加 CloudSyncLog/管理页面/数据修复 更新 |

### 解决

- **问题/背景：** 云同步只有后端无界面，用户无法查看同步状态、触发同步或排查同步错误；daemon thread 进程重启后同步状态永远卡在 running
- **办法：** 新增 CloudSyncLog 模型持久化同步记录；list_providers/sync_status/trigger_sync/sync_history 4 个 API；前端集成中心「云同步」标签页（厂商卡片 + 同步历史表格）；自动检测超 15 分钟卡死的 running 记录并重置

### 文档

- **生成文档：**
  - `docs/opsflow/features/2026-06-22-ecs-cmdb-sync.md`（追加更新）

### 验证

- 改动类型: feat+fix
- 清理乱码: 有（backend/reset 空文件）
- 子 App index.md 更新: cmdb
- 工作区状态: 干净 ✅

---

## df82a1c9

> 提交日期: 2026-06-17 | 提交信息: feat: implement CMDB hierarchy refactor — Service→Application→Process model

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/cmdb/management/commands/seed_dr_models.py` | 后端 | 新增 Application ModelDefinition + HAS_PROCESS/PROTECTED_BY 关联/模型关联种子数据 |
| `backend/agent_app/internal_views.py` | 后端 | `_sync_applications()` 同步 Application 节点 + HAS_PROCESS; `_match_calls_topology()` 建立 Application 级 CALLS |
| `backend/agent_app/apps.py` | 后端 | 实现 `get_registry_pids()` 修复死代码 |
| `backend/opsflow/services/dr_service.py` | 后端 | DR 拓扑查询改为 Application 级; neighbors_to_pipeline() 使用 Application 名 + host_ip |
| `backend/opsflow/views/mixins/template_dr.py` | 后端 | 修复 `_get_llm_client()` 解包错误 |
| `web/src/views/apps/cmdb/index.vue` | 前端 | DR 拓扑改为选中 Group 后才加载; 边过滤新增 PROTECTED_BY/HAS_PROCESS |
| `docs/cmdb/features/` | 文档 | Application 模型层次重构文档 |
| `docs/opsflow/features/` | 文档 | DR Pipeline 适配文档 |
| `backend/seed_monitor_dr.py` | 脚本 | 监控业务 DR mock 数据种子脚本 |
| `backend/clean_neo4j.py` | 脚本 | Neo4j 无效数据清理脚本 |
| `.gitignore` | 配置 | 忽略 backend/logs/ |

### 解决

- **问题/背景：** CMDB 模型扁平化在 Process(PID)级，DrGroup 直接关联 Process，CALLS 在 4 个 nginx worker 间毫无意义；缺少 Application 层承载启停语义和 DR 拓扑
- **办法：** 新增 `:Application` Neo4j 节点 + HAS_PROCESS/PROTECTED_BY 关系，将 CALLS 和 DR 关联提升到 Application 层；修复 LLM 客户端调用；前端 DR 拓扑改为 Group 选择后才加载

### 文档

- **生成文档：**
  - `docs/cmdb/features/2026-06-17-application-model-hierarchy.md`
  - `docs/opsflow/features/2026-06-17-dr-pipeline-adapter.md`

### 验证

- 改动类型: feat+refactor+fix
- 清理乱码: 无
- 子 App index.md 更新: 无
- 工作区状态: 干净 ✅

---

## ed7cb503

> 提交日期: 2026-06-15 | 提交信息: feat: implement opsflow-agent system — Go Agent + Server + Django integration

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/agent/` | 后端 | Go Agent Server + Agent daemon 核心实现（14个Go包） |
| `backend/agent_app/` | 后端 | Django App（6个模型，ViewSets，内部API） |
| `backend/opsflow/plugins/agent/` | 后端 | OpsFlow原子插件（3个：exec_cmd/file_push/file_pull） |
| `backend/job_platform/` | 后端 | AgentExecutor远程执行通道替代SSH |
| `backend/application/` | 后端 | 注册agent_app到Django |
| `backend/common/` | 后端 | Agent管理菜单seed数据 |
| `backend/agent-py/` | 后端 | Python Agent备份（重命名） |
| `web/src/views/apps/agent/` | 前端 | Agent管理页面（列表/安装/执行/文件推送） |
| `web/src/api/agent/` | 前端 | Agent API客户端 |
| `web/src/i18n/lang/` | 前端 | Agent页国际化（中/英各97个key） |
| `docs/superpowers/specs/` | 文档 | Agent设计文档 |

### 解决

- **问题/背景：** OpsFlow缺少远程Agent基础设施，远程执行依赖SSH（paramiko），无法做到指令推送、实时结果流、文件传输和主机端数据采集
- **办法：** 用Go实现类蓝鲸GSE的Agent组件体系（Server + Agent + Gateway三层架构），替换SSH成为远程执行首选通道

### 未实现 TODO

1. **应用进程管理**：应用进程的启动/停止/重启/状态查看不在本计划范围内
2. **文件传输完整链路**：Agent Server分块存储 → WS通知Agent → Agent并发HTTP拉取chunks → sha256校验 → 合并
3. **Agent Server后端批量写回**：command_result的batch_results内网端点已创建，但Agent Server的handleCommandResult尚未调用backend.Push()
4. **子进程管理器**：Agent subproc模块的框架已建，但exporter生命周期管理未实现
5. **Agent热升级端到端**：升级协议已定义，但Server端的upgrade API和Django AgentUpgrade模型尚未对接
6. **Gateway跨站点模式**：Gateway核心代码已实现，但未经过端到端测试验证
7. **CMDB采集数据写入Neo4j**：Agent collector已采集host_info，Django internal_views已接收reports，但尚未对接CMDB Service写入Neo4j
8. **Windows/AIX Agent安装包**：跨平台编译Makefile已建，但Windows Service注册和AIX SRC注册的install.sh尚未完善

### 验证

- 改动类型: feat
- 清理乱码: 有（build/目录下的二进制exe文件）
- 子App index.md 更新: agent_app（需要时更新）
- 工作区状态: 干净 ✅
