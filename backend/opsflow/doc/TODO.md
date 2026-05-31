# OpsFlow TODO

## ✅ 已完成

- [x] 数据模型 (FlowTemplate / FlowExecution / OpsLog / OpsKnowledge)
- [x] API 路由 (`/api/opsflow/*`) + WebSocket (`ws/opsflow/execution/{id}/`)
- [x] Pipeline Builder (`build_bamboo_pipeline` → bamboo-engine 标准格式)
- [x] FlowEngine (BambooDjangoRuntime + api.run_pipeline() 驱动，替代自定义解释器)
- [x] post_set_state 信号处理器 (signals.py 异步追踪节点状态 → FlowExecution + OpsLog)
- [x] signals.py 改用 framework API (get_execution_data_outputs 替代直接 ERI 查询)
- [x] 注册 contrib apps (rollback / node_timeout / engine_admin)
- [x] 启用 pipeline_event 信号 (ENABLE_PIPELINE_EVENT_SIGNALS)
- [x] 配置回滚设置 (PIPELINE_ENABLE_ROLLBACK / ROLLBACK_QUEUE)
- [x] 节点超时配置注入 (bamboo_builder.py → apply_node_timout_configs)
- [x] Service inputs_format/outputs_format 定义 (atom_service.py)
- [x] Celery 任务 (`execute_pipeline_task` / `notify_node_status`)
- [x] AI 服务 (生成 / 分析 / 多轮对话)
- [x] DesignCanvas (X6 Graph + Stencil + Minimap + PropertyPanel + DiffModal)
- [x] MonitorCanvas (实时执行监控 + WebSocket 状态同步)
- [x] AI Chat 浮窗 (多轮对话 + Layout 优化)
- [x] 后端 Serializers / Views (Template / Execution / Log / Knowledge CRUD)
- [x] 文档 (doc/ 目录架构设计文档)
- [x] Ansible Tower 集成: TowerService (launch/poll/artifacts/events/cancel) + 自适应轮询 + WebSocket 实时推送
- [x] 条件表达式增强: `${node_id.artifacts.key >= N}` 全语法支持
- [x] AI 幻觉防御: shell 原子过滤 + 跨平台误用检测 + _errors 拦截
- [x] 测试执行器: TestExecutor + test_print_time 原子（流程引擎功能验证）
- [x] 多平台原子层: Executor Factory (Ansible/ESXi/NetApp/ServiceNow/Redfish/HTTP/Test)
- [x] **菜单注册** — 前端 RBAC 菜单已配好，入口可见
- [x] **执行记录页面** — 已实现（ExecutionList.vue + ExecutionDetail.vue）
- [x] **Celery worker 启动脚本** — 注意事项.md 已记录启动命令（含 gevent 池 + Redis channel layer）
- [x] **WebSocket Channel Layer 修复** — InMemoryChannelLayer → RedisChannelLayer，async_to_sync → 手动事件循环，解决跨进程 WS 消息推送问题（详见注意事项.md 第 6 节）
- [x] **SchedulePlan 模型/API** — 一次性/CRON 定时调度计划模型 + CRUD 视图 + pause/resume/trigger/history 端点
- [x] **APScheduler 调度器** — BackgroundScheduler + DjangoJobStore + 独立进程启动命令
- [x] **部署文档** — 06-deployment-notes.md，记录 OpsFlow 所有跨目录修改
- [x] **模板列表按钮重构** — 工具栏改为图标按钮（Edit/Modify/Publish/Schedule/Delete）+goEditTemplate 跳转设计器
- [x] **DesignCanvas 模板选择器重构** — 选择器从独立栏移入画布工具栏 + loadPipeline 鲁棒性增强
- [x] **Sugiyama 布局引擎** — 适配 bk_sops drawing_new，18 文件，纯 Python 确定性布局，替代 LLM 布局方案
- [x] **DesignCanvas 缩放控件** — 工具栏添加 Zoom In/Out/Fit 按钮 + 缩放比例显示
- [x] **编辑器 Executions 按钮删除** — 编辑与执行职责分离，工具栏移除运行记录入口
- [x] **MonitorCanvas Cancel 按钮去重** — 进度条区域 Cancel 按钮已移除（执行详情页保留）

## ❌ 待处理

