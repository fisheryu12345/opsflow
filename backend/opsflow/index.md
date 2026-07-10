# OPSFLOW — Module Index

> Last auto-update: 2026-07-10 | Trigger commit: f689e639

---

## `Root`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `apps.py` | — | `OpsflowConfig` |
| `serializers.py` | — | `GlobalVariableField` — 全局变量字段 — 接受扁平或结构化格式，始终返回结构化格式<br>`FlowTemplateSerializer`<br>`TemplateVersionSerializer`<br>`FlowExecutionSerializer`<br>`TemplateNodeSerializer` |
| `tasks.py` | — | `run_async()` — 在 Celery worker 中安全执行异步协程。<br>`execute_pipeline_task()` — Celery 任务 — 异步执行 Pipeline<br>`auto_retry_node_task()` — Celery 任务 — 自动重试失败节点（由 auto_retry dispatch 触发）<br>`execute_node_timeout_strategy()` — Celery 任务 — 执行节点超时策略<br>`webhook_send()` — Celery 任务 — 发送 Webhook 回调 |
| `urls.py` | — | — |

## `core/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `audit_logger.py` | 审计日志工具 — 记录用户操作到 OperationRecord 表 | `log_operation()` — 记录操作审计 |
| `auto_retry.py` | 自动重试策略 — 节点 FAILED 时自动触发重试 | `AutoRetryStrategyCreator` — 批量创建自动重试策略 — 在 FlowEngine.run() 开始时调用<br>`dispatch_auto_retry()` — 检查并派发自动重试 — 在信号拦截到 FAILED 时调用 |
| `bamboo_validator.py` | Bamboo Pipeline Tree 兼容性验证器 | `validate_bamboo_compatibility()` — 校验 pipeline_tree 是否能被 bamboo-engine 执行 |
| `cloud_sync.py` | 阿里云 ECS → CMDB 实时同步 | `sync_after_execution()` — Pipeline 原子执行成功后触发 CMDB 同步<br>`sync_ecs_instance()` — 将单个 ECS 实例同步到 CMDB :Host 节点 |
| `conflict_checker.py` | 冲突检测规则引擎 — 检测节点配置中的语义冲突 | `check_config_conflicts()` — 检查 pipeline_tree 中的配置冲突 |
| `error_codes.py` | 标准化错误码 — 全系统统一错误分类和封装 | `ErrorCodes` — 错误码常量<br>`api_success()` — 标准成功响应<br>`api_error()` — 标准错误响应 |
| `flow_engine.py` | Flow Execution Engine — BambooDjangoRuntime + bamboo_engine.api | `FlowEngine` — 流程执行引擎 — BambooDjangoRuntime 驱动（仅异步路径） |
| `llm_service.py` | LLM 服务 — 通过集成中心调用 AI 完成流程生成/分析 | `generate_pipeline()` — Convert natural language to Pipeline Tree JSON<br>`refine_pipeline()` — Multi-turn: modify existing Pipeline Tree based on new instr<br>`rag_search()` — Simple text RAG search — recall relevant cases from OpsKnowl<br>`analyze_pipeline()` — Analyze Pipeline Tree: describe purpose, steps, and potentia |
| `mako_resolver.py` | Mako 模板变量解析 — 安全沙箱封装 | `MakoResolver` — 安全的类 Mako 表达式解析器<br>`resolve_with_mako()` — 通用入口 — 检测 #{...} 走 Mako 路径，否则原样返回 |
| `node_dispatcher.py` | NodeCommandDispatcher — 节点操作调度器 | `NodeCommandDispatcher` — 节点操作调度器 |
| `node_sync.py` | 节点同步工具 — 在 pipeline_tree JSON 与 TemplateNode/ExecutionNode 模型间同步 | `extract_nodes_from_tree()` — 从 pipeline_tree JSON 提取节点列表（标准格式，非可视化节点）<br>`sync_template_nodes()` — 将模板的 pipeline_tree 同步为 TemplateNode 行（全量删除重建）<br>`sync_execution_nodes()` — 从模板快照创建 ExecutionNode 记录 |
| `node_timeout_strategy.py` | 节点超时策略 — 超时后自动执行 forced_fail / forced_fail_and_skip | `NodeTimeoutStrategy` — 节点超时策略基类<br>`ForcedFailStrategy` — 强制失败策略 — 调用 api.forced_fail_activity<br>`ForcedFailAndSkipStrategy` — 强制失败并跳过策略<br>`batch_create_timeout_configs()` — 遍历 pipeline_tree，为 timeout_seconds > 0 的节点创建超时配置<br>`get_redis()` — 获取 Redis 连接 |
| `pipeline_preview.py` | Pipeline 预览与清理 — 执行方案预览树生成 | `PipelinePreviewService` — 执行方案预览服务 — 根据排除节点生成清理后的 pipeline 树 |
| `pipeline_schema.py` | Pipeline Tree JSON Schema 验证 | `validate_pipeline_schema()` — JSON Schema 结构验证<br>`validate_global_var_keys()` — 校验全局变量键名格式<br>`validate_pipeline_full()` — 全量验证：JSON Schema → 键名 → 返回 unified 结果 |
| `plugin_deprecation.py` | 插件退役管理 — 检测已弃用插件在模板中的引用 | `check_deprecated_plugins_in_template()` — 递归扫描模板 pipeline_tree，检测已弃用的插件引用 |
| `plugin_service_adapter.py` | bamboo-engine 适配层 — 通用 PluginService | `PluginService` — 通用 Service — 所有原子通过这一个类路由到 BasePlugin.execute()<br>`OpsflowPluginComponent` |
| `safety_guard.py` | Pipeline Tree 安全校验器 — 原子白名单从 PLUGIN_REGISTRY 动态加载 | `WHITELIST_ATOMS()` — 返回所有已注册插件的 code 集合<br>`HIGH_RISK_ATOMS()` — 返回 risk_level == 'high' 的插件 code 集合<br>`BACKUP_REQUIRED_ATOMS()` — 已废弃 — BasePlugin 不再追踪 dependencies，始终返回空集<br>`validate_pipeline()` — 校验 Pipeline Tree JSON。 |
| `scheduler_service.py` | — | `OpsflowScheduler` — APScheduler wrapper for managing SchedulePlan timed triggers |
| `states.py` | 状态枚举与流转矩阵 — 节点生命周期 + Pipeline 级别状态 | `NodeState` — 节点状态枚举 — 每个节点的生命周期状态<br>`PipelineState` — Pipeline 级状态枚举 — FlowExecution.status<br>`validate_node_transition()` — 检查节点状态转移是否合法，返回 True/False<br>`validate_pipeline_transition()` — 检查 Pipeline 级状态转移是否合法<br>`map_bamboo_node_state()` — bamboo-engine 状态 → NodeState |
| `subprocess_dispatcher.py` | Independent Subprocess Dispatcher — runs subprocess as separate FlowExecution | `SubprocessDispatcher` — Dispatches a subprocess node as an independent FlowExecution |
| `trace_logger.py` | 节点轨迹日志写入器 — 每个节点独立的 JSON Lines 日志文件 | `NodeTraceLogger` — 节点轨迹日志写入器 |
| `variable_registry.py` | 变量注册表系统 — 适配自 bk_sops LazyVariable + VariableLibrary 模式 | `RegisterVariableMeta` — 元类 — 在子类创建时自动注册到 VariableLibrary<br>`SpliceVariable` — 支持 ${key} 模板替换的变量基类<br>`LazyVariable` — 延迟计算变量 — 在模板替换后执行 get_value()<br>`VariableLibrary` — 变量库 — 按 code 检索变量类 |
| `variable_resolver.py` | 变量解析引擎 — ${key} 模板变量替换 + 跨节点数据引用 | `normalize_global_vars()` — 规范化 global_vars 为包含元数据的结构化格式<br>`get_global_vars_values()` — 从规范化（或扁平）global_vars 中提取纯值 dict<br>`count_variable_references()` — 扫描 pipeline_tree 中 `${var_key}` 的出现次数<br>`cleanup_unused_vars()` — 删除 pipeline_tree 中不再被任何节点引用的全局变量<br>`get_variable_reference_details()` — 返回变量引用明细 — 每个引用出现的节点 ID 和字段路径 |
| `webhook_service.py` | Webhook 回调服务 — 执行完成/失败时发送 HTTP 回调 | `WebhookService` — Webhook 回调服务 |

