# opsflow — 模块索引
> 上次自动更新: 2026-06-29 | 触发提交: 13c0882d
---

## `根目录`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  |  |
| `apps.py` |  | `OpsflowConfig — ` |
| `plugins\esxi\clone_vm.py` |  |  |
| `plugins\esxi\create_snapshot.py` |  |  |
| `plugins\esxi\reboot.py` |  |  |
| `plugins\esxi\reconfigure_vm.py` |  |  |
| `plugins\esxi\remove_snapshot.py` |  |  |
| `plugins\esxi\revert_snapshot.py` |  |  |
| `serializers.py` |  | `GlobalVariableField — 全局变量字段 — 接受扁平或结构化格式，始终返回结构化格式`<br>`FlowTemplateSerializer — `<br>`TemplateVersionSerializer — ` |
| `tasks.py` |  | `在 Celery worker 中安全执行异步协程。()`<br>`Celery 任务 — 异步执行 Pipeline()` |
| `tests\test_layout.py` |  |  |
| `urls.py` |  |  |

## `core`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\__init__.py` |  |  |
| `core\audit_logger.py` | 审计日志工具 — 记录用户操作到 OperationRecord 表 | `记录操作审计()` |
| `core\auto_retry.py` | 自动重试策略 — 节点 FAILED 时自动触发重试 | `AutoRetryStrategyCreator — 批量创建自动重试策略 — 在 FlowEngine.run() 开始时调用`<br>`检查并派发自动重试 — 在信号拦截到 FAILED 时调用()` |
| `core\bamboo_validator.py` | Bamboo Pipeline Tree 兼容性验证器 | `校验 pipeline_tree 是否能被 bamboo-engine 执行()` |
| `core\cloud_sync.py` | 阿里云 ECS → CMDB 实时同步 | `Pipeline 原子执行成功后触发 CMDB 同步()`<br>`将单个 ECS 实例同步到 CMDB :Host 节点()` |
| `core\conflict_checker.py` | 冲突检测规则引擎 — 检测节点配置中的语义冲突 | `检查 pipeline_tree 中的配置冲突()` |
| `core\error_codes.py` | 标准化错误码 — 全系统统一错误分类和封装 | `ErrorCodes — 错误码常量`<br>`标准成功响应()`<br>`标准错误响应()` |
| `core\flow_engine.py` | Flow Execution Engine — BambooDjangoRuntime + bamboo_engine.api | `FlowEngine — 流程执行引擎 — BambooDjangoRuntime 驱动（仅异步路径）` |
| `core\llm_service.py` | LLM 服务 — 通过集成中心调用 AI 完成流程生成/分析 | `Convert natural language to Pipeline Tree JSON()`<br>`Multi-turn: modify existing Pipeline Tree based on new instruction()` |
| `core\mako_resolver.py` | Mako 模板变量解析 — 安全沙箱封装 | `MakoResolver — 安全的类 Mako 表达式解析器`<br>`通用入口 — 检测 #{...} 走 Mako 路径，否则原样返回()` |
| `core\node_dispatcher.py` | NodeCommandDispatcher — 节点操作调度器 | `NodeCommandDispatcher — 节点操作调度器` |
| `core\node_sync.py` | 节点同步工具 — 在 pipeline_tree JSON 与 TemplateNode/ExecutionNode 模型间同步 | `从 pipeline_tree JSON 提取节点列表（标准格式，非可视化节点）()`<br>`将模板的 pipeline_tree 同步为 TemplateNode 行（全量删除重建）()` |
| `core\node_timeout_strategy.py` | 节点超时策略 — 超时后自动执行 forced_fail / forced_fail_and_skip | `NodeTimeoutStrategy — 节点超时策略基类`<br>`ForcedFailStrategy — 强制失败策略 — 调用 api.forced_fail_activity`<br>`ForcedFailAndSkipStrategy — 强制失败并跳过策略`<br>`遍历 pipeline_tree，为 timeout_seconds > 0 的节点创建超时配置()`<br>`获取 Redis 连接()` |
| `core\pipeline_preview.py` | Pipeline 预览与清理 — 执行方案预览树生成 | `PipelinePreviewService — 执行方案预览服务 — 根据排除节点生成清理后的 pipeline 树` |
| `core\pipeline_schema.py` | Pipeline Tree JSON Schema 验证 | `JSON Schema 结构验证()`<br>`校验全局变量键名格式()` |
| `core\plugin_deprecation.py` | 插件退役管理 — 检测已弃用插件在模板中的引用 | `递归扫描模板 pipeline_tree，检测已弃用的插件引用()` |
| `core\plugin_service_adapter.py` | bamboo-engine 适配层 — 通用 PluginService | `PluginService — 通用 Service — 所有原子通过这一个类路由到 BasePlugin.execute()`<br>`OpsflowPluginComponent — ` |
| `core\safety_guard.py` | Pipeline Tree 安全校验器 — 原子白名单从 PLUGIN_REGISTRY 动态加载 | `返回所有已注册插件的 code 集合()`<br>`返回 risk_level == 'high' 的插件 code 集合()` |
| `core\scheduler_service.py` |  | `OpsflowScheduler — APScheduler wrapper for managing SchedulePlan timed triggers` |
| `core\states.py` | 状态枚举与流转矩阵 — 节点生命周期 + Pipeline 级别状态 | `NodeState — 节点状态枚举 — 每个节点的生命周期状态`<br>`PipelineState — Pipeline 级状态枚举 — FlowExecution.status`<br>`检查节点状态转移是否合法，返回 True/False()`<br>`检查 Pipeline 级状态转移是否合法()` |
| `core\subprocess_dispatcher.py` | Independent Subprocess Dispatcher — runs subprocess as separate FlowExecution | `SubprocessDispatcher — Dispatches a subprocess node as an independent FlowExecution.` |
| `core\trace_logger.py` | 节点轨迹日志写入器 — 每个节点独立的 JSON Lines 日志文件 | `NodeTraceLogger — 节点轨迹日志写入器` |
| `core\variable_registry.py` | 变量注册表系统 — 适配自 bk_sops LazyVariable + VariableLibrary 模式 | `RegisterVariableMeta — 元类 — 在子类创建时自动注册到 VariableLibrary`<br>`SpliceVariable — 支持 ${key} 模板替换的变量基类`<br>`LazyVariable — 延迟计算变量 — 在模板替换后执行 get_value()` |
| `core\variable_resolver.py` | 变量解析引擎 — ${key} 模板变量替换 + 跨节点数据引用 | `规范化 global_vars 为包含元数据的结构化格式()`<br>`从规范化（或扁平）global_vars 中提取纯值 dict()` |
| `core\webhook_service.py` | Webhook 回调服务 — 执行完成/失败时发送 HTTP 回调 | `WebhookService — Webhook 回调服务` |

