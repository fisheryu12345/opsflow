# 代码结构

## 后端目录结构

```
backend/opsflow/
├── __init__.py
├── apps.py                          # AppConfig → 启动时发现插件 + 注册组件 + 信号 + Seed 示例
├── serializers.py                   # DRF 序列化器（14+ 个）
├── urls.py                          # 12 个 ViewSet + 11 个 dashboard + CMDB + API GW 端点
├── tasks.py                         # Celery 共享任务（execute/notify/retry/timeout/webhook）
├── consumers.py                     # WebSocket 消费者（execution 状态推送）
│
├── models/                          # ★ 从单 models.py 拆分为包
│   ├── __init__.py                  #   重导出所有模型
│   ├── project.py                   #   OpsProject, ProjectMember
│   ├── template.py                  #   FlowTemplate, TemplateVersion, TemplateNode, TemplateCollect, TemplateCategory
│   ├── execution.py                 #   FlowExecution, ExecutionNode, ExecutionScheme, AutoRetryStrategy, NodeTimeoutConfig, NodeExecutionTrace
│   ├── plugin.py                    #   PluginMeta
│   ├── schedule.py                  #   SchedulePlan
│   ├── webhook.py                   #   WebhookConfig, WebhookLog
│   ├── audit.py                     #   OpsLog, OperationRecord
│   ├── knowledge.py                 #   OpsKnowledge
│   ├── auth.py                      #   ApiToken
│   └── env.py                       #   ProjectEnvironmentVariable
│
├── core/
│   ├── __init__.py
│   ├── flow_engine.py               # 流程执行引擎（BambooDjangoRuntime 封装）
│   ├── bamboo_builder.py            # Pipeline Tree 构建器（前端 nodes/edges → bamboo）
│   ├── bamboo_validator.py          # ★ Pipeline Tree 兼容性验证（从 builder 提取）
│   ├── node_dispatcher.py           # ★ 节点操作调度器（retry/skip/force_fail + trace）
│   ├── states.py                    # ★ 状态枚举 + 流转矩阵（NodeState/PipelineState）
│   ├── error_codes.py               # ★ 标准化错误码
│   ├── plugin_service_adapter.py    # ★ 统一插件服务（PluginService + Component 注册）
│   ├── safety_guard.py              # Pipeline 安全校验器
│   ├── scheduler_service.py         # ★ APScheduler 封装
│   ├── variable_resolver.py         # ★ 变量解析引擎（${key} 替换）
│   ├── variable_registry.py         # ★ 变量注册表（SpliceVariable/LazyVariable）
│   ├── subprocess_dispatcher.py     # ★ 独立子流程调度器
│   ├── trace_logger.py              # ★ 节点轨迹日志写入器（JSON Lines）
│   ├── tower_service.py             # Tower REST API 封装（launch/poll/extract）
│   ├── ansible_trigger.py           # Ansible Tower HTTP 触发器
│   ├── llm_service.py               # DeepSeek AI 服务（生成/修改/分析 + RAG）
│   ├── auto_retry.py                # ★ 节点自动重试策略 + Celery 派发
│   ├── node_timeout_strategy.py     # ★ 节点超时检测 + 动作处理
│   ├── node_sync.py                 # ★ pipeline_tree ↔ TemplateNode/ExecutionNode 同步
│   ├── mako_resolver.py             # ★ Mako 模板变量替换引擎
│   ├── conflict_checker.py          # ★ 多人编辑冲突检测
│   ├── audit_logger.py              # ★ 操作审计日志记录器
│   ├── plugin_deprecation.py        # ★ 插件生命周期管理
│   ├── pipeline_preview.py          # ★ Pipeline 预览（排除节点后清理）
│   ├── pipeline_schema.py           # ★ Pipeline Schema 校验
│   └── webhook_service.py           # ★ Webhook 回调投递服务
│   │
│   ├── apigw/                       # ★ 外部 API 网关
│   │   ├── __init__.py
│   │   ├── auth.py                  #   API Token 认证
│   │   └── views.py                 #   触发/状态/模板列表端点
│   │
│   ├── variables/                   # ★ bk_sops 适配变量类型
│   │   ├── __init__.py
│   │   └── common.py                #   InputVariable / SelectVariable 等 12 种
│   │
│   └── layout/                      # Sugiyama 分层布局引擎
│       ├── __init__.py              #   导出 compute_layout()
│       ├── constants.py             #   PipelineKey / NodeType / 尺寸常量
│       ├── utils.py                 #   format_to_list / io 操作
│       ├── acyclic.py               #   环移除 + DFS 环检测
│       ├── normalize.py             #   节点字典构建
│       ├── rank/                    #   层级分配（最长路径 + 可行树）
│       │   ├── __init__.py
│       │   ├── utils.py
│       │   ├── longest_path.py
│       │   ├── feasible_tree.py
│       │   └── tight_tree.py
│       ├── order/                   #   交叉最小化（加权中位数）
│       │   ├── __init__.py
│       │   ├── order.py
│       │   └── builder.py
│       ├── dummy.py                 #   长边虚拟节点替换
│       ├── position.py              #   坐标分配 + 箭头端点
│       ├── drawing.py               #   主编排器（5 阶段）
│       ├── layout_adapter.py        #   OPSflow ↔ 引擎格式桥接
│       └── tests.py                 #   单元测试
│
├── signals/                         # ★ 从单文件拆分为包
│   ├── __init__.py                  #   on_post_set_state 向后兼容导出
│   ├── handlers.py                  #   信号接收 + 根节点状态管理 + auto_retry 派发
│   ├── state.py                     #   node_status / state_tree 持久化
│   ├── trace.py                     #   NodeExecutionTrace + OpsLog 记录
│   ├── notify.py                    #   WebSocket 通知推送
│   ├── helpers.py                   #   重试次数推断 / 错误提取 / 审批检测
│   └── timeout.py                   # ★ 超时信号处理器
│
├── plugins/                         # 标准插件系统（51+ 个原子）
│   ├── __init__.py
│   ├── base.py                      # BasePlugin 基类
│   ├── registry.py                  # 插件发现 + 注册 + 同步
│   ├── common/                      # 2 个：send_alert, test_print_time
│   ├── ansible/                     # 9 个：shell, file_copy, backup_file, java_deploy, docker_deploy 等
│   ├── http/                        # 1 个：api_call
│   ├── monitor/                     # 3 个：disk_check, health_check, ping_test
│   ├── esxi/                        # 5 个：create_vm, destroy_vm, power_*, get_state
│   ├── redfish/                     # 8 个：power_*, firmware, storage, boot_device, system_info
│   ├── servicenow/                  # 5 个：incident, change_request, cmdb_ci
│   ├── netapp/                      # 5 个：volume, snapshot
│   ├── pmax/                        # 3 个：performance, snapshot, storage_group
│   └── verify/                      # ★ 1 个：ip_ops_verify
│
├── schema/
│   └── form_schema.py               # Pydantic 表单配置协议（FormItem/FormGroup/ValidationRule）
│
├── views/
│   ├── __init__.py
│   ├── base.py                      # ★ ProjectFilteredViewSet 基类（项目隔离）
│   ├── template_views.py            # 模板 CRUD（AI/版本/变量/子流程/收藏/Webhook → mixins）
│   ├── execution_views.py           # 执行 CRUD（生命周期/节点/审批/追踪 → mixins）
│   ├── log_views.py                 # 日志只读视图
│   ├── knowledge_views.py           # 知识库 CRUD + 搜索
│   ├── schedule_views.py            # 调度计划 CRUD + pause/resume/trigger/history
│   ├── plugin_views.py              # ★ 插件只读查询 + groups/variable_types
│   ├── project_views.py             # ★ 项目 CRUD + 成员管理 + 环境变量
│   ├── scheme_views.py              # ★ 执行方案 CRUD + 预览（嵌套路由）
│   ├── node_views.py                # ★ TemplateNode/ExecutionNode 只读查询
│   └── audit_views.py               # ★ 操作审计记录只读
│   │
│   ├── mixins/                      # ★ ViewSet Mixin 提取（11 个）
│   │   ├── __init__.py
│   │   ├── template_ai.py           #   TemplateAIMixin（生成/分析/布局）
│   │   ├── template_version.py      #   TemplateVersionMixin（发布/回滚/版本对比）
│   │   ├── template_variable.py     #   TemplateVariableMixin（变量 CRUD/浏览器/钩子）
│   │   ├── template_subprocess.py   #   TemplateSubprocessMixin（子流程版本追踪）
│   │   ├── template_export.py       #   TemplateExportImportMixin（导入/导出/分类）
│   │   ├── template_collect.py      # ★ TemplateCollectMixin（收藏/取消收藏）
│   │   ├── template_webhook.py      # ★ TemplateWebhookMixin（Webhook CRUD + 日志）
│   │   ├── execution_lifecycle.py   #   ExecutionLifecycleMixin（start/pause/resume/cancel）
│   │   ├── execution_node_command.py#   ExecutionNodeCommandMixin（retry/skip/fail/batch）
│   │   ├── execution_approval.py    #   ExecutionApprovalMixin（approve/reject）
│   │   └── execution_trace.py       #   ExecutionTraceMixin（traces/trace_log）
│   │
│   ├── dashboard_views/             # ★ 从单文件拆分为包
│   │   ├── __init__.py              #   向后兼容重导出 12 个函数
│   │   ├── stats.py                 #   dashboard_stats + schedule_stats
│   │   ├── trends.py                #   dashboard_trend + success_rate_trend
│   │   └── analytics.py             #   其余 8 个分析/分布端点
│   │
│   └── mock_view/                   # ★ CMDB Mock 数据视图
│       ├── esxi.py, servers.py, netapp.py, servicenow.py
│       ├── pmax.py, ip_pools.py, resources.py, categories.py
│
├── management/commands/
│   ├── add_opsflow_menu.py          # RBAC 菜单注册
│   ├── start_opsflow_scheduler.py   # APScheduler 独立进程启动
│   ├── clean_node_trace_logs.py     # ★ 日志文件清理
│   ├── clean_opsflow_data.py        # ★ 到期数据清理
│   └── seed_knowledge.py            # ★ 种子知识库（24 条条目）
│
├── migrations/                      # 22+ 个迁移文件（0001 ~ 0022）
├── tests/                           # 9 个测试文件（test_bamboo_builder / test_flow_engine / test_states / test_trace / test_layout 等）
├── TODO.md                          # 待办清单
└── doc/                             # 本文档目录 + bk_sops 分析 + 设计文档
```

