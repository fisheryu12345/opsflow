# 功能状态

## ✅ 已完成功能

### 后端核心

| 功能 | 模块 | 说明 |
|------|------|------|
| 数据模型 | `models.py` | FlowTemplate / FlowExecution / OpsLog / OpsKnowledge |
| API 路由 | `urls.py` | 4 组 REST 端点 + WebSocket |
| Pipeline 构建 | `bamboo_builder.py` | 自定义格式 → bamboo-engine 标准 Pipeline Tree |
| 串行执行 | `flow_engine.py` | 活动节点按顺序执行 |
| ExclusiveGateway | `flow_engine.py` | 根据条件表达式选择一条分支 |
| ParallelGateway | `flow_engine.py` | Celery group 并行执行所有分支 |
| ConditionalParallelGateway | `flow_engine.py` | 按条件筛选后并行 |
| ConvergeGateway | `flow_engine.py` | Redis 原子计数，最后分支继续 |
| 暂停/继续 | `flow_engine.py` | 执行中检查 pause 状态 |
| 重试/跳过 | `flow_engine.py` | 失败节点重试或跳过 |
| 条件表达式增强 | `flow_engine.py` | ${node_id.artifacts.key >= N} 全语法 |
| Service 接口 | `atom_service.py` | 实现 bamboo-engine Service 接口 |
| 原子注册 | `atom_registry.py` | meta.json 自动扫描注册（31 个原子） |
| Executor Factory | `executors/factory.py` | 7 平台执行器统一调度（含 test） |
| Tower 集成 | `tower_service.py` | launch/poll/artifacts/events/cancel |
| 安全校验 | `safety_guard.py` | 白名单 / 高危回滚 / 备份前置 / Shell 拦截 / 跨平台检查 |
| AI 幻觉防御 | `template_views.py` + `llm_service.py` | _errors 检测 / Shell 过滤 / 跨平台误用拦截 |
| AI 生成 | `llm_service.py` | DeepSeek NL → Pipeline Tree |
| AI 多轮对话 | `llm_service.py` | 增量修改已有流程 |
| AI 分析 | `llm_service.py` | 步骤 / 风险 / 建议分析 |
| AI 布局 | `llm_service.py` | 自动排列画布节点 |
| RAG 检索 | `llm_service.py` | OpsKnowledge 相似案例搜索 |
| Ansible 触发器 | `ansible_trigger.py` | TowerService 封装 + Mock 降级 |
| Celery 任务 | `tasks.py` | execute_pipeline_task / notify_node_status |
| WebSocket | `consumers.py` | 节点状态 + tower_job_update 推送 |
| 菜单注册 | `add_opsflow_menu.py` | RBAC 菜单写入命令 |

### 前端

| 功能 | 组件 | 说明 |
|------|------|------|
| 设计画布 | `DesignCanvas.vue` | X6 Graph 拖拽式编排 |
| 组件面板 | `useDesignCanvas.ts` | Stencil 分组拖拽 |
| 节点属性 | `PropertyPanel.vue` | 编辑标签/参数/超时/重试 |
| 小地图 | `useDesignCanvas.ts` | Minimap 导航 |
| Undo/Redo | `useDesignCanvas.ts` | History 插件 + 快捷键 |
| 模板选择 | `index.vue` | 顶部居中下拉选择 |
| AI Chat | `index.vue` | 浮窗多轮对话 |
| Diff 对比 | `DiffModal.vue` | AI 原稿 vs 当前修改 |
| 实时监控 | `MonitorCanvas.vue` | WebSocket 节点实时着色 |
| 状态管理 | `opsflowStore.ts` | Pinia 设计/监控模式 |

## ❌ 待实现功能

### 高优先级

| 功能 | 说明 | 涉及文件 |
|------|------|----------|
| **执行入口 UI** | 画布工具栏添加"运行"按钮，调用 CreateExecution + StartExecution | `DesignCanvas.vue`, `index.vue`, `executions.ts` |
| **执行记录页面** | 执行历史列表（筛选状态）+ 详情页（嵌入 MonitorCanvas） | 新建页面 + `executions.ts` |

### 中优先级

| 功能 | 说明 | 涉及文件 |
|------|------|----------|
| **审计日志页面** | OpsLog 浏览（按 execution 查看每一步输出） | 新建页面 + `logs.ts` |
| **知识库页面** | OpsKnowledge CRUD 前端 | 新建页面 + `knowledge.ts` |
| **设计/监控切换** | 设计画布 ↔ 监控视图的统一切换入口 | `index.vue`, `opsflowStore.ts` |

### 低优先级

| 功能 | 说明 | 涉及文件 |
|------|------|----------|
| **模板管理页面** | 模板列表浏览/搜索/编辑/删除/版本对比 | 新建页面 + `templates.ts` |

### 平台执行器完善

| 功能 | 说明 | 当前状态 |
|------|------|----------|
| **ESXi Executor** | pyVmomi 真实调用 | 伪代码 |
| **NetApp Executor** | ONTAP REST API | 伪代码 |
| **ServiceNow Executor** | pysnow 真实调用 | 骨架 |
| **Redfish Executor** | BMC Redfish API | 骨架 |
| **Test Executor** | 流程引擎功能验证 | ✅ 已完成 |

## Pipeline 格式定义

### 前端画布格式 (nodes + edges)

```json
{
  "nodes": [
    {
      "id": "node_1",
      "label": "Check Disk",
      "node_type": "",             // 留空或 "atom" = 原子操作
      "atom_type": "disk_check",   // 原子类型（对应 ATOM_REGISTRY）
      "params": {"threshold": 80},
      "max_retries": 1,
      "timeout_seconds": 30,
      "risk_level": "low"
    },
    {
      "id": "node_2",
      "label": "Condition?",
      "node_type": "exclusive_gateway"   // 网关类型
    }
  ],
  "edges": [
    {"from": "node_1", "to": "node_2", "label": "success"},
    {"from": "node_1", "to": "node_3", "label": "failure"}
  ]
}
```

### 节点类型

| node_type | 含义 | 出度 | 入度 |
|-----------|------|------|------|
| (空) / "atom" | 原子操作 | 1-2 | ≥1 |
| "exclusive_gateway" | 排他网关 | ≥1 | ≥1 |
| "parallel_gateway" | 并行网关 | ≥1 | ≥1 |
| "conditional_parallel_gateway" | 条件并行网关 | ≥1 | ≥1 |
| "converge_gateway" | 汇聚网关 | 1 | ≥2 |
| "start_event" | 流程起点 | 1 | 0 |
| "end_event" | 流程终点 | 0 | ≥1 |

### 出边标签规则

- 原子节点出度=2 时，标签必须为 `success` 和 `failure`
- 排他网关多出边时，标签区分条件分支
- 并行网关出边标签不参与条件判断（全执行）

## 执行状态机

```
                        ┌──────────┐
                        │  PENDING │
                        └────┬─────┘
                             │ start()
                             ▼
               ┌─────────────────────┐
         ┌─────│      RUNNING        │
         │     └──────┬──────────┬───┘
         │            │          │
         │     完成    │          │ 失败
         ▼            ▼          ▼
    ┌────────┐  ┌───────────┐  ┌────────┐
    │PAUSED  │  │COMPLETED  │  │ FAILED │
    └───┬────┘  └───────────┘  └───┬────┘
        │ resume()                 │ retry()
        ▼                          ▼
    ┌──────────┐              ┌──────────┐
    │ RUNNING  │              │ RUNNING  │
    └──────────┘              └──────────┘
```