## `core/layout`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\layout\__init__.py` | Sugiyama layered graph layout engine for OPSflow. |  |
| `core\layout\acyclic.py` | Acyclic graph transformation — remove self-loops and reverse backward edges. | `Remove self-looping edges and store them for restoration.()`<br>`Restore previously removed self-loop edges.()` |
| `core\layout\constants.py` | Layout engine constants — replaces pipeline_web.constants.PWE. | `NodeType — `<br>`PipelineKey — ` |
| `core\layout\drawing.py` | Main orchestrator — wires all 5 phases of the Sugiyama layout algorithm. | `Execute the full Sugiyama layout pipeline on a pipeline tree.()` |
| `core\layout\dummy.py` | Long-edge splitting with dummy nodes + gateway fill-number computation. | `Replace edges spanning >1 rank with chains of DummyNode -> DummyFlow.()`<br>`Calculate extra vertical slots needed at each position for gateway branches.()` |
| `core\layout\layout_adapter.py` | OPSflow {nodes, edges} <-> pipeline tree format bridge. | `Convert OPSflow {nodes, edges} to a pipeline tree dict.()`<br>`Extract [{id, x, y}] from pipeline after draw_pipeline().()` |
| `core\layout\normalize.py` | Pipeline data normalization — build/remove all_nodes dictionary. | `Build flat all_nodes dict from pipeline sections.()`<br>`()` |
| `core\layout\position.py` | Coordinate assignment with arrow endpoint calculation. | `Assign x,y coordinates to all nodes and compute arrow endpoints for flows.()` |
| `core\layout\tests.py` | Unit tests for the Sugiyama layout engine. | `()`<br>`()` |
| `core\layout\utils.py` | Utility functions for flow ID management on nodes. | `Normalize incoming/outgoing to list.()`<br>`Add flow_id to node's incoming or outgoing list.()` |

## `core/layout/order`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\layout\order\__init__.py` |  |  |
| `core\layout\order\builder.py` | Stub for future layer graph builder. | `Placeholder.()` |
| `core\layout\order\order.py` | Crossing minimization via weighted-median heuristic (Sugiyama). | `Assign node order within each rank to minimize edge crossings.()`<br>`Initialize per-rank node ordering via topological traversal from start.()` |

## `core/layout/rank`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\layout\rank\__init__.py` |  |  |
| `core\layout\rank\feasible_tree.py` | Feasible-tree rank refinement — minimize total edge length. | `Refine ranks by building a spanning tree of tight edges,()` |
| `core\layout\rank\longest_path.py` | Longest-path rank assignment — initial rank for each node. | `Assign each node a rank equal to length of longest path from start node.()` |
| `core\layout\rank\tight_tree.py` | Tight-tree rank orchestrator — longest-path then feasible-tree refinement. | `Assign ranks using longest-path, then refine with feasible tree.()` |
| `core\layout\rank\utils.py` | Rank utility functions. | `()`<br>`()` |

## `core/pipeline_builder`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\pipeline_builder\__init__.py` | Pipeline Tree 构建器 — 将 FlowTemplate 的自定义 pipeline_tree 转换为 bamboo-engine 可执行格式 | `将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict()` |
| `core\pipeline_builder\elements.py` | pipeline 构建 - 节点元素创建 |  |
| `core\pipeline_builder\validation.py` | pipeline 构建 - 循环引用检测 |  |

## `core/variable_types`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `core\variable_types\__init__.py` | 变量类型包 — 导入此模块触发所有变量类注册到 VARIABLE_REGISTRY |  |
| `core\variable_types\common.py` | 通用变量类型 — 适配自 bk_sops pipeline_plugins.variables.collections.common | `InputVariable — 文本输入变量`<br>`TextareaVariable — 多行文本变量`<br>`IntVariable — 整数变量` |

## `management`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\__init__.py` |  |  |