### 高优先级

- [ ] **get_pipeline_states 状态验证** — flow_engine.py 中定期调用 api.get_pipeline_states() 验证执行状态一致性
- [ ] **X6 节点 UI 定型** — 统一节点视觉风格（尺寸、配色、图标、阴影、选中态），参考 bk_sops 节点设计规范，确保所有节点类型视觉层级清晰
- [x] **流程图布局优化** — 适配 bk_sops Sugiyama 布局引擎（core/layout/ 18 文件），支持分层布线、交叉最小化、自动起止节点合成
- [ ] **X6 连线重叠修复** — Manhattan 路由 padding 配置 + 增大垂直间距（shift_y=144, NODE_GAP=120），需持续评估复杂图场景

### 中优先级

- [x] **审计日志页面** — OpsLog 浏览页面（白卡片 + 风险状态点）
- [x] **知识库页面** — OpsKnowledge CRUD 前端页面（卡片布局）
- ~~[ ] **设计/监控模式切换** — 不合理需求，设计画布负责编辑模板，监控嵌入执行详情页，职责分离~~

### 低优先级

- [x] **模板管理页面** — 模板列表（表格/卡片视图切换 + 管道可视化 + 查看弹窗）

### 新增功能

- [x] **Dashboard 统计仪表盘** — 4 ECharts（趋势/状态分布/Top 模板/节点类型）+ 7 统计卡片 + 用户活动表

- [x] **执行轨迹双树结构** — NodeExecutionTrace 模型 + state_tree 快照 + 节点独立日志文件 + NodeCommandDispatcher 节点操作调度层
  - [x] NodeExecutionTrace 模型 (unique_together: execution/node_id/retry_count)
  - [x] FlowExecution.state_tree 字段 (增量更新，含时间/耗时/错误)
  - [x] NodeTraceLogger (JSON Lines 日志文件，按事件类型分类)
  - [x] signals.py 扩展 (_update_state_tree / _record_node_trace / _write_node_trace_log)
  - [x] NodeCommandDispatcher (retry/skip/trace 标准化操作接口)
  - [x] API 端点 (`/traces/` + `/trace_log/` + retry/skip 升级)
  - [x] 日志清理 management command (`clean_node_trace_logs`)
  - [x] 测试用例 (18 个，全部通过)
  - [x] 文档 (spec + plan)

### 待添加

- [ ] **bk-sops 配置驱动表单架构借鉴** — 参考 bk-sops 原子表单的"配置驱动"思想，构建 OpsFlow 原子参数配置表单：

  **核心思路**: 后端定义原子元信息 + 前端 JSON Schema 配置 = 自动渲染表单

  **借鉴对照表**:

  | bk-sops 实现 | OpsFlow 升级方案 |
  |---|---|
  | jQuery Tag 系统 | Vue3 + Element Plus / Ant Design Vue Form |
  | JS 配置文件 (`$.atoms[code]`) | JSON Schema (如 JSON Schema Form / Vue JSON Schema Form) |
  | `$.atoms[code]` 全局注册 | 后端 API 动态返回表单 Schema (`GET /api/opsflow/atom-schema/{code}`) |
  | `tag_code` 字符串绑定 | 类型安全的字段 key (TypeScript enum + 运行时校验) |
  | 手写 `events` 联动 | 声明式联动规则 (dependencies + react-when) 或可视化规则引擎 |

  **数据结构契约** (参考 tag_code 设计):
  ```python
  # 后端原子定义
  class AtomMeta:
      code: str          # 唯一标识
      name: str          # 显示名称
      form_schema: dict  # JSON Schema 描述参数结构
      # 数据绑定: schema 中的 field_key 对应前端表单值的 key
      # 执行时通过 field_key 取值: inputs["field_key"]

  # 前端渲染 (Vue3 + JSON Schema Form)
  # <VueForm :schema="atomMeta.form_schema" v-model="formValues" />
  # formValues = { "host_ip": "...", "var_name": "..." }  # 按 field_key 组织
  ```

  **需要解决的问题**:
  - 选择 JSON Schema 表单库 (Vue JSON Schema Form / Formily / Element Plus 动态表单?)
  - datatable 高级表格组件支持（行内编辑、动态增减、列类型可配）
  - 字段联动声明式 DSL 设计
  - 与现有 X6 画布的 PropertyPanel 集成方式