## 前端目录结构

```
web/src/views/apps/opsflow/
├── index.vue                        # 主页面（布局 + AI Chat + Dialog + 工具栏）
├── OPSFLOW.md                       # 前端开发规范
├── stores/opsflowStore.ts           # Pinia 状态管理（设计/监控双模式）
├── utils/shapes.ts                  # ★ X6 自定义形状定义（9+ 种节点）
│
├── styles/
│   ├── opsflow-variables.scss       # SCSS 变量和主题
│   └── opsflow-global.scss          # 全局覆盖样式
│
├── components/
│   ├── DesignCanvas.vue             # 设计画布（X6 Graph + Stencil + PropertyPanel）
│   ├── MonitorCanvas.vue            # 监控画布（只读 + WebSocket 着色）
│   ├── PropertyPanel.vue            # 节点属性编辑面板（插件/版本/参数/变量映射）
│   ├── CreateTemplateWizard.vue     # ★ 创建模板向导（三步：输入→生成→保存）
│   ├── SubmitWizardDialog.vue       # ★ 执行提交向导（方案选择 + 变量覆盖 + Dry Run）
│   ├── DiffModal.vue                # AI 原稿对比弹窗
│   ├── DryRunDialog.vue             # ★ Dry Run 结果显示弹窗
│   ├── HelpDrawer.vue               # ★ 帮助抽屉（快捷键/节点类型/使用指南）
│   ├── PluginPickerDialog.vue       # ★ 插件选择器（按分组树）
│   ├── PluginVisibilityDialog.vue   # ★ 插件可见性配置弹窗
│   ├── GlobalVariablePanel.vue      # ★ 全局变量编辑面板
│   ├── VariableBrowser.vue          # ★ 变量浏览器（自动补全源）
│   ├── ProjectEnvVarPanel.vue       # ★ 项目环境变量编辑面板
│   ├── ProjectSwitcher.vue          # ★ 项目切换器
│   ├── SchemeManager.vue            # ★ 执行方案管理弹窗
│   ├── SchemeSelector.vue           # ★ 执行方案选择器
│   └── SubprocessStatusBadge.vue    # ★ 子流程版本过期徽标
│
└── composables/
    ├── useDesignCanvas.ts           # 画布逻辑（9 种 X6 自定义形状 + BFS 布局）
    ├── useMonitor.ts                # WebSocket 监控 + 节点着色
    ├── useGraphCanvas.ts            # ★ 通用 X6 Graph 创建/管理
    ├── useGraphValidator.ts         # ★ 画布校验逻辑
    └── useAutoSave.ts               # ★ 自动保存逻辑

web/src/views/apps/opsflow-log/
└── index.vue                        # 审计日志页面

web/src/views/apps/opsflow-knowledge/
└── index.vue                        # 知识库页面

web/src/views/apps/opsflow-template/
├── index.vue                        # 模板管理（表格/卡片切换 + 管道可视化）
├── schedule.vue                     # 调度计划列表页面
└── components/
    ├── ScheduleManager.vue          # 调度计划管理弹窗
    ├── ScheduleForm.vue             # 调度计划表单（一次性/CRON 切换）
    ├── ScheduleTable.vue            # 调度计划列表表格
    └── VersionDialog.vue            # ★ 版本管理弹窗

web/src/views/apps/opsflow-execution/
├── index.vue                        # 执行记录列表
└── components/
    ├── ExecutionList.vue            # 执行列表（表格 + 标签过滤）
    └── ExecutionDetail.vue          # 执行详情（MonitorCanvas + 日志/轨迹/数据面板）

web/src/views/apps/opsflow-dashboard/
└── index.vue                        # Dashboard（4 ECharts + 7 统计卡片 + 用户活动表）

web/src/views/apps/opsflow-approval/
└── index.vue                        # ★ 审批管理页面

web/src/views/apps/opsflow-webhook/
└── index.vue                        # ★ Webhook 管理页面

web/src/views/apps/opsflow-project/
└── index.vue                        # ★ 项目管理页面

web/src/views/apps/opsflow-stats/
└── index.vue                        # ★ 统计概览页面

web/src/api/opsflow/
├── templates.ts                     # 模板 API（30+ 个端点）
├── executions.ts                    # 执行 API（18+ 个端点）
├── logs.ts                          # 日志 API
├── knowledge.ts                     # 知识库 API
├── dashboard.ts                     # Dashboard 统计/趋势 API（11 个端点）
├── schedule-plans.ts                # 调度计划 API（9 个端点）
├── plugins.ts                       # ★ 插件 API（3 个端点）
├── projects.ts                      # ★ 项目 API（CRUD + 成员 + 环境变量）
├── audit.ts                         # ★ 操作审计 API
├── webhooks.ts                      # ★ Webhook 配置 API
├── servicenow.ts                    # ★ ServiceNow CMDB API
├── template-categories.ts           # ★ 模板分类 API
└── request.ts                       # ★ 通用请求工具
```

