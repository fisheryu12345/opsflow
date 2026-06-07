# OPSflow 代码结构

## 1. 后端目录树 (backend/opsflow/)

```
opsflow/
├── __init__.py
├── apps.py                              # Django AppConfig (ready: 自动发现插件)
├── consumers.py                          # WebSocket consumers (执行状态推送)
├── tasks.py                              # Celery 任务定义
├── urls.py                               # URL 路由注册
├── serializers.py                        # DRF Serializers
├── schema/                               # Pydantic Schema (form_schema)
│   └── form_schema.py                    # FormConfig: 表单配置定义
│
├── models/                               # 数据模型 (拆分模块)
│   ├── __init__.py                       # 统一重新导出
│   ├── template.py                       # FlowTemplate, TemplateVersion, TemplateNode, TemplateCollect, TemplateCategory
│   ├── execution.py                      # FlowExecution, ExecutionNode, ExecutionScheme, AutoRetryStrategy, NodeTimeoutConfig, NodeExecutionTrace
│   ├── project.py                        # OpsProject, ProjectMember
│   ├── plugin.py                         # PluginMeta
│   ├── schedule.py                       # SchedulePlan
│   ├── webhook.py                        # WebhookConfig, WebhookLog
│   ├── audit.py                          # OpsLog, OperationRecord
│   ├── knowledge.py                      # OpsKnowledge
│   ├── auth.py                           # ApiToken
│   └── env.py                            # ProjectEnvironmentVariable
│
├── core/                                 # 核心引擎模块
│   ├── __init__.py
│   ├── flow_engine.py                    # FlowEngine — 流程执行引擎
│   ├── states.py                         # NodeState / PipelineState 枚举 + 流转矩阵
│   ├── pipeline_builder/                 # Pipeline Tree 构建器
│   │   ├── __init__.py                   # build_bamboo_pipeline() 主入口
│   │   ├── conditions.py                 # 边条件解析
│   │   ├── elements.py                   # 节点元素创建 (ServiceActivity/Gateway/SubProcess)
│   │   └── validation.py                 # 循环引用检测
│   ├── plugin_service_adapter.py         # PluginService + OpsflowPluginComponent
│   ├── node_dispatcher.py                # NodeCommandDispatcher — 节点操作调度
│   ├── pipeline_schema.py                # Pipeline Tree JSON Schema 校验
│   ├── pipeline_preview.py               # Pipeline 预览 (简化 build)
│   ├── safety_guard.py                   # 安全校验 (白名单/重试上限/循环引用)
│   ├── bamboo_validator.py               # bamboo-engine 兼容性校验
│   ├── auto_retry.py                     # 自动重试策略创建 + 派发
│   ├── node_timeout_strategy.py          # Redis 分布式超时追踪 + 策略执行
│   ├── ansible_trigger.py                # Ansible Tower/AWX 触发执行器
│   ├── llm_service.py                    # AI 流程生成 (DeepSeek API + RAG)
│   ├── mako_resolver.py                  # Mako 模板引擎变量解析
│   ├── variable_resolver.py              # 变量 ${key} 替换 + 清理
│   ├── variable_registry.py              # 系统变量注册 (pipeline_start/pipeline_end 等)
│   ├── variables/                        # 变量类型实现
│   │   ├── __init__.py                   # lazy_resolver 延迟计算
│   │   ├── common.py                     # 公共变量 (target_host, loop 等)
│   │   └── cmdb_variables.py             # CMDB 变量
│   ├── node_sync.py                      # 节点持久化同步 (TemplateNode/ExecutionNode)
│   ├── trace_logger.py                   # 节点轨迹日志写入器 (JSON Lines)
│   ├── webhook_service.py                # Webhook 回调服务 (HMAC + 重试)
│   ├── subprocess_dispatcher.py          # 独立子流程调度器
│   ├── scheduler_service.py              # APScheduler 定时调度服务
│   ├── tower/                            # Ansible Tower/AWX 集成包
│   │   ├── __init__.py
│   │   ├── base.py                       # TowerService 基类
│   │   ├── client.py                     # Tower REST API 客户端
│   │   ├── job.py                        # 作业管理 (launch/poll/cancel)
│   │   └── polling.py                    # 自适应轮询策略
│   ├── tower_service.py                  # Ansible Tower/AWX 集成 (旧版单文件)
│   ├── conflict_checker.py               # 并发冲突检测
│   ├── audit_logger.py                   # 审计日志
│   ├── error_codes.py                    # 错误码定义 + api_success/api_error
│   ├── plugin_deprecation.py             # 插件弃用检查
│   ├── apigw/ (已迁移)                   # 功能已迁移到 backend/open_api/
│   └── layout/                           # Sugiyama 分层布局引擎
│       ├── __init__.py
│       ├── constants.py                  # NodeType, POSITION, CANVAS_WIDTH
│       ├── layout_adapter.py             # opsflow ↔ pipeline 格式适配 + compute_layout 入口
│       ├── normalize.py                  # 输入标准化
│       ├── acyclic.py                    # 环边反转
│       ├── drawing.py                    # 主绘图流程
│       ├── position.py                   # 坐标分配
│       ├── dummy.py                      # 虚拟节点
│       ├── utils.py                      # 工具函数 (层次属性计算)
│       ├── tests.py                      # 布局测试
│       ├── order/                        # 交叉最小化
│       │   ├── __init__.py
│       │   ├── builder.py                # 层构建
│       │   └── order.py                  # WDA 排序算法
│       └── rank/                         # 层级分配
│           ├── __init__.py
│           ├── longest_path.py           # 最长路径层级
│           ├── feasible_tree.py          # 紧树构造
│           ├── tight_tree.py             # 紧树搜索
│           └── utils.py                  # 层级工具
│
├── plugins/                              # 标准插件集合
│   ├── base.py                           # BasePlugin 基类
│   ├── registry.py                       # 插件注册中心 (PLUGIN_REGISTRY)
│   ├── ansible/                          # Ansible 执行插件 (9原子)
│   │   ├── shell.py, script_exec.py, file_copy.py
│   │   ├── upload_file.py, backup_file.py
│   │   ├── java_deploy.py, docker_deploy.py
│   │   ├── nginx_reload.py, service_control.py
│   ├── cmdb/                             # CMDB 插件
│   │   ├── query.py                      # CMDB 查询
│   │   └── resource_selector.py          # 资源选择器
│   ├── common/                           # 通用插件
│   │   ├── send_alert.py, test_print_time.py
│   ├── esxi/                             # VMware ESXi 插件 (5原子)
│   │   ├── create_vm.py, destroy_vm.py, get_state.py
│   │   ├── power_on.py, power_off.py
│   ├── http/                             # HTTP API 调用插件
│   │   └── api_call.py
│   ├── itsm/                             # ITSM 插件
│   │   ├── create_ticket.py              # 创建工单
│   │   └── update_ticket.py              # 更新工单
│   ├── monitor/                          # 监控插件 (3原子)
│   │   ├── disk_check.py, health_check.py, ping_test.py
│   ├── netapp/                           # NetApp 存储插件 (5原子)
│   │   ├── netapp_create_snapshot.py, netapp_create_volume.py
│   │   ├── netapp_delete_volume.py, netapp_get_volume.py
│   │   ├── netapp_modify_volume.py
│   ├── pmax/                             # Dell PowerMax 插件 (3原子)
│   │   ├── performance.py, snapshot.py, storage_group.py
│   ├── redfish/                          # Redfish BMC 插件 (7原子)
│   │   ├── redfish_firmware_inventory.py, redfish_get_system_info.py
│   │   ├── redfish_list_storage.py, redfish_power_cycle.py
│   │   ├── redfish_power_off.py, redfish_power_on.py
│   │   └── redfish_set_boot_device.py
│   ├── servicenow/                       # ServiceNow ITSM 插件 (5原子)
│   │   ├── servicenow_create_change_request.py
│   │   ├── servicenow_create_incident.py
│   │   ├── servicenow_get_cmdb_ci.py
│   │   ├── servicenow_get_incident.py
│   │   └── servicenow_update_incident.py
│   └── verify/                           # 验证测试插件
│       └── ip_ops_verify.py              # 运维验证
│
├── signals/                              # 信号处理模块
│   ├── __init__.py
│   ├── handlers.py                       # on_post_set_state 主接收器
│   ├── state.py                          # 节点状态持久化 (JSON_SET 原子更新)
│   ├── trace.py                          # 轨迹记录 + 日志写入
│   ├── notify.py                         # WebSocket 推送
│   ├── timeout.py                        # Redis 超时追踪更新
│   └── helpers.py                        # 信号辅助函数
│
├── views/                                # API 视图
│   ├── base.py                           # ProjectFilteredViewSet, ProjectReadOnlyViewSet
│   ├── template_views.py                 # FlowTemplateViewSet (CRUD)
│   ├── execution_views.py                # FlowExecutionViewSet (CRUD + dry_run)
│   ├── plugin_views.py                   # PluginViewSet
│   ├── project_views.py                  # OpsProjectViewSet
│   ├── schedule_views.py                 # SchedulePlanViewSet
│   ├── scheme_views.py                   # ExecutionSchemeViewSet
│   ├── node_views.py                     # 节点状态/轨迹查询
│   ├── audit_views.py                    # 审计日志查询
│   ├── log_views.py                      # 操作日志查询
│   ├── knowledge_views.py                # 知识库视图
│   ├── template_category_views.py        # 模板分类视图
│   ├── mixins/                           # ViewSet Mixin 拆分
│   │   ├── template_ai.py               # AI 生成/分析/布局/比较
│   │   ├── template_version.py           # 版本管理 (发布/回滚/diff)
│   │   ├── template_variable.py          # 变量管理
│   │   ├── template_subprocess.py        # 子流程追踪
│   │   ├── template_export.py            # 导入导出
│   │   ├── template_collect.py           # 收藏
│   │   ├── template_webhook.py           # Webhook 配置
│   │   ├── execution_lifecycle.py        # 生命周期 (start/pause/resume/cancel)
│   │   ├── execution_node_command.py     # 节点操作 (retry/skip/force_fail/batch)
│   │   ├── execution_approval.py         # 审批 (approve/reject)
│   │   └── execution_trace.py            # 轨迹查询
│   └── dashboard_views/                  # 仪表盘统计
│       ├── stats.py                      # 基础统计 (总数/成功率/运行中)
│       ├── trends.py                     # 趋势统计
│       └── analytics.py                  # 深度分析 (Top模板/用户活跃/分布)
│
├── management/commands/                  # Django 管理命令
│   ├── start_opsflow_scheduler.py        # 启动 APScheduler
│   ├── seed_sample_template.py           # 种子模板数据
│   ├── seed_template_categories.py       # 种子分类数据
│   ├── seed_knowledge.py                 # 种子知识库数据
│   ├── index_knowledge.py               # 知识库索引
│   ├── clean_node_trace_logs.py          # 清理轨迹日志
│   ├── clean_opsflow_data.py            # 清理数据
│   ├── fix_node_status_double_encode.py # 修复双编码
│   └── opsflow_migrate_projects.py      # 项目迁移
│
├── migrations/                           # 数据库迁移
│
└── tests/                                # 单元测试
    ├── test_flow_engine.py
    ├── test_bamboo_builder.py
    ├── test_layout.py
    ├── test_states.py
    └── ...

```