## OpsFlow Doc Updater Skill

已创建 `.claude/skills/opsflow-doc-updater/SKILL.md`，通过 `/opsflow-doc-updater` 命令触发，自动扫描代码并同步 doc/ 文档。

---

## 统一原子层封装多平台接口调度

### 背景

OpsFlow 最初只支持 Ansible 作为原子执行引擎，所有 atom 的 `executor_type` 默认为 `ansible`。随着接入平台增多（ESXi、NetApp、ServiceNow、Redfish、HTTP API），需要将原子层抽象为统一接口，使 bamboo-engine 的 Service 层无需关心底层实现。

### 设计思路

```
meta.json  (executor_type 字段)  →  AtomExecutorFactory  →  BaseExecutor子类
                                                                ├── AnsibleExecutor    (具体实现)
                                                                ├── EsxiExecutor       (伪代码，需完善)
                                                                ├── NetAppExecutor     (伪代码，需完善)
                                                                ├── ServiceNowExecutor (骨架，需完善)
                                                                ├── RedfishExecutor    (骨架，需完善)
                                                                └── HttpExecutor       (具体实现，泛用)
```

核心原则:
- `meta.json` 新增 `executor_type` 字段（默认 `"ansible"`），factory 据此路由
- `BaseExecutor` 定义 `execute(inputs) -> ExecuteResult` / `rollback(inputs, context) -> ExecuteResult` 契约
- `AtomExecutorFactory` 惰性加载 + 缓存实例，被 `atom_service.py` 调用
- 向后兼容：已有 13 个 Ansible atom 无需修改 meta.json（默认走 ansible 执行器）

### ☑ 平台执行器状态

| 执行器 | 状态 | 依赖 | 优先级 |
|--------|------|------|--------|
| AnsibleExecutor | 具体实现完成 | ansible_trigger.execute_atom() | - |
| HttpExecutor | 具体实现完成 | requests 库 | - |
| EsxiExecutor | 伪代码 | pyVmomi / REST API | 高 |
| NetAppExecutor | 伪代码 | ONTAP REST API | 高 |
| ServiceNowExecutor | 骨架 | pysnow / REST API | 中 |
| RedfishExecutor | 骨架 | redfish 库 | 中 |
| TestExecutor | 具体实现完成 | 无（纯 Python 打印时间） | - |

### 待办事项

#### 高优先级（平台完善）

- [ ] **EsxiExecutor 完善** — 替换伪代码为真实 pyVmomi 调用:
  - 依赖: `pip install pyvmomi`
  - 凭证管理: 从 vault/环境变量读取 ESXi host + username + password
  - 连接池: 复用 `SmartConnectNoSSL` 实例，按 host 缓存
  - 待实现: `create_vm` (VM规格参数化), `destroy_vm` (确保先关机), `power_on/off` (确保幂等), `get_state` (查询 guest 状态)

- [ ] **NetAppExecutor 完善** — 替换伪代码为 ONTAP REST API 调用:
  - 依赖: `requests` 库（ONTAP 9.8+ 推荐 REST API，不依赖 netapp-lib）
  - 认证: HTTP Basic Auth over HTTPS（管理账号 + 密码）
  - API 基础路径: `https://{cluster_ip}/api/`
  - 待实现: 卷创建/删除/修改/查询、快照创建、导出策略管理
  - 特殊处理: 卷删除前需确保无 Snapshot 副本锁定；扩容仅支持增加不支持缩减

- [ ] **ServiceNowExecutor 完善** — 接入真实 ServiceNow 实例:
  - 依赖: `pip install pysnow` 或直接 requests
  - 认证: OAuth2 client_credentials 或 Basic Auth
  - 实例 URL: 需从 vault 读取
  - 待实现: Incident CRUD、Change Request 标准流程、CMDB CI 查询

- [ ] **RedfishExecutor 完善** — 接入 BMC Redfish API:
  - 依赖: `pip install redfish` 或直接 requests
  - 认证: Basic Auth（BMC 账号）
  - 基础路径: `https://{bmc_ip}/redfish/v1/`
  - 待实现: 系统信息查询、电源控制、启动设备设置、存储/固件清单