## `management/commands`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\commands\__init__.py` |  |  |
| `management\commands\backfill_plugin_en.py` | 为所有插件自动补齐 name_en / description_en / form_schema name_en | `Command — ` |
| `management\commands\clean_expired_locks.py` | Clean expired template editing locks — heartbeat > 60s old. | `Command — ` |
| `management\commands\clean_node_trace_logs.py` | 清理 N 天前的节点轨迹日志文件 | `Command — ` |
| `management\commands\clean_opsflow_data.py` | 清理过期 OpsFlow 数据 — DB 记录 + 日志文件 | `Command — ` |
| `management\commands\fix_node_status_double_encode.py` | Management command — 修复 MySQL JSON_SET 双层编码导致的 node_status 值错误 | `Command — `<br>`检查值是否带双层引号：字符串以 " 开头和结尾且长度 > 2()`<br>`去掉外层引号：'"completed"' → 'completed'()` |
| `management\commands\fix_timezone_data.py` | Timezone data migration — correct existing naive Asia/Shanghai datetimes for USE_TZ=True | `Command — ` |
| `management\commands\index_knowledge.py` | Index all knowledge entries for vector search.
批量索引所有知识条目以供向量搜索。 | `Command — ` |
| `management\commands\scan_plugins.py` | 扫描插件目录并注册新插件 | `Command — ` |
| `management\commands\seed_opsflow.py` | Seed OpsFlow reference & mock data | `Command — `<br>`Command — ` |
| `management\commands\seed_template_presets.py` | Seed Template Presets — 10 个常见 IT 运维场景预设提示词 (中英双语) | `Command — ` |
| `management\commands\start_opsflow_scheduler.py` |  | `Command — ` |

## `models`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models\__init__.py` |  |  |
| `models\audit.py` |  | `OperationRecord — 操作审计记录 — 记录所有重要用户操作`<br>`OpsLog — 审计日志 — 每一步的详细执行记录` |
| `models\auth.py` |  | `ApiToken — 外部 API Token — 用于第三方系统认证，绑定 Business + Deployment Environment` |
| `models\env.py` |  | `ProjectEnvironmentVariable — 项目级环境变量 — 跨模板共享的配置值` |
| `models\execution.py` |  | `FlowExecution — 执行实例 — 一次流程运行记录`<br>`ExecutionNode — 执行节点 — 执行实例中的节点记录，从 TemplateNode 同步`<br>`ExecutionScheme — 执行方案 — 预定义的节点排除集 + 变量覆盖` |
| `models\knowledge.py` |  | `OpsKnowledge — RAG 知识库 — 历史案例/故障/文档` |
| `models\plugin.py` |  | `PluginMeta — 标准插件元数据 — 注册时自动同步（支持多版本）` |
| `models\schedule.py` |  | `SchedulePlan — 调度计划 — 一次性或周期性自动执行` |
| `models\template.py` |  | `FlowTemplate — 编排模板 — AI 生成的或人工创建的流程定义`<br>`TemplateVersion — 模板版本历史 — 每次发布时创建`<br>`TemplateNode — 模板节点 — 从 pipeline_tree JSON 同步为独立行，支持 SQL 查询` |
| `models\webhook.py` |  | `WebhookConfig — Webhook 回调配置 — 绑定到模板，执行完成后触发`<br>`WebhookLog — Webhook 投递日志` |

## `plugins`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\__init__.py` |  |  |
| `plugins\base.py` | BasePlugin 基类 — 所有标准插件继承此类 | `BasePlugin — 标准插件基类 — 每个运维原子（技能）继承此类` |
| `plugins\loader.py` | Plugin 热加载器 — 文件快照 + 增量注册 | `PluginLoader — 插件热加载器` |
| `plugins\registry.py` | 插件注册中心 — 自动扫描 plugins/ 下所有 BasePlugin 子类 | `扫描 opsflow/plugins/ 下所有模块，自动注册 BasePlugin 子类()`<br>`获取插件类，version=None 时返回最新版本()` |

## `plugins/agent`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\agent\__init__.py` | Agent 远程执行插件 — 通过 Agent 在被管控主机上执行命令和脚本 |  |
| `plugins\agent\agent_process_restart.py` | agent_process_restart — 通过 Agent 远程重启应用进程 | `AgentProcessRestartPlugin — ` |
| `plugins\agent\agent_process_start.py` | agent_process_start — 通过 Agent 远程启动应用进程 | `AgentProcessStartPlugin — ` |
| `plugins\agent\agent_process_status.py` | agent_process_status — 通过 Agent 查询应用进程状态 | `AgentProcessStatusPlugin — ` |
| `plugins\agent\agent_process_stop.py` | agent_process_stop — 通过 Agent 远程停止应用进程 | `AgentProcessStopPlugin — ` |
| `plugins\agent\exec_cmd.py` | agent_exec_cmd — 通过 Agent 远程执行命令/脚本 | `AgentExecCmdPlugin — ` |
| `plugins\agent\file_pull.py` | agent_file_pull — 通过 Agent Agent 从目标主机拉取文件 | `AgentFilePullPlugin — ` |
| `plugins\agent\file_push.py` | agent_file_push — 通过 Agent Agent 推送文件到目标主机 | `AgentFilePushPlugin — ` |