## 模型关系

```
┌──────────────────┐       ┌───────────────────┐
│   OpsProject     │       │  FlowExecution    │
│──────────────────│       │───────────────────│
│ id               │◄──────│ project (FK)      │
│ name             │       │ template (FK) ────┼──┐
│ description      │       │ status            │  │
│ owner            │       │ node_status       │  │
│ is_active        │       │ state_tree        │  │
│ max_schedule_plans│      │ context           │  │
│ created_at       │       │ template_snapshot │  │
└────────┬─────────┘       │ current_node      │  │
         │                 │ started_at        │  │
         │                 │ ended_at          │  │
         │                 │ created_by        │  │
         │  ┌──────────────┤ schedule_plan(FK)─┼──┐│
         │  │              │ parent_exec(FK)   │  ││
         │  │              │ is_subprocess     │  ││
         │  │              │ excluded_nodes    │  ││
         │  │              └────────┬──────────┘  ││
         │  │                       │             ││
         │  │              ┌────────▼──────────┐  ││
         │  │              │  ExecutionNode     │  ││
         │  │              │───────────────────│  ││
         │  │              │ execution (FK)    │  ││
         │  │              │ template_node(FK) │  ││
         │  │              │ node_id/status    │  ││
         │  │              └───────────────────┘  ││
         │  │                       │             ││
         │  │              ┌────────▼──────────┐  ││
         │  │              │ NodeExecutionTrace │  ││
         │  │              │───────────────────│  ││
         │  │              │ execution (FK)    │  ││
         │  │              │ node_id/status    │  ││
         │  │              │ inputs/outputs    │  ││
         │  │              │ duration_ms       │  ││
         │  │              │ log_file_path     │  ││
         │  │              └───────────────────┘  ││
         │  │                       │             ││
         │  │              ┌────────▼──────────┐  ││
         │  │              │     OpsLog        │  ││
         │  │              │───────────────────│  ││
         │  │              │ execution (FK)    │  ││
         │  │              │ step/command      │  ││
         │  │              │ risk_level        │  ││
         │  │              └───────────────────┘  ││
         │  │                                    ││
         │  │  ┌──────────────────┐              ││
         │  ├──│ ProjectMember    │              ││
         │  │  │──────────────────│              ││
         │  │  │ project (FK)     │              ││
         │  │  │ user (FK)        │              ││
         │  │  │ role (admin/     │              ││
         │  │  │  editor/viewer)  │              ││
         │  │  └──────────────────┘              ││
         │  │                                    ││
         │  │  ┌──────────────────┐              ││
         │  ├──│ ProjectEnvVar    │              ││
         │  │  │──────────────────│              ││
         │  │  │ project (FK)     │              ││
         │  │  │ key/value/type   │              ││
         │  │  └──────────────────┘              ││
         │  │                                    ││
         │  │  ┌──────────────────┐              ││
         │  ├──│   FlowTemplate   │◄─────────────┘│
         │  │  │──────────────────│               │
         │  │  │ id               │               │
         │  │  │ name             │               │
         │  │  │ pipeline_tree    │               │
         │  │  │ target_hosts     │               │
         │  │  │ global_vars      │               │
         │  │  │ is_draft         │               │
         │  │  │ ai_original_tree │               │
         │  │  │ category         │               │
         │  │  │ tags             │               │
         │  │  │ hook_variables   │               │
         │  │  │ version          │               │
         │  │  │ snapshot         │               │
         │  │  │ is_public        │               │
         │  │  │ project_scope    │               │
         │  │  │ project (FK) ────┼───────────────┘
         │  │  │ created_by       │
         │  │  └────────┬─────────┘
         │  │           │
         │  │  ┌────────▼─────────┐
         │  │  │  TemplateVersion │
         │  │  │──────────────────│
         │  │  │ template (FK)    │
         │  │  │ version          │
         │  │  │ pipeline_tree    │
         │  │  │ version_note     │
         │  │  └──────────────────┘
         │  │           │
         │  │  ┌────────▼─────────┐
         │  │  │  TemplateNode    │
         │  │  │──────────────────│
         │  │  │ template (FK)    │
         │  │  │ node_id/type     │
         │  │  │ atom_type/label  │
         │  │  │ node_config      │
         │  │  │ position_x/y     │
         │  │  │ max_retries      │
         │  │  │ timeout_seconds  │
         │  │  │ risk_level       │
         │  │  │ is_subprocess    │
         │  │  └──────────────────┘
         │  │           │
         │  │  ┌────────▼─────────┐
         │  │  │ ExecutionScheme  │
         │  │  │──────────────────│
         │  │  │ template (FK)    │
         │  │  │ project (FK)     │
         │  │  │ name/desc        │
         │  │  │ excluded_nodes   │
         │  │  │ variable_overrides│
         │  │  │ is_default       │
         │  │  └──────────────────┘
         │  │           │
         │  │  ┌────────▼─────────┐
         │  │  │  SchedulePlan    │
         │  │  │──────────────────│
         │  │  │ template (FK)    │
         │  │  │ project (FK)     │
         │  │  │ name             │
         │  │  │ schedule_type    │
         │  │  │ cron_expr        │
         │  │  │ status           │
         │  │  │ template_snapshot│
         │  │  │ total_run_count  │
         │  │  │ last_run_at      │
         │  │  │ next_run_at      │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│  WebhookConfig   │
         │  │  │──────────────────│
         │  │  │ template (FK)    │
         │  │  │ name/url/secret  │
         │  │  │ trigger_events   │
         │  │  │ retry_count/int  │
         │  │  │ enabled          │
         │  │  └────────┬─────────┘
         │  │           │
         │  │  ┌────────▼─────────┐
         │  │  │  WebhookLog      │
         │  │  │──────────────────│
         │  │  │ webhook (FK)     │
         │  │  │ execution (FK)   │
         │  │  │ event/status     │
         │  │  │ response_status  │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│  TemplateCollect │
         │  │  │──────────────────│
         │  │  │ user (FK)        │
         │  │  │ template (FK)    │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│ TemplateCategory │
         │  │  │──────────────────│
         │  │  │ name/code/icon   │
         │  │  │ sort_order       │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│  OpsKnowledge    │
         │  │  │──────────────────│
         │  │  │ title / content  │
         │  │  │ tags / source    │
         │  │  │ project (FK)     │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│   PluginMeta     │
         │  │  │──────────────────│
         │  │  │ code / name      │
         │  │  │ group / version  │
         │  │  │ form_schema      │
         │  │  │ output_schema    │
         │  │  │ phase            │
         │  │  │ allowed_projects │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  ├──│ OperationRecord  │
         │  │  │──────────────────│
         │  │  │ action/resource  │
         │  │  │ detail/operator  │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  │  │  ApiToken        │
         │  │  │──────────────────│
         │  │  │ name/token       │
         │  │  │ allowed_actions  │
         │  │  │ expires_at       │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  └──│ AutoRetryStrategy│
         │  │  │──────────────────│
         │  │  │ execution (FK)   │
         │  │  │ node_id          │
         │  │  │ max_retry_times  │
         │  │  │ interval         │
         │  │  │ retry_times      │
         │  │  └──────────────────┘
         │  │
         │  │  ┌──────────────────┐
         │  └──│ NodeTimeoutConfig│
         │     │──────────────────│
         │     │ execution (FK)   │
         │     │ node_id          │
         │     │ timeout_seconds  │
         │     │ action           │
         │     └──────────────────┘
```