## 2. 前端目录树

前端页面按功能独立目录存放于 `web/src/views/apps/` 下，共享代码在 `opsflow/` 主目录：

### 核心共享目录 (web/src/views/apps/opsflow/)

```
opsflow/                                    # 核心共享代码
├── index.vue                              # 主入口 (路由: /opsflow)
├── stores/
│   └── opsflowStore.ts                    # Pinia 状态管理
├── types/
│   └── index.ts                           # TypeScript 类型定义
├── utils/
│   ├── shapes.ts                          # X6 自定义图形 (Node/Edge 样式)
│   └── nodes.ts                           # X6 节点定义辅助
├── composables/
│   ├── useDesignCanvas.ts                 # 设计器画布交互
│   ├── useMonitor.ts                      # 监控画布交互
│   ├── useGraphCanvas.ts                  # 通用 X6 画布操作
│   ├── useGraphValidator.ts               # 画布图结构校验
│   └── useAutoSave.ts                     # 模板自动保存 (debounce)
├── components/
│   ├── canvas/
│   │   ├── DesignCanvas.vue               # 流程设计器 (X6)
│   │   └── MonitorCanvas.vue              # 执行监控画布 (X6)
│   ├── panels/
│   │   ├── PropertyPanel.vue              # 节点属性面板 (右侧)
│   │   ├── GlobalVariablePanel.vue        # 全局变量编辑
│   │   └── MonitorPanel.vue               # 监控面板
│   ├── dialogs/
│   │   ├── CreateTemplateWizard.vue       # 创建模板向导
│   │   ├── SubmitWizardDialog.vue         # 提交执行向导
│   │   ├── PluginPickerDialog.vue         # 插件选择弹窗
│   │   ├── PluginVisibilityDialog.vue     # 插件可见性配置
│   │   ├── DiffModal.vue                  # 版本 Diff 弹窗
│   │   ├── DryRunDialog.vue               # Dry Run 弹窗
│   │   └── ConditionDialog.vue            # 条件编辑弹窗
│   ├── gates/
│   │   └── ConditionRow.vue               # 条件行 (AND/OR)
│   ├── pickers/
│   │   ├── VariableBrowser.vue            # 变量浏览器
│   │   └── VariablePicker.vue             # 变量选择器
│   ├── badges/
│   │   └── SubprocessStatusBadge.vue      # 子流程状态徽标
│   ├── schemes/
│   │   ├── SchemeManager.vue              # 执行方案管理
│   │   └── SchemeSelector.vue             # 执行方案选择
│   └── common/
│       ├── ProjectSwitcher.vue            # 项目切换器
│       ├── ProjectEnvVarPanel.vue         # 项目环境变量
│       └── HelpDrawer.vue                 # 帮助抽屉
└── api/                                   # API 请求封装
    ├── request.ts                         # axios 实例 (拦截器)
    ├── templates.ts                       # 模板相关 API
    ├── executions.ts                      # 执行相关 API
    ├── plugins.ts                         # 插件相关 API
    ├── projects.ts                        # 项目相关 API
    ├── dashboard.ts                       # 仪表盘 API
    ├── schedule-plans.ts                  # 定时计划 API
    ├── webhooks.ts                        # Webhook API
    ├── audit.ts                           # 审计 API
    ├── logs.ts                            # 日志 API
    ├── knowledge.ts                       # 知识库 API
    ├── servicenow.ts                      # ServiceNow API
    └── template-categories.ts             # 分类 API
```