## `plugins/ai`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\ai\__init__.py` |  |  |
| `plugins\ai\ai_text_gen.py` | AI Text Generation Plugin — 调用 LLM 生成文本 / AI Text Generation Atom | `AiTextGenPlugin — ` |

## `plugins/aliyun_ecs`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\aliyun_ecs\__init__.py` |  |  |
| `plugins\aliyun_ecs\_client.py` | 阿里云 ECS SDK 客户端工厂 — 复用集成中心凭证 | `获取阿里云 ECS SDK AcsClient()`<br>`从 CMDB 查询阿里云实例的地域()` |
| `plugins\aliyun_ecs\create_image.py` | 创建自定义镜像 | `AliyunEcsCreateImagePlugin — ` |
| `plugins\aliyun_ecs\create_instance.py` | 创建 ECS 实例（含可选公网 IP 分配） | `AliyunEcsCreatePlugin — ` |
| `plugins\aliyun_ecs\delete_instance.py` | 释放 ECS 实例 | `AliyunEcsDeletePlugin — ` |
| `plugins\aliyun_ecs\describe_instance.py` | 查询 ECS 实例详情 | `AliyunEcsDescribePlugin — ` |
| `plugins\aliyun_ecs\modify_instance.py` | 修改 ECS 实例属性（名称、描述） | `AliyunEcsModifyPlugin — ` |
| `plugins\aliyun_ecs\restart_instance.py` | 重启 ECS 实例 | `AliyunEcsRebootPlugin — ` |
| `plugins\aliyun_ecs\start_instance.py` | 启动 ECS 实例 | `AliyunEcsStartPlugin — ` |
| `plugins\aliyun_ecs\stop_instance.py` | 停止 ECS 实例 | `AliyunEcsStopPlugin — ` |

## `plugins/ansible`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\ansible\__init__.py` |  |  |
| `plugins\ansible\backup_file.py` | 文件备份 — 备份远程主机上的文件或目录（通过 Ansible Tower） | `BackupFilePlugin — ` |
| `plugins\ansible\docker_deploy.py` | Docker 部署 — 部署 Docker 容器（通过 Ansible Tower） | `DockerDeployPlugin — ` |
| `plugins\ansible\file_copy.py` | 文件复制 — 复制文件或目录到远程主机（通过 Ansible Tower） | `FileCopyPlugin — ` |
| `plugins\ansible\java_deploy.py` | Java 部署 — 部署 Java 应用（通过 Ansible Tower） | `JavaDeployPlugin — ` |
| `plugins\ansible\nginx_reload.py` | Nginx 重载 — 验证 Nginx 配置并执行重载（通过 Ansible Tower） | `NginxReloadPlugin — ` |
| `plugins\ansible\script_exec.py` | 脚本执行 — 上传脚本内容并在远程主机上执行（通过 Ansible Tower） | `ScriptExecPlugin — ` |
| `plugins\ansible\service_control.py` | 服务控制 — 控制系统服务的启动/停止/重启/重载状态（通过 Ansible Tower） | `ServiceControlPlugin — ` |
| `plugins\ansible\shell.py` | Shell 执行 — 在目标主机上执行 Shell 命令（通过 Ansible Tower） | `ShellPlugin — ` |
| `plugins\ansible\upload_file.py` | 文件上传 — 上传本地文件到远程主机（通过 Ansible Tower） | `UploadFilePlugin — ` |

## `plugins/ansible/tower_backend`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\ansible\tower_backend\__init__.py` | Ansible Tower (AWX) REST API 服务封装 — 插件后端执行引擎 | `TowerService — Ansible Tower (AWX) REST API 服务`<br>`获取 TowerService 单例()` |
| `plugins\ansible\tower_backend\base.py` | Ansible Tower (AWX) 服务常量与异常 | `TowerConfigError — Tower 配置错误`<br>`TowerJobError — Tower 作业执行错误`<br>`TowerTimeoutError — Tower 作业轮询超时` |
| `plugins\ansible\tower_backend\base_plugin.py` | TowerBasePlugin — 通过 Ansible Tower REST API 执行的插件基类 | `TowerBasePlugin — 通过 Ansible Tower 执行的插件基类` |
| `plugins\ansible\tower_backend\client.py` | Ansible Tower — HTTP 客户端层 | `TowerClientMixin — Tower HTTP 客户端 — 配置加载、Session 管理、统一请求` |
| `plugins\ansible\tower_backend\job.py` | Ansible Tower — 作业生命周期管理 | `TowerJobMixin — Tower 作业管理 — 启动、查询、取消、结果提取` |
| `plugins\ansible\tower_backend\polling.py` | Ansible Tower — 主动轮询与状态推送 | `TowerPollingMixin — Tower 轮询管理 — 自适应轮询、进度估算、WebSocket 推送` |

## `plugins/cmdb`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\cmdb\__init__.py` | CMDB 集成插件包 |  |
| `plugins\cmdb\query.py` | CMDB 查询插件 — 在 pipeline 执行过程中查询 CMDB 数据 | `CmdbQueryPlugin — CMDB 查询` |
| `plugins\cmdb\resource_selector.py` | CMDB 资源选择器 — 在工作流节点中选择 CMDB 资产作为执行目标 | `CmdbResourceSelector — CMDB 资源选择器` |