## API 端点汇总

### 模板（FlowTemplateViewSet）

| 端点 | 方法 | Mixin 来源 | 说明 |
|------|------|-----------|------|
| `/api/opsflow/templates/` | GET/POST | — | 模板列表/创建 |
| `/api/opsflow/templates/{id}/` | GET/PUT/PATCH/DELETE | — | 模板详情/更新/删除 |
| `/api/opsflow/templates/create_from_ai/` | POST | template_ai | AI 自然语言生成 Pipeline |
| `/api/opsflow/templates/analyze/` | POST | template_ai | AI 流程分析 |
| `/api/opsflow/templates/refine/` | POST | template_ai | 多轮对话修改 |
| `/api/opsflow/templates/ai_layout/` | POST | template_ai | Sugiyama 布局优化 |
| `/api/opsflow/templates/{id}/diff/` | GET | template_ai | AI 原稿 vs 当前对比 |
| `/api/opsflow/templates/{id}/confirm_draft/` | POST | template_version | 草稿→V1 发布 |
| `/api/opsflow/templates/{id}/publish/` | POST | template_version | 发布新版本 |
| `/api/opsflow/templates/{id}/versions/` | GET | template_version | 版本历史列表 |
| `/api/opsflow/templates/{id}/rollback/` | POST | template_version | 回滚到指定版本 |
| `/api/opsflow/templates/{id}/version_diff/` | POST | template_version | DeepDiff 版本对比 |
| `/api/opsflow/templates/{id}/diff_draft/` | GET | template_version | 草稿 vs 发布版对比 |
| `/api/opsflow/templates/{id}/export/` | GET | template_export | 导出 JSON 包 |
| `/api/opsflow/templates/import_template/` | POST | template_export | 导入 JSON 模板 |
| `/api/opsflow/templates/{id}/hook_variables/` | GET/POST | template_variable | 可提升变量配置 |
| `/api/opsflow/templates/{id}/global-variables/` | GET/POST/PATCH | template_variable | 全局变量 CRUD |
| `/api/opsflow/templates/{id}/variable-browser/` | GET | template_variable | 变量浏览器 |
| `/api/opsflow/templates/{id}/hook-variable/` | POST | template_variable | 提升为全局变量 |
| `/api/opsflow/templates/{id}/unhook-variable/` | POST | template_variable | 解除变量关联 |
| `/api/opsflow/templates/{id}/subprocess-status/` | GET | template_subprocess | 子流程版本过期检查 |
| `/api/opsflow/templates/{id}/update-subprocess-refs/` | POST | template_subprocess | 批量更新子流程引用 |
| `/api/opsflow/templates/{id}/collect/` | POST | template_collect | ★ 收藏模板 |
| `/api/opsflow/templates/{id}/uncollect/` | POST | template_collect | ★ 取消收藏 |
| `/api/opsflow/templates/{id}/is_collected/` | GET | template_collect | ★ 检查是否已收藏 |
| `/api/opsflow/templates/{id}/webhooks/` | GET/POST | template_webhook | ★ Webhook 配置 CRUD |
| `/api/opsflow/templates/{id}/webhooks/{wh_id}/` | PATCH/DELETE | template_webhook | ★ Webhook 更新/删除 |
| `/api/opsflow/templates/{id}/webhooks/{wh_id}/logs/` | GET | template_webhook | ★ Webhook 投递日志 |
| `/api/opsflow/templates/update_plugin_phase/` | POST | template_views | ★ 更新插件生命周期阶段 |
| `/api/opsflow/templates/{id}/check_deprecated_plugins/` | GET | template_views | ★ 检查弃用插件 |

