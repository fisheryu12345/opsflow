# Webhook 增强 + 统一重试机制

> 提交: b3c3b7fa | 日期: 2026-07-11
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

触发器 HTTP 回调 action 只支持 `url + method + body + timeout` 四个字段，无法设置请求头、查询参数、Content-Type、SSL 校验。且所有 action 类型失败后无法自动重试，网络超时/服务不可达导致触发器静默失败。

## 实现方案

### 核心架构

重试逻辑在 `TriggerExecutor.process_pending()` 层统一处理，所有 action 类型（NOTIFY/WEBHOOK/OPSFLOW/MODIFY_FIELD）失败后都能自动重试。每条 action 的 `config.retry = {max, interval}` 控制重试策略，执行时取所有 action 的最大值作为整体重试配置。

### 关键代码

**WebhookRunner — 完整 HTTP 请求配置**（`trigger_service.py:233`）：

- `query_params` → `requests.request(..., params=...)` URL 查询参数
- `headers` → 自定义请求头，自动补充 Content-Type
- `content_type` → 控制 `json=` vs `data=` 参数选择，JSON 解码失败时自动降级
- `ssl_verify` → `requests.request(..., verify=ssl_verify)`
- 统一使用 `requests.request(method, url, **kwargs)` 支持所有 HTTP 方法

**process_pending — 重试逻辑**（`trigger_service.py:334`）：

```python
# 取 PENDING + 到期的 RETRYING
executions = select_for_update(skip_locked=True).filter(
    Q(status='PENDING') | Q(status='RETRYING', next_retry_at__lte=now)
)[:50]

# 对每条 execution:
derive_execution_retry_config(exec)  # 从所有 action config 取 max values
for action in exec.trigger.actions.order_by('order'):
    result = ActionRunner.run(action, ...)
    if result['status'] == 'FAILED':
        break  # 失败后停止后续 action
if has_failure and exec.retry_count < exec.max_retries:
    exec.status = 'RETRYING'
    exec.next_retry_at = now + timedelta(seconds=exec.retry_interval)
else:
    exec.status = 'FAILED' if has_failure else 'SUCCESS'
```

**derive_execution_retry_config()**（`trigger_service.py:393`）：

```python
@staticmethod
def derive_execution_retry_config(exec):
    max_r, interval = 0, 60
    for action in exec.trigger.actions.all():
        retry_cfg = (action.config or {}).get('retry', {})
        max_r = max(max_r, retry_cfg.get('max', 0))
        interval = max(interval, retry_cfg.get('interval', 60))
    exec.max_retries = max_r
    exec.retry_interval = interval
```

### 数据流

```
用户配置 Webhook action → DesignerConfigPanel 表单
  │
  ├─ url/method/headers/query_params/content_type/body_tpl/ssl_verify
  └─ retry: {max: 3, interval: 60}
       │
       ▼ 保存到 TriggerAction.config
       │
       ▼ 工单事件触发 enqueue()
       │
       ▼ TriggerExecutor.process_pending() (每10s)
  ├─ select_for_update(skip_locked) 锁行
  ├─ derive_execution_retry_config() 取最大重试值
  ├─ ActionRunner → WebhookRunner → requests.request()
  ├─ 失败 + retry_count < max_retries → RETRYING + next_retry_at
  └─ 达到最大重试 → FAILED
```

### 设计决策

| 决策 | 原因 |
|------|------|
| 重试在 TriggerExecutor 层而非 ActionRunner 层 | 保证动作顺序执行，失败后从第一个 action 重新开始 |
| 取所有 action 的 max retry | 最宽松策略，保证每个 action 都有机会成功 |
| RETRYING 状态而非直接 PENDING | 区分"待首次执行"和"待重试"，避免无限循环 |
| `select_for_update(skip_locked=True)` | 多 worker 并发安全，跳过已被其他 worker 锁定的行 |
| 失败后 break 不继续后续 action | 避免部分执行的不一致状态（如先改字段再发 webhook 失败） |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/trigger.py` | TriggerExecution 新增 retry_count/max_retries/retry_interval/next_retry_at，STATUS_CHOICES 加 RETRYING/PROCESSING |
| `backend/itsm/services/trigger_service.py` | WebhookRunner 增强(:233)、process_pending 重试(:334)、derive_execution_retry_config(:393) |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | 触发器对话框：卡片布局、Webhook 表单增强、重试配置、i18n(:266-330) |

## 使用方式

1. 打开流程设计器 → 选中节点 → 触发器区域 → 添加触发器 → 动作列表 → 选择 "HTTP 回调"
2. 填写 URL / Method / Body 模板 / Headers / Query Params / Content-Type / SSL
3. 设置重试次数和间隔
4. 保存触发器 → 保存流程 → 部署
5. 工单触发时，失败后自动按配置重试

### 关联文档

- 相关功能文档: [2026-07-11-notification-template-design.md](../specs/2026-07-11-notification-template-design.md)
- 相关配置变更: [trigger-commit-analysis](../../COMMIT_ANALYSIS.md)