### 子页面目录 (web/src/views/apps/ 同级)

```
├── opsflow-approval/
│   └── index.vue                          # 审批页面
├── opsflow-dashboard/
│   └── index.vue                          # 仪表盘页面
├── opsflow-execution/
│   ├── index.vue                          # 执行列表页
│   └── components/
│       ├── ExecutionList.vue              # 执行列表
│       └── ExecutionDetail.vue            # 执行详情
├── opsflow-knowledge/
│   └── index.vue                          # 知识库管理
├── opsflow-log/
│   └── index.vue                          # 操作日志
├── opsflow-project/
│   └── index.vue                          # 项目管理
├── opsflow-stats/
│   └── index.vue                          # 统计报表
├── opsflow-template/
│   └── index.vue                          # 模板管理列表
└── opsflow-webhook/
    └── index.vue                          # Webhook 配置
```

## 3. 模型关系图

```
┌──────────────────────┐     ┌──────────────────────────┐
│    OpsProject        │     │    FlowTemplate           │
│──────────────────────│     │──────────────────────────│
│ id (PK)              │     │ id (PK)                   │
│ name                 │◄────┤ project (FK → OpsProject) │
│ description          │  m  │ name                      │
└──────────┬───────────┘  1  │ pipeline_tree (JSON)     │
           │                 │ target_hosts (JSON)       │
           │                 │ global_vars (JSON)        │
┌──────────▼───────────┐     │ snapshot (JSON)           │
│   ProjectMember      │     │ version (int)             │
│──────────────────────│     │ is_draft                  │
│ id (PK)              │     │ is_public                 │
│ project (FK)         │     │ project_scope (JSON)      │
│ user (FK → User)     │     │ ai_original_tree (JSON)   │
│ role                 │     │ category                  │
└──────────────────────┘     │ created_by (FK → User)    │
                             └────────────┬──────────────┘
                                 1        │        1
                                 │        │        │
                  ┌──────────────┘  ┌─────┴─────┐  └──────────────┐
                  ▼                 ▼           ▼                 ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  TemplateVersion     │  │  TemplateNode     │  │  TemplateCollect     │
│──────────────────────│  │──────────────────│  │──────────────────────│
│ template (FK)        │  │ template (FK)     │  │ user (FK → User)     │
│ version              │  │ node_id           │  │ template (FK)        │
│ pipeline_tree (JSON) │  │ node_type         │  │ unique: (user, tmpl) │
│ target_hosts (JSON)  │  │ atom_type         │  └──────────────────────┘
│ global_vars (JSON)   │  │ label             │
│ version_note         │  │ position_x/y      │   ┌──────────────────────┐
│ unique: (tmpl, ver)  │  │ max_retries       │   │  TemplateCategory    │
└──────────────────────┘  │ timeout_seconds   │   │──────────────────────│
                          │ risk_level        │   │ name, code, icon     │
                          │ unique: (tmpl,nid)│   │ sort_order           │
                          └──────────────────┘   └──────────────────────┘

┌─────────────────────────┐       ┌─────────────────────────┐
│  FlowExecution          │       │  SchedulePlan           │
│─────────────────────────│       │─────────────────────────│
│ id (PK)                 │       │ template (FK)            │
│ template (FK)           │       │ project (FK)             │
│ project (FK → Project)  │       │ name                     │
│ status                  │◄──────┤ crontab / interval       │
│ node_status (JSON)      │m    1 │ enabled                  │
│ state_tree (JSON)       │       │ excluded_nodes (JSON)    │
│ context (JSON)          │       │ variable_overrides (JSON)│
│ template_snapshot (JSON)│       └─────────────────────────┘
│ current_node            │
│ excluded_nodes (JSON)   │               1
│ parent_execution (FK)   │               │
│ is_subprocess           │               │ m
│ schedule_plan (FK)      │       ┌─────────────────────────┐
│ created_by (FK → User)  │       │  AutoRetryStrategy      │
│ started_at / ended_at   │       │─────────────────────────│
└────────────┬────────────┘       │ execution (FK)           │
     1 │     │     │              │ node_id                  │
      │     │     │              │ max_retry_times          │
      │ m   │ m   │ m            │ interval                  │
  ┌───┘     │     └───┐         │ retry_times              │
  ▼         ▼         ▼         │ unique: (exec, nid)      │
┌────────┐ ┌────────┐ ┌───────┐ └─────────────────────────┘
│ Exec-  │ │ Exec-  │ │ Node-  │
│ ution  │ │ ution  │ │ Exec-  │ ┌─────────────────────────┐
│ Node   │ │ Scheme │ │ ution  │ │  NodeTimeoutConfig      │
│────────│ │────────│ │ Trace  │ │─────────────────────────│
│ exec   │ │ tmpl   │ │────────│ │ execution (FK)           │
│ nid    │ │ name   │ │ exec   │ │ node_id                  │
│ ntype  │ │ excl   │ │ nid    │ │ timeout_seconds          │
│ status │ │ nodes  │ │ status │ │ action                   │
│ max_   │ │ var_   │ │ dur_ms │ │ unique: (exec, nid)      │
│ retries│ │ over   │ │ logs   │ └─────────────────────────┘
│ uniq:  │ │        │ │ uniq:  │
│ (exec, │ │        │ │ (exec, │ ┌─────────────────────────┐
│  nid)  │ │        │ │ nid,rc)│ │  WebhookConfig          │
└────────┘ └────────┘ └────────┘ │─────────────────────────│
                                 │ template (FK)            │
┌────────────────────┐          │ url, secret, name        │
│  PluginMeta        │          │ trigger_events (JSON)    │
│────────────────────│          │ retry_count, retry_intvl │
│ code + version     │          │ enabled                   │
│   (unique_together)│          └─────────────────────────┘
│ name, group        │
│ description        │          ┌─────────────────────────┐
│ risk_level, icon   │          │  WebhookLog             │
│ form_schema (JSON) │          │─────────────────────────│
│ output_schema(JSON)│          │ webhook (FK)             │
│ phase (生命周期)   │          │ execution (FK)           │
│ allowed_projects   │          │ event, status            │
│ is_active          │          │ request/response fields  │
└────────────────────┘          │ retry_count              │
                                └─────────────────────────┘
┌────────────────────┐
│ OpsKnowledge       │   ┌──────────────────────┐
│────────────────────│   │ OpsLog / Operation   │
│ title              │   │       Record         │
│ content            │   │──────────────────────│
│ category           │   │ template/execution   │
│ created_by         │   │ action, detail, user │
│ tags (JSON)        │   │ timestamp            │
└────────────────────┘   └──────────────────────┘

┌──────────────────────────┐
│  ProjectEnvironmentVar   │
│──────────────────────────│
│ project (FK)              │
│ key (unique per project) │
│ value (encrypted)        │
│ description              │
└──────────────────────────┘
```

