# OpsFlow — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 状态 | ✅ 目标达成 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| FlowEngine 流程引擎 | P0 | ✅ | Pipeline 执行入口 (start/pause/resume/cancel/retry/skip) | 完整，含子流程重试 |
| PipelineBuilder | P0 | ✅ | pipeline_tree → bamboo-engine DAG | 节点元素(Exclusive/Parallel/Converge Gateway)，NodeOutput 注册，回环检测 |
| PluginService 路由 | P0 | ✅ | 原子执行路由 (execute/schedule/rollback) | 完整，含异步 schedule 轮询 |
| Plugin Registry | P0 | ✅ | 插件管理 | 15组77原子插件，自动发现+版本管理 |
| SafetyGuard 校验 | P0 | ✅ | Pipeline 安全校验 | 结构验证+环检测+连接性+插件白名单+语义冲突 | 
| LayoutEngine 布局 | P0 | ✅ | Sugiyama 自动布局 | 完整9子模块 |
| VariableResolver 变量 | P0 | ✅ | ${key} + Mako | plain/splice/split/lazy 类型 |
| LLMService AI | P0 | ✅ | DeepSeek 生成/精炼/分析 | 集成中心 AI 连接器 |
| SchedulerService 调度 | P0 | ✅ | APScheduler 定时调度 | cron/one_time/cmdb_event |
| Signal 信号链 | P0 | ✅ | 状态变更异步处理 | state/trace/notify/timeout |
| DesignCanvas 画布 | P0 | ✅ | X6 可视化设计 | 拖拽/连接/属性/AI 布局/条件编辑器 |
| MonitorCanvas 监控 | P0 | ✅ | 实时监控 | 着色/追踪/日志/审批 |
| PropertyPanel 属性 | P0 | ✅ | 节点/边配置 | 插件表单/参数/条件/Loop/变量浏览器 |
| 执行向导 (5步) | P0 | ✅ | 校验→CR→变量→风险→调度 | 完整实现 |
| 审批节点 | P0 | ✅ | 多级审批/会签 | 暂停+恢复 |
| 手动暂停原子 | P1 | ✅ | Pipeline 中无条件暂停 | 通用插件 `ManualPausePlugin`，PluginService 直接调 FlowEngine.pause()，前端蓝色 banner 提示，复用 Resume 按钮 |
| 子流程 | P0 | ✅ | 嵌入/独立 | 变量映射+输出映射 |
| 版本管理 | P0 | ✅ | 发布/回滚 | snapshot 冻结 |
| 定时计划 | P1 | ✅ | CRUD + pause/resume | 含调度历史 |
| Webhook | P1 | ✅ | 完成/失败回调 | 签名+重试+投递日志 |
| 模板收藏 | P1 | ✅ | collect/uncollect | 用户级 |
| 导出导入 | P1 | ✅ | JSON 导出/导入 | 含 categories |
| AI 布局 | P1 | ✅ | 自动布局 | Sugiyama 后端 |
| 仪表盘 | P1 | ✅ | 11 统计端点 | ECharts 前端 |
| Dry Run | P1 | ✅ | 模拟执行 | test 原子替换 |
| 自动重试 | P2 | ✅ | 失败自动 | Celery 调度 |
| 超时策略 | P2 | ✅ | 节点超时 | Redis Sorted Set |
| 变量浏览器 | P2 | ✅ | 引用/插入 | DOM 光标 |
| 多轮对话 | P2 | ✅ | 自然语言修改 | 上下文+layout 识别 |
| 多租户隔离 | P2 | ✅ | Project 过滤 | iam.TenantPermission |
| 节点持久化同步 | P2 | ✅ | ↔ TemplateNode | sync 服务 |
| loop_iteration 追踪 | P2 | ✅ | 循环多行记录 | _resolve_loop_iteration |
| 条件编辑器 | P2 | ✅ | 结构化条件 | 排他网关条件编辑 |
| 模板冲突提示 | P2 | ✅ | 多人编辑冲突 | TemplateLock 悲观锁+心跳(30s)+过期自动释放(60s)+弹窗提示 |
| CI/CD + K8s 部署 | P2 | 📅 | Helm Chart | — |

## TODO

- [x] 模板自动保存冲突提示（P2） ✅
- [ ] CI/CD + K8s 部署支持（P2）
- [x] 测试框架统一: 18 → 252 个测试发现 ✅
- [x] 端到端 E2E 测试: 串行/并行/排他/回环/loop 全覆盖 ✅

### 2026-06-28 Update
> 提交: 6ce7605d
- 模板冲突提示: 状态改为 ✅ — TemplateLock 悲观锁实现（心跳+过期+弹窗阻挡）

### 2026-06-28 Update
> 提交: 31664118
- 测试框架: 14 个 pytest 文件 → Django TestCase/SimpleTestCase 统一
- 新增 TemplateLock 测试 9 个（acquire/release/heartbeat/expiry/loop_iteration）
- 测试发现: 18 → 240 个（python manage.py test 单命令运行）
- pytest 已从项目移除

### 2026-06-28 Update
> 提交: 5f00962e
- 端到端 E2E 测试: 6 个测试覆盖串行/并行/排他/回环(Mechanism B)/loop_config(Mechanism A)
- 测试总数: 240 → 252

### 2026-06-29 Update
> 提交: 6e23a2f0
- 手动暂停原子: 新增 ✅ — ManualPausePlugin + PluginService 直接暂停 + 蓝色横幅
- Optional 跳过修复: handlers.py FAILED 分支补全

### 2026-06-29 Update
> 提交: 8834b280
- Approval 重构: 标准插件 + IAM 用户搜索 API + stencil 清理

### 2026-06-30 Update
> 提交: e39712c8
- 全插件组中英文补齐: 17 组 61 文件（name_en/icon/color/version/output_schema/i18n）
- ESXi 6 文件语法修复 + git hooks + VS Code 配置

### 2026-06-30 Update
> 提交: b91ba26c
- ITSM SLA 引擎 bug 修复