## `core/layout/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Sugiyama layered graph layout engine for OPSflow. | — |
| `acyclic.py` | Acyclic graph transformation — remove self-loops and reverse backward edges. | `remove_self_edges()` — Remove self-looping edges and store them for restoration.<br>`insert_self_edges()` — Restore previously removed self-loop edges.<br>`acyclic_run()` — Reverse backward edges until graph is acyclic. Returns rever<br>`acyclic_undo()` — Restore previously reversed edges to their original directio |
| `constants.py` | Layout engine constants — replaces pipeline_web.constants.PWE. | `NodeType`<br>`PipelineKey` |
| `drawing.py` | Main orchestrator — wires all 5 phases of the Sugiyama layout algorithm. | `draw_pipeline()` — Execute the full Sugiyama layout pipeline on a pipeline tree |
| `dummy.py` | Long-edge splitting with dummy nodes + gateway fill-number computation. | `replace_long_path_with_dummy()` — Replace edges spanning >1 rank with chains of DummyNode -> D<br>`compute_nodes_fill_num()` — Calculate extra vertical slots needed at each position for g<br>`remove_dummy()` — Remove dummy nodes/flows and restore long edges. |
| `layout_adapter.py` | OPSflow {nodes, edges} <-> pipeline tree format bridge. | `opsflow_to_pipeline()` — Convert OPSflow {nodes, edges} to a pipeline tree dict.<br>`pipeline_to_positions()` — Extract [{id, x, y}] from pipeline after draw_pipeline().<br>`compute_layout()` — Full layout computation: OPSflow format in -> positions out. |
| `normalize.py` | Pipeline data normalization — build/remove all_nodes dictionary. | `get_all_nodes()` — Build flat all_nodes dict from pipeline sections.<br>`normalize_run()`<br>`normalize_undo()` |
| `position.py` | Coordinate assignment with arrow endpoint calculation. | `position()` — Assign x,y coordinates to all nodes and compute arrow endpoi |
| `tests.py` | Unit tests for the Sugiyama layout engine. | `test_empty_graph()`<br>`test_single_node()`<br>`test_two_nodes()`<br>`test_serial_three()` — 3 serial nodes — x strictly increasing, y centered.<br>`test_branching()` — 1 start -> exclusive_gateway -> 2 tasks -> converge -> end |
| `utils.py` | Utility functions for flow ID management on nodes. | `format_to_list()` — Normalize incoming/outgoing to list.<br>`add_flow_id_to_node_io()` — Add flow_id to node's incoming or outgoing list.<br>`delete_flow_id_from_node_io()` — Remove flow_id from node's incoming or outgoing list. |