## `plugins/common`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\common\__init__.py` |  |  |
| `plugins\common\manual_pause.py` | 手动暂停原子 — Pipeline 执行到此处时暂停，等待用户手动恢复 | `ManualPausePlugin — ` |
| `plugins\common\send_alert.py` | 发送告警 — 发送通知到指定渠道 | `SendAlertPlugin — ` |
| `plugins\common\send_email.py` | 发送邮件 — 通过 SMTP 发送电子邮件通知 | `SendEmailPlugin — ` |
| `plugins\common\test_print_time.py` | 测试打印时间 — 后台打印当前时间，用于流程引擎功能验证 | `TestPrintTimePlugin — ` |

## `plugins/esxi`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\esxi\__init__.py` |  |  |
| `plugins\esxi\attach_disk.py` | 挂载磁盘到 ESXi 虚拟机 | `EsxiAttachDiskPlugin — ` |
| `plugins\esxi\create_vm.py` | 在 ESXi/vCenter 上创建虚拟机 | `EsxiCreateVmPlugin — ` |
| `plugins\esxi\destroy_vm.py` | 删除 ESXi 上的虚拟机 | `EsxiDestroyVmPlugin — ` |
| `plugins\esxi\get_state.py` | 查询 ESXi 虚拟机状态 | `EsxiGetStatePlugin — ` |
| `plugins\esxi\power_off.py` | 关闭 ESXi 虚拟机 (强制关机) | `EsxiPowerOffPlugin — ` |
| `plugins\esxi\power_on.py` | 启动 ESXi 虚拟机 | `EsxiPowerOnPlugin — ` |

## `plugins/http`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\http\__init__.py` |  |  |
| `plugins\http\api_call.py` | HTTP API 调用 — 发送 HTTP 请求到目标 API | `HttpApiPlugin — ` |

## `plugins/itsm`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\itsm\__init__.py` | ITSM plugin package — create/update tickets from OpsFlow executions |  |
| `plugins\itsm\create_ticket.py` | Create ITSM Ticket — 在 OpsFlow 执行节点中创建 ITSM 工单 | `CreateItsmTicketPlugin — ` |
| `plugins\itsm\update_ticket.py` | Update ITSM Ticket — 在 OpsFlow 执行节点中更新 ITSM 工单 | `UpdateItsmTicketPlugin — ` |

## `plugins/monitor`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\monitor\__init__.py` |  |  |
| `plugins\monitor\disk_check.py` | 磁盘检查 — 检查远程主机磁盘使用率，超过阈值可触发告警 | `DiskCheckPlugin — ` |
| `plugins\monitor\health_check.py` | 健康检查 — Ping + 端口检测 | `HealthCheckPlugin — ` |
| `plugins\monitor\ping_test.py` | Ping 测试 — 测试目标主机的网络连通性 | `PingTestPlugin — ` |

## `plugins/netapp`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\netapp\__init__.py` |  |  |
| `plugins\netapp\netapp_create_snapshot.py` | NetApp 存储卷快照 — 为 NetApp 存储卷创建快照 | `NetappCreateSnapshotPlugin — ` |
| `plugins\netapp\netapp_create_volume.py` | NetApp 创建卷 — 在 NetApp ONTAP 上创建 FlexVol 存储卷 | `NetappCreateVolumePlugin — ` |
| `plugins\netapp\netapp_delete_volume.py` | NetApp 删除卷 — 删除 NetApp 存储卷 | `NetappDeleteVolumePlugin — ` |
| `plugins\netapp\netapp_get_volume.py` | NetApp 查询卷 — 查询 NetApp 存储卷详情 | `NetappGetVolumePlugin — ` |
| `plugins\netapp\netapp_modify_volume.py` | NetApp 修改卷 — 修改 NetApp 卷属性 (扩容/改策略) | `NetappModifyVolumePlugin — ` |

## `plugins/pmax`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\pmax\__init__.py` |  |  |
| `plugins\pmax\performance.py` | Dell PowerMax 性能监控 — 查询阵列和存储组性能指标 | `GetPerformancePlugin — ` |
| `plugins\pmax\snapshot.py` | Dell PowerMax 快照管理 — 创建、查看、删除快照 | `CreateSnapshotPlugin — `<br>`DeleteSnapshotPlugin — ` |
| `plugins\pmax\storage_group.py` | Dell PowerMax 存储组管理 — 创建、查询、删除存储组 | `CreateStorageGroupPlugin — `<br>`DeleteStorageGroupPlugin — `<br>`ListStorageGroupsPlugin — ` |

## `plugins/process`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\process\__init__.py` |  |  |
| `plugins\process\process_start.py` | 进程启动 — 通过 Ansible Tower 远程启动目标进程 | `ProcessStartPlugin — ` |
| `plugins\process\process_status.py` | 进程状态检查 — 通过 Ansible Tower 检查远程进程状态 | `ProcessStatusPlugin — ` |
| `plugins\process\process_stop.py` | 进程停止 — 通过 Ansible Tower 远程停止目标进程 | `ProcessStopPlugin — ` |