## 4. API 端点表

| ViewSet/Prefix | Method | URL | 功能 |
|----------------|--------|-----|------|
| **FlowTemplateViewSet** | GET | `/api/opsflow/templates/` | 模板列表 (分页) |
| | POST | `/api/opsflow/templates/` | 创建模板 |
| | GET | `/api/opsflow/templates/{id}/` | 模板详情 |
| | PUT | `/api/opsflow/templates/{id}/` | 更新模板 |
| | DELETE | `/api/opsflow/templates/{id}/` | 删除模板 |
| | POST | `/api/opsflow/templates/create_from_ai/` | AI 生成模板 |
| | POST | `/api/opsflow/templates/analyze/` | AI 分析流程 |
| | POST | `/api/opsflow/templates/refine/` | AI 修改流程 |
| | POST | `/api/opsflow/templates/ai_layout/` | 自动布局 |
| | POST | `/{id}/confirm_draft/` | 确认草稿 (V1) |
| | POST | `/{id}/publish/` | 发布新版本 |
| | GET | `/{id}/versions/` | 版本列表 |
| | POST | `/{id}/rollback/` | 回滚版本 |
| | POST | `/{id}/version_diff/` | 版本对比 |
| | GET | `/{id}/diff_draft/` | 草稿 vs 已发布 diff |
| | GET | `/{id}/diff/` | AI 原稿 vs 当前 diff |
| | GET | `/{id}/subprocess_chain/` | 子流程链路追踪 |
| | POST | `/{id}/collect/` | 收藏/取消收藏 |
| | GET | `/{id}/webhooks/` | 模板 Webhook 配置 |
| | POST | `/{id}/webhooks/` | 更新 Webhook 配置 |
| | GET | `/{id}/check_deprecated_plugins/` | 弃用插件检查 |
| | POST | `/api/opsflow/templates/update_plugin_phase/` | 更新插件生命周期 |
| **FlowExecutionViewSet** | GET | `/api/opsflow/executions/` | 执行列表 (用户过滤) |
| | POST | `/api/opsflow/executions/` | 创建执行 |
| | GET | `/api/opsflow/executions/{id}/` | 执行详情 |
| | POST | `/{id}/start/` | 启动执行 |
| | POST | `/{id}/pause/` | 暂停执行 |
| | POST | `/{id}/resume/` | 恢复执行 |
| | POST | `/{id}/cancel/` | 取消执行 |
| | POST | `/{id}/retry_node/` | 重试节点 |
| | POST | `/{id}/skip_node/` | 跳过节点 |
| | POST | `/{id}/force_fail/` | 强制失败 |
| | POST | `/{id}/batch_retry/` | 批量重试 |
| | POST | `/{id}/batch_skip/` | 批量跳过 |
| | POST | `/{id}/retry_subprocess/` | 重试子流程 |
| | GET | `/{id}/trace/{node_id}/` | 节点轨迹 |
| | GET | `/{id}/trace_log/{node_id}/` | 节点日志 |
| | GET | `/{id}/state_tree/` | 状态树 |
| | GET | `/{id}/traces/` | 全部轨迹摘要 |
| | GET | `/api/opsflow/executions/pending_approval/` | 待审批列表 |
| | POST | `/{id}/approve/` | 审批通过 |
| | POST | `/{id}/reject/` | 审批拒绝 |
| | POST | `/api/opsflow/executions/dry_run/` | Dry Run 执行 |
| **PluginViewSet** | GET | `/api/opsflow/plugins/` | 插件列表 (按组分) |
| | POST | `/api/opsflow/plugins/sync/` | 同步插件元数据 |
| | POST | `/api/opsflow/plugins/update_phases/` | 批量更新生命周期 |
| **SchedulePlanViewSet** | CRUD | `/api/opsflow/schedule-plans/` | 定时计划管理 |
| **OpsProjectViewSet** | CRUD | `/api/opsflow/projects/` | 项目管理 |
| **ExecutionSchemeViewSet** | CRUD | `/api/opsflow/schemes/` | 执行方案管理 |
| **Dashboard** | GET | `/api/opsflow/dashboard/stats/` | 基础统计 |
| | GET | `/api/opsflow/dashboard/trend/` | 执行趋势 |
| | GET | `/api/opsflow/dashboard/success_rate_trend/` | 成功率趋势 |
| | GET | `/api/opsflow/dashboard/top_templates/` | Top 模板 |
| | GET | `/api/opsflow/dashboard/user_activity/` | 用户活跃 |
| | GET | `/api/opsflow/dashboard/status_distribution/` | 状态分布 |
| | GET | `/api/opsflow/dashboard/node_type_distribution/` | 节点类型分布 |
| | GET | `/api/opsflow/dashboard/duration_distribution/` | 耗时分布 |
| | GET | `/api/opsflow/dashboard/node_duration_top/` | 节点耗时 Top |
| | GET | `/api/opsflow/dashboard/schedule_stats/` | 定时计划统计 |
| | GET | `/api/opsflow/dashboard/template_stats/` | 模板统计 |
| **Audit** | GET | `/api/opsflow/audit/logs/` | 审计日志 |
| **Log** | GET | `/api/opsflow/logs/` | 操作日志 |
| **Knowledge** | CRUD | `/api/opsflow/knowledge/` | 知识库 |
| **TemplateCategory** | CRUD | `/api/opsflow/template-categories/` | 模板分类 |
| **WebSocket** | WS | `/ws/opsflow/execution/{id}/` | 执行状态推送 |