## `core/layout/order/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `builder.py` | Stub for future layer graph builder. | `build_layer_graph()` — Placeholder. |
| `order.py` | Crossing minimization via weighted-median heuristic (Sugiyama). | `ordering()` — Assign node order within each rank to minimize edge crossing<br>`init_order()` — Initialize per-rank node ordering via topological traversal <br>`wmedian()` — Apply weighted-median heuristic in alternating direction.<br>`refer_node_ids()` — Get connected node IDs in adjacent layer (incoming → source,<br>`median_value()` — Compute median position of reference nodes in adjacent layer |

## `core/layout/rank/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `feasible_tree.py` | Feasible-tree rank refinement — minimize total edge length. | `feasible_tree_ranker()` — Refine ranks by building a spanning tree of tight edges, |
| `longest_path.py` | Longest-path rank assignment — initial rank for each node. | `longest_path_ranker()` — Assign each node a rank equal to length of longest path from |
| `tight_tree.py` | Tight-tree rank orchestrator — longest-path then feasible-tree refinement. | `tight_tree_ranker()` — Assign ranks using longest-path, then refine with feasible t |
| `utils.py` | Rank utility functions. | `max_rank()`<br>`min_rank()`<br>`normalize_ranks()` — Shift all ranks so that min rank is 0.<br>`slack()` — Return slack (tightness) of a flow: rank(target) - rank(sour |

## `core/pipeline_builder/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Pipeline Tree 构建器 — 将 FlowTemplate 的自定义 pipeline_tree 转换为 bamboo-engine 可执行格式 | `build_bamboo_pipeline()` — 将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict |
| `elements.py` | pipeline 构建 - 节点元素创建 | — |
| `validation.py` | pipeline 构建 - 循环引用检测 | — |

## `core/variable_types/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | 变量类型包 — 导入此模块触发所有变量类注册到 VARIABLE_REGISTRY | — |
| `common.py` | 通用变量类型 — 适配自 bk_sops pipeline_plugins.variables.collections.common | `InputVariable` — 文本输入变量<br>`TextareaVariable` — 多行文本变量<br>`IntVariable` — 整数变量<br>`FloatVariable` — 浮点数变量<br>`DatetimeVariable` — 日期时间变量 |

## `management/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |

## `management/commands/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `clean_opsflow_data.py` | 清理过期 OpsFlow 数据 — DB 记录 + 日志文件 | `Command` |
| `index_knowledge.py` | Index all knowledge entries for vector search.
批量索引所有知识条目以供向量搜索。 | `Command` |
| `seed_opsflow.py` | Seed OpsFlow reference & mock data | `Command` |
| `seed_template_presets.py` | Seed Template Presets — 10 个常见 IT 运维场景预设提示词 (中英双语) | `Command` |
| `start_opsflow_scheduler.py` | — | `Command` |

## `models/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `audit.py` | — | `OperationRecord` — 操作审计记录 — 记录所有重要用户操作<br>`OpsLog` — 审计日志 — 每一步的详细执行记录 |
| `auth.py` | — | `ApiToken` — 外部 API Token — 用于第三方系统认证，绑定 Business + Deployment Environmen |
| `env.py` | — | `ProjectEnvironmentVariable` — 项目级环境变量 — 跨模板共享的配置值 |
| `execution.py` | — | `FlowExecution` — 执行实例 — 一次流程运行记录<br>`ExecutionNode` — 执行节点 — 执行实例中的节点记录，从 TemplateNode 同步<br>`ExecutionScheme` — 执行方案 — 预定义的节点排除集 + 变量覆盖<br>`AutoRetryStrategy` — 节点自动重试策略 — 在信号拦截到 FAILED 时自动触发重试<br>`NodeTimeoutConfig` — 节点超时配置 — 绑定到执行实例的节点超时策略 |
| `knowledge.py` | — | `OpsKnowledge` — RAG 知识库 — 历史案例/故障/文档 |
| `plugin.py` | — | `PluginMeta` — 标准插件元数据 — 注册时自动同步（支持多版本） |
| `schedule.py` | — | `SchedulePlan` — 调度计划 — 一次性或周期性自动执行 |
| `template.py` | — | `FlowTemplate` — 编排模板 — AI 生成的或人工创建的流程定义<br>`TemplateVersion` — 模板版本历史 — 每次发布时创建<br>`TemplateNode` — 模板节点 — 从 pipeline_tree JSON 同步为独立行，支持 SQL 查询<br>`TemplateCollect` — 用户收藏的模板<br>`TemplateCategory` — 模板分类 — 可管理配置，管理员可增删 |
| `webhook.py` | — | `WebhookConfig` — Webhook 回调配置 — 绑定到模板，执行完成后触发<br>`WebhookLog` — Webhook 投递日志 |

## `plugins/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `base.py` | BasePlugin 基类 — 所有标准插件继承此类 | `BasePlugin` — 标准插件基类 — 每个运维原子（技能）继承此类 |
| `loader.py` | Plugin 热加载器 — 文件快照 + 增量注册 | `PluginLoader` — 插件热加载器 |
| `registry.py` | 插件注册中心 — 自动扫描 plugins/ 下所有 BasePlugin 子类 | `discover_plugins()` — 扫描 opsflow/plugins/ 下所有模块，自动注册 BasePlugin 子类<br>`get_plugin()` — 获取插件类，version=None 时返回最新版本<br>`get_plugin_versions()` — 返回指定 code 的所有版本列表<br>`get_all_plugins()`<br>`get_plugins_by_group()` — 返回分组的所有插件（每个 code 的最新版本） |

## `plugins/agent/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Agent 远程执行插件 — 通过 Agent 在被管控主机上执行命令和脚本 | — |
| `agent_process_restart.py` | agent_process_restart — 通过 Agent 远程重启应用进程 | `AgentProcessRestartPlugin` |
| `agent_process_start.py` | agent_process_start — 通过 Agent 远程启动应用进程 | `AgentProcessStartPlugin` |
| `agent_process_status.py` | agent_process_status — 通过 Agent 查询应用进程状态 | `AgentProcessStatusPlugin` |
| `agent_process_stop.py` | agent_process_stop — 通过 Agent 远程停止应用进程 | `AgentProcessStopPlugin` |
| `exec_cmd.py` | agent_exec_cmd — 通过 Agent 远程执行命令/脚本 | `AgentExecCmdPlugin` |
| `file_pull.py` | agent_file_pull — 通过 Agent Agent 从目标主机拉取文件 | `AgentFilePullPlugin` |
| `file_push.py` | agent_file_push — 通过 Agent Agent 推送文件到目标主机 | `AgentFilePushPlugin` |

## `plugins/ai/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `ai_text_gen.py` | AI Text Generation Plugin — 调用 LLM 生成文本 / AI Text Generation Atom | `AiTextGenPlugin` |

## `plugins/aliyun_ecs/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `_client.py` | 阿里云 ECS SDK 客户端工厂 — 复用集成中心凭证 | `get_ecs_client()` — 获取阿里云 ECS SDK AcsClient<br>`resolve_cmdb_region()` — 从 CMDB 查询阿里云实例的地域 |
| `create_image.py` | 创建自定义镜像 | `AliyunEcsCreateImagePlugin` |
| `create_instance.py` | 创建 ECS 实例（含可选公网 IP 分配） | `AliyunEcsCreatePlugin` |
| `delete_instance.py` | 释放 ECS 实例 | `AliyunEcsDeletePlugin` |
| `describe_instance.py` | 查询 ECS 实例详情 | `AliyunEcsDescribePlugin` |
| `modify_instance.py` | 修改 ECS 实例属性（名称、描述） | `AliyunEcsModifyPlugin` |
| `restart_instance.py` | 重启 ECS 实例 | `AliyunEcsRebootPlugin` |
| `start_instance.py` | 启动 ECS 实例 | `AliyunEcsStartPlugin` |
| `stop_instance.py` | 停止 ECS 实例 | `AliyunEcsStopPlugin` |

## `plugins/ansible/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `backup_file.py` | 文件备份 — 备份远程主机上的文件或目录（通过 Ansible Tower） | `BackupFilePlugin` |
| `docker_deploy.py` | Docker 部署 — 部署 Docker 容器（通过 Ansible Tower） | `DockerDeployPlugin` |
| `file_copy.py` | 文件复制 — 复制文件或目录到远程主机（通过 Ansible Tower） | `FileCopyPlugin` |
| `java_deploy.py` | Java 部署 — 部署 Java 应用（通过 Ansible Tower） | `JavaDeployPlugin` |
| `nginx_reload.py` | Nginx 重载 — 验证 Nginx 配置并执行重载（通过 Ansible Tower） | `NginxReloadPlugin` |
| `script_exec.py` | 脚本执行 — 上传脚本内容并在远程主机上执行（通过 Ansible Tower） | `ScriptExecPlugin` |
| `service_control.py` | 服务控制 — 控制系统服务的启动/停止/重启/重载状态（通过 Ansible Tower） | `ServiceControlPlugin` |
| `shell.py` | Shell 执行 — 在目标主机上执行 Shell 命令（通过 Ansible Tower） | `ShellPlugin` |
| `upload_file.py` | 文件上传 — 上传本地文件到远程主机（通过 Ansible Tower） | `UploadFilePlugin` |

## `plugins/ansible/tower_backend/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Ansible Tower (AWX) REST API 服务封装 — 插件后端执行引擎 | `TowerService` — Ansible Tower (AWX) REST API 服务<br>`get_tower_service()` — 获取 TowerService 单例 |
| `base.py` | Ansible Tower (AWX) 服务常量与异常 | `TowerConfigError` — Tower 配置错误<br>`TowerJobError` — Tower 作业执行错误<br>`TowerTimeoutError` — Tower 作业轮询超时 |
| `base_plugin.py` | TowerBasePlugin — 通过 Ansible Tower REST API 执行的插件基类 | `TowerBasePlugin` — 通过 Ansible Tower 执行的插件基类 |
| `client.py` | Ansible Tower — HTTP 客户端层 | `TowerClientMixin` — Tower HTTP 客户端 — 配置加载、Session 管理、统一请求 |
| `job.py` | Ansible Tower — 作业生命周期管理 | `TowerJobMixin` — Tower 作业管理 — 启动、查询、取消、结果提取 |
| `polling.py` | Ansible Tower — 主动轮询与状态推送 | `TowerPollingMixin` — Tower 轮询管理 — 自适应轮询、进度估算、WebSocket 推送 |

## `plugins/approval/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Approval Plugin — 审批原子，暂停流程并等待审批人操作 | — |
| `approval.py` | 审批原子 — Pipeline 执行到此处时暂停，等待指定审批人审批 | `ApprovalPlugin` |

## `plugins/cmdb/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | CMDB 集成插件包 | — |
| `query.py` | CMDB 查询插件 — 在 pipeline 执行过程中查询 CMDB 数据 | `CmdbQueryPlugin` — CMDB 查询 |
| `resource_selector.py` | CMDB 资源选择器 — 在工作流节点中选择 CMDB 资产作为执行目标 | `CmdbResourceSelector` — CMDB 资源选择器 |

## `plugins/common/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `manual_pause.py` | 手动暂停原子 — Pipeline 执行到此处时暂停，等待用户手动恢复 | `ManualPausePlugin` |
| `send_alert.py` | 发送告警 — 发送通知到指定渠道 | `SendAlertPlugin` |
| `send_email.py` | 发送邮件 — 通过 SMTP 发送电子邮件通知 | `SendEmailPlugin` |
| `test_print_time.py` | 测试打印时间 — 后台打印当前时间，用于流程引擎功能验证 | `TestPrintTimePlugin` |

## `plugins/esxi/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `attach_disk.py` | 挂载磁盘到 ESXi 虚拟机 | `EsxiAttachDiskPlugin` |
| `clone_vm.py` | 克隆 ESXi 虚拟机 — 从源虚拟机克隆为新虚拟机 | `EsxiCloneVmPlugin` |
| `create_snapshot.py` | 创建 ESXi 虚拟机快照 | `EsxiCreateSnapshotPlugin` |
| `create_vm.py` | 在 ESXi/vCenter 上创建虚拟机 | `EsxiCreateVmPlugin` |
| `destroy_vm.py` | 删除 ESXi 上的虚拟机 | `EsxiDestroyVmPlugin` |
| `get_state.py` | 查询 ESXi 虚拟机状态 | `EsxiGetStatePlugin` |
| `power_off.py` | 关闭 ESXi 虚拟机 (强制关机) | `EsxiPowerOffPlugin` |
| `power_on.py` | 启动 ESXi 虚拟机 | `EsxiPowerOnPlugin` |
| `reboot.py` | 重启 ESXi 虚拟机 (Guest OS Reboot / Hard Reset) | `EsxiRebootPlugin` |
| `reconfigure_vm.py` | 修改 ESXi 虚拟机配置 — CPU / 内存热调整 | `EsxiReconfigureVmPlugin` |
| `remove_snapshot.py` | 删除 ESXi 虚拟机快照 | `EsxiRemoveSnapshotPlugin` |
| `revert_snapshot.py` | 恢复 ESXi 虚拟机快照 | `EsxiRevertSnapshotPlugin` |

## `plugins/http/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `api_call.py` | HTTP API 调用 — 发送 HTTP 请求到目标 API | `HttpApiPlugin` |

## `plugins/itsm/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | ITSM plugin package — create/update tickets from OpsFlow executions | — |
| `create_ticket.py` | Create ITSM Ticket — 在 OpsFlow 执行节点中创建 ITSM 工单 | `CreateItsmTicketPlugin` |
| `update_ticket.py` | Update ITSM Ticket — 在 OpsFlow 执行节点中更新 ITSM 工单 | `UpdateItsmTicketPlugin` |

## `plugins/monitor/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `disk_check.py` | 磁盘检查 — 检查远程主机磁盘使用率，超过阈值可触发告警 | `DiskCheckPlugin` |
| `health_check.py` | 健康检查 — Ping + 端口检测 | `HealthCheckPlugin` |
| `ping_test.py` | Ping 测试 — 测试目标主机的网络连通性 | `PingTestPlugin` |

## `plugins/netapp/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `netapp_create_snapshot.py` | NetApp 存储卷快照 — 为 NetApp 存储卷创建快照 | `NetappCreateSnapshotPlugin` |
| `netapp_create_volume.py` | NetApp 创建卷 — 在 NetApp ONTAP 上创建 FlexVol 存储卷 | `NetappCreateVolumePlugin` |
| `netapp_delete_volume.py` | NetApp 删除卷 — 删除 NetApp 存储卷 | `NetappDeleteVolumePlugin` |
| `netapp_get_volume.py` | NetApp 查询卷 — 查询 NetApp 存储卷详情 | `NetappGetVolumePlugin` |
| `netapp_modify_volume.py` | NetApp 修改卷 — 修改 NetApp 卷属性 (扩容/改策略) | `NetappModifyVolumePlugin` |

## `plugins/pmax/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `performance.py` | Dell PowerMax 性能监控 — 查询阵列和存储组性能指标 | `GetPerformancePlugin` |
| `snapshot.py` | Dell PowerMax 快照管理 — 创建、查看、删除快照 | `CreateSnapshotPlugin`<br>`DeleteSnapshotPlugin` |
| `storage_group.py` | Dell PowerMax 存储组管理 — 创建、查询、删除存储组 | `CreateStorageGroupPlugin`<br>`DeleteStorageGroupPlugin`<br>`ListStorageGroupsPlugin` |

## `plugins/process/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `process_start.py` | 进程启动 — 通过 Ansible Tower 远程启动目标进程 | `ProcessStartPlugin` |
| `process_status.py` | 进程状态检查 — 通过 Ansible Tower 检查远程进程状态 | `ProcessStatusPlugin` |
| `process_stop.py` | 进程停止 — 通过 Ansible Tower 远程停止目标进程 | `ProcessStopPlugin` |

## `plugins/redfish/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `redfish_firmware_inventory.py` | Redfish 固件清单 — 通过 BMC 获取服务器固件版本清单 | `RedfishFirmwareInventoryPlugin` |
| `redfish_get_system_info.py` | Redfish 获取系统信息 — 通过 BMC 获取服务器硬件信息 | `RedfishGetSystemInfoPlugin` |
| `redfish_list_storage.py` | Redfish 存储清单 — 通过 BMC 获取存储控制器信息 | `RedfishListStoragePlugin` |
| `redfish_power_cycle.py` | Redfish 重启 — 通过 BMC 远程重启/重置服务器 | `RedfishPowerCyclePlugin` |
| `redfish_power_off.py` | Redfish 关机 — 通过 BMC 远程关机 | `RedfishPowerOffPlugin` |
| `redfish_power_on.py` | Redfish 开机 — 通过 BMC 远程开机 | `RedfishPowerOnPlugin` |
| `redfish_set_boot_device.py` | Redfish 设置启动设备 — 通过 BMC 设置下次启动设备 | `RedfishSetBootDevicePlugin` |

## `plugins/servicenow/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `servicenow_create_change_request.py` | ServiceNow 创建变更 — 创建 ServiceNow 变更申请 | `ServicenowCreateChangeRequestPlugin` |
| `servicenow_create_incident.py` | ServiceNow 创建事件 — 创建 ServiceNow 事件记录 | `ServicenowCreateIncidentPlugin` |
| `servicenow_get_cmdb_ci.py` | ServiceNow CMDB CI 查询 | `ServiceNowGetCmbdCiPlugin` |
| `servicenow_get_incident.py` | ServiceNow 查询事件 — 获取 ServiceNow 事件详情 | `ServicenowGetIncidentPlugin` |
| `servicenow_update_incident.py` | ServiceNow 更新事件 — 更新 ServiceNow 事件记录 | `ServicenowUpdateIncidentPlugin` |

## `plugins/verify/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `ip_ops_verify.py` | IP 运维验证原子 — 用于验证 IP 选择器/资源选择/表格/级联功能 | `IpOpsVerifyPlugin` |

## `schema/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `form_schema.py` | 表单配置协议 — 定义插件入参的描述模型 | `ValidationType`<br>`ValidationRule`<br>`FormEvent` — 跨字段联动事件<br>`FormItem` — 单个表单字段<br>`FormGroup` — 分组/组合 — 递归包含 FormItem 或其他 FormGroup |

## `services/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `dr_service.py` | DR 拓扑服务 — Neo4j 查询 + AI Prompt + 拓扑描述 | `get_dr_group_topology()` — 基于 Neo4j 查询 DR 组拓扑—Application 级<br>`neighbors_to_pipeline()` — 将 Application 级拓扑数据生成为标准 pipeline 格式（支持 CALLS 依赖排序）<br>`build_topology_description()` — 将拓扑数据转为 AI 可读的文本描述（Application 级） |
| `vector_service.py` | 向量嵌入服务 — 将知识条目转为向量存入数据库
Vector Embedding Service — Convert knowledge entries to vectors for similarity search | `VectorService` — 向量嵌入服务 — Vector Embedding Service |

## `signals/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Pipeline 信号处理器 — 追踪 BambooDjangoRuntime ERI 状态变更 | — |
| `cmdb_events.py` | CMDB 变更事件 — CMDB 数据变更时触发 Pipeline 或 Webhook | `CmdbEventEmitter` — CMDB 变更事件发射器 |
| `handlers.py` | Signal handlers — on_post_set_state 接收器和根节点状态管理器 | `on_post_set_state()` — BambooDjangoRuntime 节点状态变更信号处理器 |
| `helpers.py` | Helper functions — 信号处理中使用的工具函数 | — |
| `state.py` | State management — 节点状态持久化和状态树增量更新 | — |
| `timeout.py` | 超时追踪 — 节点状态变更时更新 Redis 超时集合 | — |
| `trace.py` | Trace management — 节点执行轨迹、日志记录、OpsLog 写入 | — |

## `tests/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `test_auto_retry.py` | 自动重试策略测试 — AutoRetryStrategyCreator + dispatch_auto_retry | `TestAutoRetryStrategyCreator` — AutoRetryStrategyCreator.batch_create_strategy 测试<br>`TestDispatchAutoRetry` — dispatch_auto_retry 测试 |
| `test_bamboo_builder.py` | bamboo_builder 测试 — build_bamboo_pipeline / _create_element / validate_bamboo_compatibility | `TestCreateElement` — _create_element 元素工厂<br>`TestBuildBambooPipeline` — build_bamboo_pipeline 完整构建<br>`TestValidateBambooCompatibility` — validate_bamboo_compatibility 校验<br>`TestExclusiveGatewayBuild` — 排他网关 — 元素创建 + 完整流程<br>`TestParallelGatewayBuild` — 并行网关 — 元素创建 + 完整流程 |
| `test_conflict_checker.py` | Conflict Checker 冲突检测 — 排他网关规则专项测试 | `TestExclusiveGatewayConflictRules` — 排他网关冲突检测 — Rule 6: 出边条件表达式<br>`TestParallelGatewayConflictRules` — 并行网关冲突检测 — Rule 4: 缺少汇聚网关 |
| `test_e2e_pipeline.py` | End-to-end pipeline execution tests — 串行/并行/排他/回环/loop全部场景 | `PipelineE2ETest` |
| `test_execution_api.py` | API integration tests — FlowExecutionViewSet | `ExecAPITestBase`<br>`ExecutionListTest`<br>`ExecutionDetailTest`<br>`ExecutionLifecycleTest`<br>`ExecutionNodeCommandTest` |
| `test_flow_engine.py` | FlowEngine 测试 — 状态管理 + run/retry/skip | `TestFlowEngineStateManagement` — FlowEngine 状态管理 — 不需要 bamboo 依赖<br>`TestFlowEngineRun` — FlowEngine.run() — pipline 构建+执行<br>`TestFlowEngineWSNotification` — WebSocket 通知（best-effort） |
| `test_gateway_execution.py` | 排他网关（Exclusive Gateway）完整执行流程测试 | `TestExclusiveGatewayPipelineBuild` — 排他网关 pipeline 构建验证<br>`TestExclusiveGatewayFlowEngineRun` — FlowEngine.run() 与排他网关集成测试<br>`TestExclusiveGatewayNodeCommands` — 排他网关场景下的节点操作（retry/skip/force_fail） |
| `test_gateway_signal.py` | 排他网关信号处理测试 — 节点状态更新 + 状态树增量 | `TestExclusiveGatewaySignalStateUpdate` — 排他网关场景下 _update_execution_node_status 和 _update_state_tree<br>`TestExclusiveGatewaySignalHandler` — on_post_set_state 信号处理器在排他网关场景下的行为<br>`TestWsNodeStatusPush` — _push_node_status_via_ws WebSocket 推送测试 |
| `test_layout.py` | Integration tests for the ai_layout API endpoint. | `TestAiLayoutEndpoint` — Tests for FlowTemplateViewSet.ai_layout method. |
| `test_mako_resolver.py` | Mako 模板变量解析测试 | `TestMakoResolver` |
| `test_manual_pause.py` | Manual Pause 原子测试 — ManualPausePlugin / PluginService 集成 | `TestManualPausePlugin` — ManualPausePlugin 原子<br>`TestPluginServiceManualPause` — PluginService.execute 中 manual_pause 暂停触发 |
| `test_node_sync.py` | 节点持久化同步测试 — 测试 extract_nodes_from_tree 数据转换逻辑 | `TestExtractNodes` — extract_nodes_from_tree — 将 pipeline_tree JSON 转换为标准节点列表 |
| `test_node_timeout_strategy.py` | 节点超时策略测试 — batch_create_timeout_configs / update_node_timeout / dispatch_timeout_nodes / 策略实现 | `TestBatchCreateTimeoutConfigs` — batch_create_timeout_configs 测试<br>`TestUpdateNodeTimeout` — update_node_timeout 测试（Redis 交互）<br>`TestDispatchTimeoutNodes` — dispatch_timeout_nodes 测试<br>`TestForcedFailStrategy` — ForcedFailStrategy 测试<br>`TestForcedFailAndSkipStrategy` — ForcedFailAndSkipStrategy 测试 |
| `test_optional_skip.py` | Optional 节点失败自动跳过测试 — _check_optional_skip / on_post_set_state 集成 | `TestCheckOptionalSkip` — _check_optional_skip 辅助函数<br>`TestOptionalSkipInSignal` — on_post_set_state 信号中 optional skip 集成 |
| `test_parallel_gateway.py` | 并行网关（Parallel Gateway）完整执行流程测试 | `TestParallelGatewayBuild` — 并行网关 pipeline 构建验证<br>`TestParallelGatewayFlowEngine` — FlowEngine.run() 与并行网关集成测试 |
| `test_safety_guard.py` | Pipeline 安全校验测试 — validate_pipeline 各种场景 | `TestValidatePipeline` — validate_pipeline 核心逻辑 |
| `test_states.py` | 状态机测试 — NodeState / PipelineState 转移矩阵 | `TestNodeState` — 节点状态转移矩阵验证<br>`TestPipelineState` — Pipeline 级状态转移矩阵验证<br>`TestMapBambooNodeState` — bamboo-engine 状态 → NodeState 映射 |
| `test_template_api.py` | API integration tests — FlowTemplate edit lock | `TemplateLockTest` — TemplateLock acquire/release actions (do not use ProjectFilt |
| `test_template_lock.py` | TemplateLock tests — acquire/release/heartbeat/expiry/update guard | `TemplateLockAcquireTest` — acquire_lock happy path and conflict detection<br>`TemplateLockExpiryTest` — is_expired and heartbeat timeout<br>`TemplateLockReleaseTest` — release_lock idempotency<br>`TemplateLoopIterationTest` — _resolve_loop_iteration increment logic |
| `test_trace.py` | 执行轨迹双树结构 — 测试用例 | `NodeExecutionTraceModelTest` — Test NodeExecutionTrace model constraints and defaults<br>`NodeTraceLoggerTest` — Test NodeTraceLogger file I/O<br>`UpdateStateTreeTest` — Test _update_state_tree helper<br>`NodeCommandDispatcherTest` — Test NodeCommandDispatcher retry/skip/trace |
| `test_variable_registry.py` | 变量注册表测试 — RegisterVariableMeta 自动注册 + VariableLibrary 检索 | `TestVariableRegistry` — RegisterVariableMeta 自动注册<br>`TestVariableLibrary` — VariableLibrary 检索和解析<br>`TestLazyVariable` — LazyVariable get_value() 自定义转换 |
| `test_variable_resolver.py` | 变量解析引擎测试 — resolve_variables / build_execution_context / get_variable_reference_details | `TestResolveVariables` — resolve_variables 核心替换逻辑<br>`TestSplitValue` — split_value 字符串分割<br>`TestDeepGet` — _deep_get 嵌套路径查找<br>`TestBuildExecutionContext` — build_execution_context 上下文构建 (mock execution)<br>`TestGetVariableReferenceDetails` — get_variable_reference_details — 变量引用明细追踪 |

## `views/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `aliyun_views.py` | 阿里云 ECS 资源查询 API — 供表单 async_select 动态加载数据 | `describe_images()`<br>`describe_instance_types()`<br>`describe_security_groups()`<br>`describe_vswitches()`<br>`describe_regions()` |
| `audit_views.py` | 操作审计视图 — 只读查询接口 | `OperationRecordViewSet` — 操作审计记录 — 只读 |
| `base.py` | ViewSet base class — project isolation + multi-tenant permission support | `ProjectFilteredViewSet` — Project-scoped ViewSet with multi-tenant permission enforcem<br>`ProjectReadOnlyViewSet` — Read-only variant — disables all write operations. |
| `clause_views.py` | — | `PrivacyView` — OpsFlow Privacy Policy (隐私政策)<br>`TermsServiceView` — OpsFlow Terms of Service (服务条款) |
| `execution_views.py` | FlowExecution ViewSet — 执行 CRUD | `FlowExecutionViewSet` |
| `knowledge_views.py` | — | `OpsKnowledgeViewSet` |
| `log_views.py` | — | `OpsLogViewSet` — OpsLog 通过 execution.project 间接隔离，不直接设 project FK |
| `node_views.py` | 节点视图 — 提供 TemplateNode / ExecutionNode 的只读查询接口 | `TemplateNodeViewSet` — 模板节点 — 只读，支持按 template / node_type / atom_type 过滤<br>`ExecutionNodeViewSet` — 执行节点 — 只读，支持按 execution / node_type / status 过滤 |
| `plugin_views.py` | 标准插件 API — 对接前端 RenderForm 的插件元数据和表单配置 | `PluginViewSet` — 标准插件只读接口 — 提供插件列表、详情、分组树 |
| `project_views.py` | Project ViewSet — 项目 CRUD + 成员管理 + 我的项目 | `OpsProjectViewSet` — 项目管理 CRUD + 成员管理 |
| `schedule_views.py` | — | `SchedulePlanViewSet` |
| `scheme_views.py` | ExecutionScheme ViewSet — 执行方案 CRUD（嵌套于模板下） | `ExecutionSchemeViewSet` — 执行方案 CRUD — 预定义节点排除集 + 变量覆盖 |
| `template_category_views.py` | 模板分类 API | `TemplateCategoryViewSet` |
| `template_views.py` | FlowTemplate ViewSet — 流程模板 CRUD | `FlowTemplateViewSet` |

## `views/dashboard_views/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | Dashboard API endpoints — 为 urls.py 向后兼容重新导出 | — |
| `analytics.py` | Dashboard — 分析/分布端点（top_templates, user_activity, 分布, 排行等） | `dashboard_top_templates()` — Top N templates ranked by execution count (with success rate<br>`dashboard_user_activity()` — User execution activity statistics<br>`dashboard_status_distribution()` — Execution status distribution<br>`dashboard_node_type_distribution()` — Node type distribution (aggregated by atom_type from NodeExe<br>`dashboard_duration_distribution()` — 执行耗时分布 — 按耗时区间统计执行次数 |
| `stats.py` | Dashboard — 聚合统计 + 调度统计端点 | `dashboard_stats()` — Return aggregate statistics for the opsflow dashboard (inclu<br>`dashboard_schedule_stats()` — Return detailed scheduler statistics for the dashboard. |
| `trends.py` | Dashboard — 执行趋势 + 成功率趋势端点 | `dashboard_trend()` — Return execution trend data per day for the last N days (def<br>`dashboard_success_rate_trend()` — 每日成功率趋势 — 按日聚合执行成功/失败数量及成功率 |

## `views/mixins/`

| File | Purpose | Core Components |
|------|---------|-----------------|
| `__init__.py` | — | — |
| `execution_approval.py` | Execution Approval — 审批/拒绝端点 Mixin | `ExecutionApprovalMixin` — 审批端点混入（approve/reject/pending_approval） |
| `execution_lifecycle.py` | Execution Lifecycle — 启动/暂停/恢复/取消端点 Mixin | `ExecutionLifecycleMixin` — 执行生命周期端点混入（start/pause/resume/cancel） |
| `execution_node_command.py` | Execution Node Commands — 节点操作/批量/子流程重试端点 Mixin | `ExecutionNodeCommandMixin` — 节点操作端点混入（retry/skip/force_fail/batch/subprocess） |
| `execution_trace.py` | Execution Trace — 节点轨迹查询端点 Mixin | `ExecutionTraceMixin` — 节点轨迹查询端点混入（traces/trace_log） |
| `template_ai.py` | Template AI — AI 生成/分析/布局端点 Mixin | `TemplateAIMixin` — AI 生成、分析、布局端点混入 |
| `template_collect.py` | Template Collect — 收藏/取消收藏端点 Mixin | `TemplateCollectMixin` — 收藏管理端点混入 |
| `template_dr.py` | Template DR — AI 生成 DR 切换 Pipeline 端点 | `preview_dr_topology()` — 预览 DR 组拓扑 — 返回结构化的主站/备站进程 + CALLS 关系<br>`create_dr_pipeline()` — AI 生成 DR 切换 Pipeline |
| `template_export.py` | Template Export/Import — 导出/导入/分类端点 Mixin | `TemplateExportImportMixin` — 导出、导入、分类端点混入 |
| `template_subprocess.py` | Template Subprocess — 子流程版本追踪端点 Mixin | `TemplateSubprocessMixin` — 子流程版本追踪端点混入 |
| `template_variable.py` | Template Variable — 全局变量/变量浏览器/变量提升端点 Mixin | `TemplateVariableMixin` — 全局变量系统端点混入 |
| `template_version.py` | Template Version — 版本管理/发布/回滚端点 Mixin | `TemplateVersionMixin` — 版本管理、发布、回滚端点混入 |
| `template_webhook.py` | Template Webhook — 模板 Webhook 回调配置端点 Mixin | `TemplateWebhookMixin` — 模板 Webhook CRUD + 日志查询 |