## `plugins/redfish`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\redfish\__init__.py` |  |  |
| `plugins\redfish\redfish_firmware_inventory.py` | Redfish 固件清单 — 通过 BMC 获取服务器固件版本清单 | `RedfishFirmwareInventoryPlugin — ` |
| `plugins\redfish\redfish_get_system_info.py` | Redfish 获取系统信息 — 通过 BMC 获取服务器硬件信息 | `RedfishGetSystemInfoPlugin — ` |
| `plugins\redfish\redfish_list_storage.py` | Redfish 存储清单 — 通过 BMC 获取存储控制器信息 | `RedfishListStoragePlugin — ` |
| `plugins\redfish\redfish_power_cycle.py` | Redfish 重启 — 通过 BMC 远程重启/重置服务器 | `RedfishPowerCyclePlugin — ` |
| `plugins\redfish\redfish_power_off.py` | Redfish 关机 — 通过 BMC 远程关机 | `RedfishPowerOffPlugin — ` |
| `plugins\redfish\redfish_power_on.py` | Redfish 开机 — 通过 BMC 远程开机 | `RedfishPowerOnPlugin — ` |
| `plugins\redfish\redfish_set_boot_device.py` | Redfish 设置启动设备 — 通过 BMC 设置下次启动设备 | `RedfishSetBootDevicePlugin — ` |

## `plugins/servicenow`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\servicenow\__init__.py` |  |  |
| `plugins\servicenow\servicenow_create_change_request.py` | ServiceNow 创建变更 — 创建 ServiceNow 变更申请 | `ServicenowCreateChangeRequestPlugin — ` |
| `plugins\servicenow\servicenow_create_incident.py` | ServiceNow 创建事件 — 创建 ServiceNow 事件记录 | `ServicenowCreateIncidentPlugin — ` |
| `plugins\servicenow\servicenow_get_cmdb_ci.py` | ServiceNow CMDB 查询 — 查询 ServiceNow CMDB CI 信息 | `ServicenowGetCmdbCiPlugin — ` |
| `plugins\servicenow\servicenow_get_incident.py` | ServiceNow 查询事件 — 获取 ServiceNow 事件详情 | `ServicenowGetIncidentPlugin — ` |
| `plugins\servicenow\servicenow_update_incident.py` | ServiceNow 更新事件 — 更新 ServiceNow 事件记录 | `ServicenowUpdateIncidentPlugin — ` |

## `plugins/verify`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `plugins\verify\__init__.py` |  |  |
| `plugins\verify\ip_ops_verify.py` | IP 运维验证原子 — 用于验证 IP 选择器/资源选择/表格/级联功能 | `IpOpsVerifyPlugin — ` |

## `schema`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `schema\__init__.py` |  |  |
| `schema\form_schema.py` | 表单配置协议 — 定义插件入参的描述模型 | `ValidationType — `<br>`ValidationRule — `<br>`FormEvent — 跨字段联动事件` |

## `services`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `services\__init__.py` |  |  |
| `services\dr_service.py` | DR 拓扑服务 — Neo4j 查询 + AI Prompt + 拓扑描述 | `基于 Neo4j 查询 DR 组拓扑—Application 级()`<br>`将 Application 级拓扑数据生成为标准 pipeline 格式（支持 CALLS 依赖排序）()` |
| `services\vector_service.py` | 向量嵌入服务 — 将知识条目转为向量存入数据库
Vector Embedding Service — Convert knowledge entries to vectors for similarity search | `VectorService — 向量嵌入服务 — Vector Embedding Service` |

## `signals`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `signals\__init__.py` | Pipeline 信号处理器 — 追踪 BambooDjangoRuntime ERI 状态变更 |  |
| `signals\cmdb_events.py` | CMDB 变更事件 — CMDB 数据变更时触发 Pipeline 或 Webhook | `CmdbEventEmitter — CMDB 变更事件发射器` |
| `signals\handlers.py` | Signal handlers — on_post_set_state 接收器和根节点状态管理器 | `BambooDjangoRuntime 节点状态变更信号处理器()` |
| `signals\helpers.py` | Helper functions — 信号处理中使用的工具函数 |  |
| `signals\state.py` | State management — 节点状态持久化和状态树增量更新 |  |
| `signals\timeout.py` | 超时追踪 — 节点状态变更时更新 Redis 超时集合 |  |
| `signals\trace.py` | Trace management — 节点执行轨迹、日志记录、OpsLog 写入 |  |