### 执行（FlowExecutionViewSet）

| 端点 | 方法 | Mixin 来源 | 说明 |
|------|------|-----------|------|
| `/api/opsflow/executions/` | GET/POST | — | 执行记录列表/创建 |
| `/api/opsflow/executions/{id}/` | GET/PUT/PATCH/DELETE | — | 执行详情/更新 |
| `/api/opsflow/executions/pending_approval/` | GET | execution_approval | 待审批列表 |
| `/api/opsflow/executions/{id}/start/` | POST | execution_lifecycle | 启动执行 |
| `/api/opsflow/executions/{id}/pause/` | POST | execution_lifecycle | 暂停 |
| `/api/opsflow/executions/{id}/resume/` | POST | execution_lifecycle | 恢复 |
| `/api/opsflow/executions/{id}/cancel/` | POST | execution_lifecycle | 取消 |
| `/api/opsflow/executions/{id}/retry_node/` | POST | execution_node_command | 重试节点 |
| `/api/opsflow/executions/{id}/skip_node/` | POST | execution_node_command | 跳过节点 |
| `/api/opsflow/executions/{id}/force_fail/` | POST | execution_node_command | 强制失败 |
| `/api/opsflow/executions/{id}/batch_retry/` | POST | execution_node_command | 批量重试 |
| `/api/opsflow/executions/{id}/batch_skip/` | POST | execution_node_command | 批量跳过 |
| `/api/opsflow/executions/{id}/retry_subprocess/` | POST | execution_node_command | 重试子流程 |
| `/api/opsflow/executions/{id}/approve/` | POST | execution_approval | 审批通过 |
| `/api/opsflow/executions/{id}/reject/` | POST | execution_approval | 审批拒绝 |
| `/api/opsflow/executions/{id}/traces/` | GET | execution_trace | 节点轨迹 |
| `/api/opsflow/executions/{id}/trace_log/` | GET | execution_trace | 轨迹日志 |
| `/api/opsflow/executions/dry_run/` | POST | execution_views | ★ Dry Run 安全执行 |