#### 中优先级（基础设施）

- [ ] **凭证管理** — 统一 secrets 接入层:
  - 对接 HashiCorp Vault 或 Django Model 加密存储（`django-fernet-fields`）
  - 平台凭证按 `(executor_type, host/cluster)` 索引
  - 执行器 `execute()` 时自动注入凭证，不暴露给流程画布

- [ ] **连接池与重试** — 为各平台添加连接复用:
  - ESXi: 按 host 缓存 `SmartConnectNoSSL` 连接，自动重连
  - NetApp/Redfish: `requests.Session` + `urllib3.Retry`
  - ServiceNow: `pysnow.Client` 实例复用

- [ ] **异步执行** — 长耗时操作（VM 创建、卷创建）异步化:
  - 返回 `202 Accepted` + task reference
  - 轮询或 Webhook 等待完成
  - 当前 Ansible 原子通过 Celery 已异步，其他平台需跟进

#### 低优先级（增强）

- [ ] **幂等性保障** — 每个 executor 需标注是否幂等:
  - `BaseExecutor` 新增 `is_idempotent` 属性
  - 非幂等操作（vm destroy、volume delete）执行前二次确认
  - 流程引擎中 risk_level=high 且非幂等的操作需要人工审批节点

- [ ] **批量操作** — 支持多目标并行:
  - ESXi: 批量创建 VM、批量电源操作
  - Redfish: 批量 BMC 固件升级
  - 复用 ParallelGateway + Celery group 架构

- [ ] **审计增强** — 每个 executor 执行记录结构化:
  - 记录请求/响应摘要到 OpsLog（避免存储敏感字段）
  - 提供 `dry_run` 模式预览执行效果

- [ ] **测试覆盖**:
  - 单元测试: `BaseExecutor.validate_inputs()` 校验逻辑
  - Mock 测试: 各 executor 的 `execute()` 返回值模拟
  - 集成测试: 在测试环境对准生产设备执行（标注 `@pytest.mark.slow`）

---

## Ansible Tower 异步执行集成

### 背景

现有 `ansible_trigger.py` 通过 POST 触发 Ansible Tower (AWX) 的 Job Template 来执行原子操作。Tower 是异步执行引擎（作业排队、调度、分发到独立 worker），而 bamboo-engine Service 的 `execute()` 是同步调用。必须建立"触发 → 轮询 → 提取 → 注入"的完整闭环。

### 已实现

- **TowerService** (`tower_service.py`): Tower REST API 完整封装
  - `launch_job()` → POST job_template/{id}/launch/ → job_id
  - `poll_job()` → 自适应间隔轮询 + WebSocket 实时推送
  - `extract_result()` → artifacts/events/stdout 提取
  - `cancel_job()` → POST /api/v2/jobs/{id}/cancel/
  - 自动重试 Session、连接复用
- **ansible_trigger.py** 重构: 使用 TowerService，执行结果含 `artifacts/summary/elapsed`
- **WebSocket 推送**: `tower_job_update` 消息类型，前端实时获取进度
- **Context 注入**: `_execute_activity()` 将 Tower artifacts 注入 `execution.context`
- **条件求值**: `_evaluate_condition()` 支持 `${node_id.artifacts.key >= N}` 表达式

### 待办

#### 高优先级（轮询可靠性）

- [ ] **超时中断** — 前端发起"取消"时，调 `TowerService.cancel_job()` + 终止 Celery 任务:
  - `flow_engine.py` 新增 `cancel()` 方法: 调用 `TowerService.cancel_job(job_id)` + 标记节点为 cancelled
  - tasks.py 新增 `cancel_pipeline_task(execution_id)` 撤销 Celery 任务
  - 前端 WebSocket 发送 `{"type": "cancel"}` 触发取消流程

- [ ] **并发限制** — Tower 有 `max_concurrent_jobs` 限制，bamboo-engine 需做信号量控制:
  ```python
  # tower_service.py 新增
  from redis import Redis
  TOWER_SEM_KEY = "opsflow:tower:concurrent_sem"
  TOWER_MAX_CONCURRENT = 5  # 从配置读取
  
  def acquire_slot(self) -> bool:
      """尝试获取 Tower 执行槽位（Redis 计数信号量）"""
      r = get_redis_connection("default")
      current = r.incr(TOWER_SEM_KEY)
      if current > TOWER_MAX_CONCURRENT:
          r.decr(TOWER_SEM_KEY)
          return False
      return True
  
  def release_slot(self):
      r = get_redis_connection("default")
      r.decr(TOWER_SEM_KEY)
  ```
  当前伪代码，需结合具体并发策略选择（阻塞等待 vs 快速失败回退到排队）。