## `tests`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `tests\__init__.py` |  |  |
| `tests\test_auto_retry.py` | 自动重试策略测试 — AutoRetryStrategyCreator + dispatch_auto_retry | `TestAutoRetryStrategyCreator — AutoRetryStrategyCreator.batch_create_strategy 测试`<br>`TestDispatchAutoRetry — dispatch_auto_retry 测试` |
| `tests\test_bamboo_builder.py` | bamboo_builder 测试 — build_bamboo_pipeline / _create_element / validate_bamboo_compatibility | `TestCreateElement — _create_element 元素工厂`<br>`TestBuildBambooPipeline — build_bamboo_pipeline 完整构建`<br>`TestValidateBambooCompatibility — validate_bamboo_compatibility 校验` |
| `tests\test_conflict_checker.py` | Conflict Checker 冲突检测 — 排他网关规则专项测试 | `TestExclusiveGatewayConflictRules — 排他网关冲突检测 — Rule 6: 出边条件表达式`<br>`TestParallelGatewayConflictRules — 并行网关冲突检测 — Rule 4: 缺少汇聚网关` |
| `tests\test_e2e_pipeline.py` | End-to-end pipeline execution tests — 串行/并行/排他/回环/loop全部场景 | `PipelineE2ETest — ` |
| `tests\test_execution_api.py` | API integration tests — FlowExecutionViewSet | `ExecAPITestBase — `<br>`ExecutionListTest — `<br>`ExecutionDetailTest — ` |
| `tests\test_flow_engine.py` | FlowEngine 测试 — 状态管理 + run/retry/skip | `TestFlowEngineStateManagement — FlowEngine 状态管理 — 不需要 bamboo 依赖`<br>`TestFlowEngineRun — FlowEngine.run() — pipline 构建+执行`<br>`TestFlowEngineWSNotification — WebSocket 通知（best-effort）` |
| `tests\test_gateway_execution.py` | 排他网关（Exclusive Gateway）完整执行流程测试 | `TestExclusiveGatewayPipelineBuild — 排他网关 pipeline 构建验证`<br>`TestExclusiveGatewayFlowEngineRun — FlowEngine.run() 与排他网关集成测试`<br>`TestExclusiveGatewayNodeCommands — 排他网关场景下的节点操作（retry/skip/force_fail）` |
| `tests\test_gateway_signal.py` | 排他网关信号处理测试 — 节点状态更新 + 状态树增量 | `TestExclusiveGatewaySignalStateUpdate — 排他网关场景下 _update_execution_node_status 和 _update_state_tree`<br>`TestExclusiveGatewaySignalHandler — on_post_set_state 信号处理器在排他网关场景下的行为`<br>`TestWsNodeStatusPush — _push_node_status_via_ws WebSocket 推送测试` |
| `tests\test_mako_resolver.py` | Mako 模板变量解析测试 | `TestMakoResolver — ` |
| `tests\test_manual_pause.py` | Manual Pause 原子测试 — ManualPausePlugin / PluginService 集成 | `TestManualPausePlugin — ManualPausePlugin 原子`<br>`TestPluginServiceManualPause — PluginService.execute 中 manual_pause 暂停触发` |
| `tests\test_node_sync.py` | 节点持久化同步测试 — 测试 extract_nodes_from_tree 数据转换逻辑 | `TestExtractNodes — extract_nodes_from_tree — 将 pipeline_tree JSON 转换为标准节点列表` |
| `tests\test_node_timeout_strategy.py` | 节点超时策略测试 — batch_create_timeout_configs / update_node_timeout / dispatch_timeout_nodes / 策略实现 | `TestBatchCreateTimeoutConfigs — batch_create_timeout_configs 测试`<br>`TestUpdateNodeTimeout — update_node_timeout 测试（Redis 交互）`<br>`TestDispatchTimeoutNodes — dispatch_timeout_nodes 测试` |
| `tests\test_optional_skip.py` | Optional 节点失败自动跳过测试 — _check_optional_skip / on_post_set_state 集成 | `TestCheckOptionalSkip — _check_optional_skip 辅助函数`<br>`TestOptionalSkipInSignal — on_post_set_state 信号中 optional skip 集成` |
| `tests\test_parallel_gateway.py` | 并行网关（Parallel Gateway）完整执行流程测试 | `TestParallelGatewayBuild — 并行网关 pipeline 构建验证`<br>`TestParallelGatewayFlowEngine — FlowEngine.run() 与并行网关集成测试` |
| `tests\test_safety_guard.py` | Pipeline 安全校验测试 — validate_pipeline 各种场景 | `TestValidatePipeline — validate_pipeline 核心逻辑` |
| `tests\test_states.py` | 状态机测试 — NodeState / PipelineState 转移矩阵 | `TestNodeState — 节点状态转移矩阵验证`<br>`TestPipelineState — Pipeline 级状态转移矩阵验证`<br>`TestMapBambooNodeState — bamboo-engine 状态 → NodeState 映射` |
| `tests\test_template_api.py` | API integration tests — FlowTemplate edit lock | `TemplateLockTest — TemplateLock acquire/release actions (do not use ProjectFilteredViewset)` |
| `tests\test_template_lock.py` | TemplateLock tests — acquire/release/heartbeat/expiry/update guard | `TemplateLockAcquireTest — acquire_lock happy path and conflict detection`<br>`TemplateLockExpiryTest — is_expired and heartbeat timeout`<br>`TemplateLockReleaseTest — release_lock idempotency` |
| `tests\test_trace.py` | 执行轨迹双树结构 — 测试用例 | `NodeExecutionTraceModelTest — Test NodeExecutionTrace model constraints and defaults`<br>`NodeTraceLoggerTest — Test NodeTraceLogger file I/O`<br>`UpdateStateTreeTest — Test _update_state_tree helper` |
| `tests\test_variable_registry.py` | 变量注册表测试 — RegisterVariableMeta 自动注册 + VariableLibrary 检索 | `TestVariableRegistry — RegisterVariableMeta 自动注册`<br>`TestVariableLibrary — VariableLibrary 检索和解析`<br>`TestLazyVariable — LazyVariable get_value() 自定义转换` |
| `tests\test_variable_resolver.py` | 变量解析引擎测试 — resolve_variables / build_execution_context / get_variable_reference_details | `TestResolveVariables — resolve_variables 核心替换逻辑`<br>`TestSplitValue — split_value 字符串分割`<br>`TestDeepGet — _deep_get 嵌套路径查找` |