### 项目（OpsProjectViewSet）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/projects/` | GET/POST | ★ 项目列表/创建 |
| `/api/opsflow/projects/{id}/` | GET/PUT/PATCH/DELETE | ★ 项目详情/更新/删除 |
| `/api/opsflow/projects/my_projects/` | GET | ★ 当前用户项目列表 |
| `/api/opsflow/projects/{id}/members/` | GET/POST | ★ 成员列表/添加 |
| `/api/opsflow/projects/{id}/members/{member_id}/` | DELETE | ★ 移除成员 |
| `/api/opsflow/projects/{id}/env-vars/` | GET/POST/PATCH | ★ 环境变量 CRUD |

### 执行方案（ExecutionSchemeViewSet，嵌套路由）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/templates/{tid}/schemes/` | GET/POST | ★ 方案列表/创建 |
| `/api/opsflow/templates/{tid}/schemes/{id}/` | GET/PUT/PATCH/DELETE | ★ 方案详情/更新/删除 |
| `/api/opsflow/templates/{tid}/schemes/{id}/preview/` | GET | ★ 方案预览（排除节点后） |

### 节点（TemplateNodeViewSet / ExecutionNodeViewSet）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/template-nodes/` | GET | ★ 模板节点列表（只读） |
| `/api/opsflow/template-nodes/{id}/` | GET | ★ 模板节点详情 |
| `/api/opsflow/execution-nodes/` | GET | ★ 执行节点列表（只读） |
| `/api/opsflow/execution-nodes/{id}/` | GET | ★ 执行节点详情 |

