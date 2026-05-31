# 代码结构

## 后端目录结构

```
backend/opsflow/
├── __init__.py
├── apps.py                          # AppConfig → 启动时注册原子 + Service
├── models.py                        # 4 个数据模型
├── serializers.py                   # DRF 序列化器
├── urls.py                          # 6 条路由注册（含 dashboard）
├── tasks.py                         # Celery 任务
├── consumers.py                     # WebSocket 消费者 (含 tower_job_update)
│
├── core/
│   ├── __init__.py
│   ├── atom_registry.py             # 原子注册中心（37 个原子）
│   ├── atom_service.py              # bamboo-engine Service 实现
│   ├── ansible_trigger.py           # Ansible Tower HTTP 触发器
│   ├── tower_service.py             # Tower REST API 封装（launch/poll/extract）
│   ├── bamboo_builder.py            # Pipeline Tree 构建器
│   ├── flow_engine.py               # 流程执行引擎（含增强条件求值）
│   ├── llm_service.py              # DeepSeek AI 服务（不含布局）
│   ├── safety_guard.py             # Pipeline 安全校验器
│   │
│   ├── layout/                      # ★ Sugiyama 分层布局引擎
│   │   ├── __init__.py              # 导出 compute_layout()
│   │   ├── constants.py             # PipelineKey / NodeType / 尺寸常量
│   │   ├── utils.py                 # format_to_list / io 操作
│   │   ├── acyclic.py               # 环移除 + DFS 环检测
│   │   ├── normalize.py             # 节点字典构建
│   │   ├── rank/                    # 层级分配（最长路径 + 可行树）
│   │   │   ├── __init__.py
│   │   │   ├── utils.py
│   │   │   ├── longest_path.py
│   │   │   ├── feasible_tree.py
│   │   │   └── tight_tree.py
│   │   ├── order/                   # 交叉最小化（加权中位数）
│   │   │   ├── __init__.py
│   │   │   ├── order.py
│   │   │   └── builder.py
│   │   ├── dummy.py                 # 长边虚拟节点替换
│   │   ├── position.py              # 坐标分配 + 箭头端点
│   │   ├── drawing.py               # 主编排器（5 阶段）
│   │   ├── layout_adapter.py        # OPSflow ↔ 引擎格式桥接
│   │   └── tests.py                 # 单元测试
│   │
│   └── executors/                   # ★ 多平台原子执行器
│       ├── __init__.py
│       ├── base.py                  # BaseExecutor + ExecuteResult 契约
│       ├── factory.py               # AtomExecutorFactory（惰性加载 + 缓存）
│       ├── ansible_executor.py      # AnsibleExecutor → TowerService
│       ├── esxi_executor.py         # EsxiExecutor（伪代码，需 pyVmomi）
│       ├── netapp_executor.py       # NetAppExecutor（伪代码，需 ONTAP REST）
│       ├── servicenow_executor.py   # ServiceNowExecutor（骨架，需 pysnow）
│       ├── redfish_executor.py      # RedfishExecutor（骨架，需 redfish 库）
│       └── http_executor.py         # HttpExecutor（通用 REST，具体实现）
│       └── test_executor.py         # TestExecutor（流程引擎测试用）
│
├── views/
│   ├── __init__.py
│   ├── template_views.py           # 模板 CRUD + AI 端点
│   ├── execution_views.py          # 执行 CRUD + 控制端点
│   ├── log_views.py                # 日志只读视图
│   ├── knowledge_views.py          # 知识库 CRUD + 搜索
│   └── dashboard_views.py          # Dashboard 统计/趋势 API
│
├── management/commands/
│   └── add_opsflow_menu.py         # RBAC 菜单注册命令
│
├── migrations/
│   └── 0001_initial.py
│
├── TODO.md                          # 待办清单
└── doc/                             # 本文档目录
```

## 前端目录结构

```
web/src/views/apps/opsflow/
├── index.vue                        # 主页面（布局 + AI Chat + Dialog）
├── stores/opsflowStore.ts           # Pinia 状态管理
│
├── components/
│   ├── DesignCanvas.vue             # 设计画布（X6 Graph）
│   ├── MonitorCanvas.vue            # 监控画布（只读 + WebSocket）
│   ├── PropertyPanel.vue            # 节点属性编辑面板
│   └── DiffModal.vue                # AI 原稿对比弹窗
│
└── composables/
    ├── useDesignCanvas.ts           # 画布逻辑（节点/连线/布局/X6 插件）
    └── useMonitor.ts                # WebSocket 监控逻辑

web/src/views/apps/opsflow-log/
└── index.vue                        # 审计日志页面（白卡片 + 风险状态点 + 图标按钮）

web/src/views/apps/opsflow-knowledge/
└── index.vue                        # 知识库页面（卡片布局 + 编辑/删除图标按钮）

web/src/views/apps/opsflow-template/
└── index.vue                        # 模板管理页面（表格/卡片切换 + 管道可视化 + 详情弹窗）

web/src/views/apps/opsflow-execution/
├── index.vue                        # 执行记录列表（筛选状态 + 时间线）
└── components/
    ├── ExecutionList.vue            # 执行列表（表格 + 标签过滤）
    └── ExecutionDetail.vue          # 执行详情（嵌入 MonitorCanvas）

web/src/views/apps/opsflow-dashboard/
└── index.vue                        # Dashboard（4 ECharts + 7 统计卡片 + 用户活动表）

web/src/api/opsflow/
├── templates.ts                     # 模板 API
├── executions.ts                    # 执行 API
├── logs.ts                          # 日志 API
├── knowledge.ts                     # 知识库 API
└── dashboard.ts                     # Dashboard 统计/趋势 API
```