## `views`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views\__init__.py` |  |  |
| `views\aliyun_views.py` | 阿里云 ECS 资源查询 API — 供表单 async_select 动态加载数据 | `()`<br>`()` |
| `views\audit_views.py` | 操作审计视图 — 只读查询接口 | `OperationRecordViewSet — 操作审计记录 — 只读` |
| `views\base.py` | ViewSet base class — project isolation + multi-tenant permission support | `ProjectFilteredViewSet — Project-scoped ViewSet with multi-tenant permission enforcement.`<br>`ProjectReadOnlyViewSet — Read-only variant — disables all write operations.` |
| `views\execution_views.py` | FlowExecution ViewSet — 执行 CRUD | `FlowExecutionViewSet — ` |
| `views\knowledge_views.py` |  | `OpsKnowledgeViewSet — ` |
| `views\log_views.py` |  | `OpsLogViewSet — OpsLog 通过 execution.project 间接隔离，不直接设 project FK` |
| `views\node_views.py` | 节点视图 — 提供 TemplateNode / ExecutionNode 的只读查询接口 | `TemplateNodeViewSet — 模板节点 — 只读，支持按 template / node_type / atom_type 过滤`<br>`ExecutionNodeViewSet — 执行节点 — 只读，支持按 execution / node_type / status 过滤` |
| `views\plugin_views.py` | 标准插件 API — 对接前端 RenderForm 的插件元数据和表单配置 | `PluginViewSet — 标准插件只读接口 — 提供插件列表、详情、分组树` |
| `views\project_views.py` | Project ViewSet — 项目 CRUD + 成员管理 + 我的项目 | `OpsProjectViewSet — 项目管理 CRUD + 成员管理` |
| `views\schedule_views.py` |  | `SchedulePlanViewSet — ` |
| `views\scheme_views.py` | ExecutionScheme ViewSet — 执行方案 CRUD（嵌套于模板下） | `ExecutionSchemeViewSet — 执行方案 CRUD — 预定义节点排除集 + 变量覆盖` |
| `views\template_category_views.py` | 模板分类 API | `TemplateCategoryViewSet — ` |
| `views\template_views.py` | FlowTemplate ViewSet — 流程模板 CRUD | `FlowTemplateViewSet — ` |

## `views/dashboard_views`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views\dashboard_views\__init__.py` | Dashboard API endpoints — 为 urls.py 向后兼容重新导出 |  |
| `views\dashboard_views\analytics.py` | Dashboard — 分析/分布端点（top_templates, user_activity, 分布, 排行等） | `Top N templates ranked by execution count (with success rate and average duration)()`<br>`User execution activity statistics()` |
| `views\dashboard_views\stats.py` | Dashboard — 聚合统计 + 调度统计端点 | `Return aggregate statistics for the opsflow dashboard (including scheduler).()`<br>`Return detailed scheduler statistics for the dashboard.()` |
| `views\dashboard_views\trends.py` | Dashboard — 执行趋势 + 成功率趋势端点 | `Return execution trend data per day for the last N days (default 30).()`<br>`每日成功率趋势 — 按日聚合执行成功/失败数量及成功率()` |

## `views/mixins`
| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views\mixins\__init__.py` |  |  |
| `views\mixins\execution_approval.py` | Execution Approval — 审批/拒绝端点 Mixin | `ExecutionApprovalMixin — 审批端点混入（approve/reject/pending_approval）` |
| `views\mixins\execution_lifecycle.py` | Execution Lifecycle — 启动/暂停/恢复/取消端点 Mixin | `ExecutionLifecycleMixin — 执行生命周期端点混入（start/pause/resume/cancel）` |
| `views\mixins\execution_node_command.py` | Execution Node Commands — 节点操作/批量/子流程重试端点 Mixin | `ExecutionNodeCommandMixin — 节点操作端点混入（retry/skip/force_fail/batch/subprocess）` |
| `views\mixins\execution_trace.py` | Execution Trace — 节点轨迹查询端点 Mixin | `ExecutionTraceMixin — 节点轨迹查询端点混入（traces/trace_log）` |
| `views\mixins\template_ai.py` | Template AI — AI 生成/分析/布局端点 Mixin | `TemplateAIMixin — AI 生成、分析、布局端点混入` |
| `views\mixins\template_collect.py` | Template Collect — 收藏/取消收藏端点 Mixin | `TemplateCollectMixin — 收藏管理端点混入` |
| `views\mixins\template_dr.py` | Template DR — AI 生成 DR 切换 Pipeline 端点 | `预览 DR 组拓扑 — 返回结构化的主站/备站进程 + CALLS 关系()`<br>`AI 生成 DR 切换 Pipeline()` |
| `views\mixins\template_export.py` | Template Export/Import — 导出/导入/分类端点 Mixin | `TemplateExportImportMixin — 导出、导入、分类端点混入` |
| `views\mixins\template_subprocess.py` | Template Subprocess — 子流程版本追踪端点 Mixin | `TemplateSubprocessMixin — 子流程版本追踪端点混入` |
| `views\mixins\template_variable.py` | Template Variable — 全局变量/变量浏览器/变量提升端点 Mixin | `TemplateVariableMixin — 全局变量系统端点混入` |
| `views\mixins\template_version.py` | Template Version — 版本管理/发布/回滚端点 Mixin | `TemplateVersionMixin — 版本管理、发布、回滚端点混入` |
| `views\mixins\template_webhook.py` | Template Webhook — 模板 Webhook 回调配置端点 Mixin | `TemplateWebhookMixin — 模板 Webhook CRUD + 日志查询` |