### 日志 / 知识库 / 调度 / 插件 / 审计 / 分类

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/logs/` | GET | 审计日志列表（只读） |
| `/api/opsflow/knowledge/` | GET/POST | 知识库 CRUD |
| `/api/opsflow/knowledge/{id}/` | GET/PUT/PATCH/DELETE | 知识库详情/更新/删除 |
| `/api/opsflow/knowledge/search/` | POST | 知识库文本搜索 |
| `/api/opsflow/schedule-plans/` | GET/POST | 调度计划 CRUD |
| `/api/opsflow/schedule-plans/{id}/` | GET/PUT/PATCH/DELETE | 调度计划详情/更新/删除 |
| `/api/opsflow/schedule-plans/{id}/pause/` | POST | 暂停调度 |
| `/api/opsflow/schedule-plans/{id}/resume/` | POST | 恢复调度 |
| `/api/opsflow/schedule-plans/{id}/trigger/` | POST | 手动立即触发 |
| `/api/opsflow/schedule-plans/{id}/history/` | GET | 执行历史 |
| `/api/opsflow/plugins/` | GET | 插件列表（按 code 聚合，不含 form_schema） |
| `/api/opsflow/plugins/{code}/` | GET | 插件详情（含 form_schema，?version=过滤） |
| `/api/opsflow/plugins/groups/` | GET | 插件分组树 |
| `/api/opsflow/plugins/variable_types/` | GET | 注册的变量类型列表 |
| `/api/opsflow/audit/` | GET | ★ 操作审计记录列表 |
| `/api/opsflow/audit/{id}/` | GET | ★ 操作审计记录详情 |
| `/api/opsflow/template-categories/` | GET/POST | ★ 模板分类 CRUD |
| `/api/opsflow/template-categories/{id}/` | GET/PUT/PATCH/DELETE | ★ 模板分类详情/更新/删除 |

### Dashboard

| 端点 | 说明 |
|------|------|
| `/api/opsflow/dashboard/stats/` | 聚合统计（执行/模板/用户/性能/调度） |
| `/api/opsflow/dashboard/trend/` | 每日执行趋势（默认 30 天 + 平均耗时） |
| `/api/opsflow/dashboard/schedule-stats/` | 调度类型分布 + Top 调度 + 趋势 |
| `/api/opsflow/dashboard/top-templates/` | Top N 模板（执行次数/成功率/耗时） |
| `/api/opsflow/dashboard/user-activity/` | 用户活跃度排行 |
| `/api/opsflow/dashboard/status-distribution/` | 执行状态分布 |
| `/api/opsflow/dashboard/node-type-distribution/` | 节点类型分布 |
| `/api/opsflow/dashboard/duration-distribution/` | 执行耗时分布（7 个区间） |
| `/api/opsflow/dashboard/node-duration-top/` | 节点耗时排行榜 |
| `/api/opsflow/dashboard/success-rate-trend/` | 每日成功率趋势 |
| `/api/opsflow/dashboard/template-stats/` | 模板执行聚合统计 |

### API Gateway

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/apigw/v1/executions/` | POST | ★ 外部触发执行（API Token 认证） |
| `/api/opsflow/apigw/v1/executions/{id}/` | GET | ★ 查询执行状态 |
| `/api/opsflow/apigw/v1/templates/` | GET | ★ 外部查询模板列表 |