## 模型关系

```
┌──────────────┐       ┌─────────────────┐
│ FlowTemplate │       │  FlowExecution  │
│──────────────│       │─────────────────│
│ id           │◄──────│ template (FK)   │
│ name         │       │ status          │
│ pipeline_tree│       │ node_status     │
│ target_hosts │       │ context         │
│ global_vars  │       │ current_node    │
│ is_draft     │       │ started_at      │
│ ai_original_tree│      │ ended_at        │
│ created_by   │       │ created_by      │
└──────────────┘       └───────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │     OpsLog       │
                      │─────────────────│
                      │ execution (FK)  │
                      │ step / command  │
                      │ stdout / stderr │
                      │ returncode      │
                      │ risk_level      │
                      │ approved_by     │
                      └─────────────────┘

┌──────────────────┐
│  OpsKnowledge    │
│──────────────────│
│ title / content  │
│ tags / source    │
│ embedding        │
└──────────────────┘
```

## API 端点汇总

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/opsflow/templates/` | GET/POST | 模板列表/创建 |
| `/api/opsflow/templates/{id}/` | GET/PUT/PATCH/DELETE | 模板详情/更新/删除 |
| `/api/opsflow/templates/create_from_ai/` | POST | AI 自然语言生成 |
| `/api/opsflow/templates/{id}/confirm_draft/` | POST | 确认草稿正式入库 |
| `/api/opsflow/templates/ai_layout/` | POST | 布局优化（Sugiyama 引擎） |
| `/api/opsflow/templates/{id}/diff/` | GET | AI 原稿 vs 当前 |
| `/api/opsflow/templates/analyze/` | POST | AI 流程分析 |
| `/api/opsflow/templates/refine/` | POST | 多轮对话修改 |
| `/api/opsflow/executions/` | GET/POST | 执行记录列表/创建 |
| `/api/opsflow/executions/{id}/` | GET/PUT/PATCH/DELETE | 执行详情/更新 |
| `/api/opsflow/executions/{id}/start/` | POST | 启动执行 |
| `/api/opsflow/executions/{id}/pause/` | POST | 暂停执行 |
| `/api/opsflow/executions/{id}/resume/` | POST | 恢复执行 |
| `/api/opsflow/executions/{id}/retry_node/` | POST | 重试节点 |
| `/api/opsflow/executions/{id}/skip_node/` | POST | 跳过节点 |
| `/api/opsflow/logs/` | GET | 审计日志列表（只读） |
| `/api/opsflow/knowledge/` | GET/POST | 知识库列表/创建 |
| `/api/opsflow/knowledge/search/` | POST | 知识库文本搜索 |
| `/api/opsflow/dashboard/stats/` | GET | Dashboard 统计数据（14 项聚合指标） |
| `/api/opsflow/dashboard/trend/` | GET | Dashboard 执行趋势（按日，默认 30 天） |
| `ws://host/ws/opsflow/execution/{id}/` | WebSocket | 实时状态 + Tower 进度推送 |

## 核心模块依赖

```
apps.py
  ├─ scan_atoms()          → atom_registry.py
  └─ register_atom_services()  → atom_service.py

template_views.py
  ├─ llm_service.py       (generate_pipeline / refine_pipeline / analyze)
  ├─ safety_guard.py      (validate_pipeline)
  ├─ layout               (compute_layout — Sugiyama 引擎)
  └─ bamboo_builder.py    (validate_bamboo_compatibility)

flow_engine.py
  ├─ bamboo_builder.py    (build_bamboo_pipeline)
  ├─ atom_service.py      (get_service → AnsibleAtomService)
  ├─ tasks.py             (notify_node_status)
  ├─ channels             (WebSocket group_send)
  └─ django_redis         (Redis converge counter)

atom_service.py
  ├─ atom_registry.py     (get_atom_meta)
  └─ executors/factory.py (AtomExecutorFactory.execute_atom)
       └─ executors/ansible_executor.py
            └─ ansible_trigger.py
                 └─ tower_service.py (TowerService)

executors/factory.py
  ├─ executors/base.py      (BaseExecutor)
  ├─ executors/ansible_executor.py
  ├─ executors/esxi_executor.py
  ├─ executors/netapp_executor.py
  ├─ executors/servicenow_executor.py
  ├─ executors/redfish_executor.py
  └─ executors/http_executor.py
  └─ executors/test_executor.py
```