> **注：** 外部 API 网关已从 `opsflow/core/apigw/` 迁移到独立 `backend/open_api/` 应用。外部端点路径为 `/api/v2/open/pipelines/trigger/`（触发 Pipeline）、`/api/v2/open/pipelines/{id}/`（查询状态）、`/api/v2/open/pipelines/templates/`（列出模板）。详见 [docs/opsflow_target.md](../opsflow_target.md)。

## 5. 核心模块依赖图

```
                       FlowEngine
                      ┌──────────┐
                      │  run()   │
                      │  start() │
                      │  pause() │─────────► BambooDjangoRuntime
                      │  resume()│─────────► bamboo_engine.api
                      │  retry() │
                      │  cancel()│
                      └─────┬────┘
                            │
          ┌─────────────────┼────────────────────┐
          ▼                 ▼                     ▼
  PipelineBuilder      SafetyGuard          AutoRetryCreator
  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
  │ filter_nodes │   │ WHITELIST   │   │ batch_create_    │
  │ adjacency    │   │  _ATOMS()   │   │ strategy()       │
  │ create_elems │   │ max_retries │   │ dispatch_auto_   │
  │ topological  │   │ circular    │   │ retry()          │
  │ connect      │   │ ref detect  │   └──────────────────┘
  │ pair_conv    │   └──────────────┘
  │ build_data   │           │               NodeTimeoutConfig
  └──────┬───────┘           │           ┌──────────────────────┐
         │                   │           │ batch_create_timeout │
         ▼                   ▼           │ update_node_timeout  │
  Pipeline Tree JSON    bamboo_validator │ dispatch_timeout_    │
  {nodes, edges}                        │ nodes()              │
                                         └──────────────────────┘
         │
         ▼                                    Signals
  PluginService                            ┌──────────────┐
  ┌──────────────────┐                     │ handlers.py  │
  │ execute()        │                     │  → state.py  │
  │   → get_plugin() │◄──── PLUGIN_        │  → trace.py  │
  │   → resolve_     │      REGISTRY        │  → notify.py │
  │     params()     │                     │  → timeout.py│
  │   → instance.    │                     └──────┬───────┘
  │     execute()    │                            │
  └──────────────────┘                            ▼
                                            NodeCommandDispatcher
                                            ┌──────────────────┐
                                            │ retry/skip/      │
                                            │ force_fail       │
                                            │ get_trace        │
                                            └──────────────────┘
```