- [ ] **节点级超时** — 目前 TowerService.poll_job 的 timeout=3600 是硬编码。需改为从节点的 `timeout_seconds` 参数读取:
  ```python
  # flow_engine.py _execute_activity
  node_timeout = activity.get("component", {}).get("timeout", 3600)
  plain_inputs["_timeout"] = node_timeout
  ```
  当前 ansible_executor 未读取此参数，需在 `execute()` 中传递给 `ansible_trigger.execute_atom()`。

#### 中优先级（运维与监控）

- [ ] **Tower 作业事件持久化** — 将 `poll_job()` 获取的 `events` 写入 `OpsLog`:
  - 当前只在内存中返回，未持久化
  - 需在 `_execute_activity()` 完成时遍历 events 写入 OpsLog 记录
  - 每条 event 对应一条 OpsLog（host/event/stdout）

- [ ] **Mock 模式增强** — 当前 mock 数据过于简单:
  - 不能模拟长时间运行（用于测试 WebSocket 推送）
  - 不支持条件分支的差异化 mock（所有 mock 都返回 success）
  - 改进: `_mock_execute` 支持 `sleep_seconds` 参数模拟延迟，支持 `mock_outcome` 参数（success/failed）模拟不同结果

- [ ] **Tower 连接健康检查** — API 端点/管理命令:
  ```python
  # management/commands/check_tower.py
  class Command(BaseCommand):
      def handle(self, *args, **options):
          tower = get_tower_service()
          try:
              ping = tower._request("GET", "ping/")
              self.stdout.write(f"Tower OK: {ping.json()}")
          except Exception as e:
              self.stderr.write(f"Tower ERROR: {e}")
  ```

#### 低优先级（增强功能）

- [ ] **Webhook 回调方案（替代轮询）**:
  - 背景: 轮询在高并发场景下对 Tower API 有压力（每秒请求数随作业数线性增长）
  - 思路: Tower Settings → Job Completion Webhook URL → POST Django `/api/tower/callback/`
  - 优势: 零延迟通知、减少 API 调用
  - 挑战: 需要 Tower 能访问 Django 服务（网络打通）、需要 Webhook Key 校验、回调丢失需兜底轮询
  - 当前策略: 以轮询为主，回调为可选优化

  ```python
  # 回调接收器（伪代码，需网络打通后实现）
  @api_view(['POST'])
  @permission_classes([IsAuthenticated])
  def tower_callback(request):
      """Tower 作业完成后回调"""
      job_id = request.data.get("id")
      status = request.data.get("status")
      # 1. 从 job_id 反查 execution + node
      # 2. 提取 artifacts
      # 3. 唤醒 bamboo-engine 继续执行
      return Response({"status": "received"})
  ```

- [ ] **Tower API 连接池配置化**:
  - 当前 `HTTPAdapter(max_retries=2)` 是固定值
  - 需改为 Django settings: `TOWER_POOL_CONNECTIONS=10`, `TOWER_POOL_MAXSIZE=20`
  - 避免高并发时 socket 耗尽

- [ ] **条件表达式 DSL 增强**:
  - 当前 `${node_id.artifacts.key >= N}` 支持有限
  - 期望支持: `${node_id.summary.failed > 0 && node_id.artifacts.retry_count < 3}`
  - 需要安全沙箱 eval 或轻量级表达式解析器（如 `simpleeval` 库）
  - 当前不支持 `&&`/`||` 组合条件

- [ ] **Tower 多 Job Template 支持**:
  - 当前只有 `ANSIBLE_TEMPLATE_ID` 一个模板
  - 期望: 不同的原子可以使用不同的 Tower Job Template（通过 meta.json 新增 `tower_template_id` 字段）
  - 需修改 `tower_service.launch_job()` 支持按 atom 指定 template_id