### CMDB Mock 数据

| 端点 | 说明 |
|------|------|
| `/api/opsflow/cmdb/esxi-hosts/` | ★ ESXi 主机 Mock 列表 |
| `/api/opsflow/cmdb/servers/` | ★ 服务器 Mock 列表 |
| `/api/opsflow/cmdb/netapp-clusters/` | ★ NetApp 集群 Mock 列表 |
| `/api/opsflow/cmdb/servicenow-instances/` | ★ ServiceNow 实例 Mock 列表 |
| `/api/opsflow/cmdb/servicenow-change-requests/` | ★ ServiceNow Change Request Mock |
| `/api/opsflow/cmdb/pmax-arrays/` | ★ Pmax 阵列 Mock 列表 |
| `/api/opsflow/cmdb/ip-pools/` | ★ IP 池 Mock 列表 |
| `/api/opsflow/cmdb/resources/` | ★ 资源 Mock 列表 |
| `/api/opsflow/cmdb/categories/` | ★ 分类 Mock 列表 |

### WebSocket

| 端点 | 说明 |
|------|------|
| `ws://host/ws/opsflow/execution/{id}/` | 实时状态推送（init_state/node_status/tower_job_update/execution_completed） |

## 核心模块依赖

```
apps.py
  ├─ discover_plugins()          → plugins/registry.py
  ├─ sync_plugin_meta_to_db()    → PluginMeta 表
  ├─ discover_variables()        → core/variables/common.py
  ├─ from opsflow import signals # noqa  → signals/ 包
  ├─ plugin_service_adapter      # noqa  → Component 自动注册
  └─ scheduler_service.start()   → APScheduler 启动

template_views.py (→ mixins/*.py)
  ├─ llm_service.py              (generate_pipeline / refine_pipeline / analyze)
  ├─ safety_guard.py             (validate_pipeline)
  ├─ layout                      (compute_layout — Sugiyama)
  ├─ bamboo_validator.py         (validate_bamboo_compatibility)
  ├─ variable_resolver.py        (normalize_global_vars / cleanup_unused_vars)
  └─ plugins/registry.py         (get_plugin)

execution_views.py (→ mixins/*.py)
  ├─ flow_engine.py              (FlowEngine)
  ├─ node_dispatcher.py          (NodeCommandDispatcher)
  ├─ states.py                   (PipelineState / transitions)
  └─ error_codes.py              (ErrorCodes / api_success / api_error)

flow_engine.py
  ├─ bamboo_builder.py           (build_bamboo_pipeline)
  ├─ safety_guard.py             (validate_pipeline)
  └─ tasks.py                    (execute_pipeline_task.delay)

signals/ (监听 post_set_state)
  ├─ handlers.py → state.py / trace.py / notify.py
  │   ├─ core/states.py          (PipelineState / map_bamboo_node_state)
  │   ├─ core/trace_logger.py    (NodeTraceLogger)
  │   ├─ core/flow_engine.py     (FlowEngine — 回滚)
  │   └─ tasks.py                (notify_node_status.delay / run_async)

plugin_service_adapter.py
  ├─ plugins/registry.py         (get_plugin)
  ├─ core/variable_resolver.py   (resolve_params — ${key} 替换)
  └─ pipeline.component_framework (Component 注册)

plugins/registry.py
  └─ plugins/base.py             (BasePlugin)
       └─ schema/form_schema.py  (FormItem / FormGroup)

bamboo_builder.py
  ├─ core/variable_resolver.py   (get_global_vars_values)
  └─ core/bamboo_validator.py    (_EXPR_PATTERN, _VAR_REF_PATTERN)
```
