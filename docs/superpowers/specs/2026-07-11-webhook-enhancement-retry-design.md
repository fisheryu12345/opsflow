# Webhook 增强 + 统一重试 — Design Spec

> **Date:** 2026-07-11
> **Status:** Design Complete
> **Context:** HTTP 回调 config 太简陋，需加请求参数配置 + 统一重试机制

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Webhook 增强 | headers UI + query_params + content_type + ssl_verify | 覆盖日常 HTTP 调用需求 |
| 重试范围 | 所有动作类型统一重试（TriggerExecutor 层） | NOTIFY/WEBHOOK/OPSFLOW/MODIFY_FIELD 失败后都能重试 |
| 重试粒度 | 每次执行整体重试（从头执行所有 actions） | 简单可靠，单 action 重试语义复杂 |
| max_retries/interval | 每条 action 的 config 中取最大值 | 最宽松策略保证所有 action 有机会重试 |

---

## 1. Data Model Changes

### 1.1 TriggerExecution 新增字段

```
TriggerExecution (trigger.py):
    # NEW fields
    retry_count = IntegerField(default=0)        # 已重试次数
    max_retries = IntegerField(default=0)        # 最大重试次数
    retry_interval = IntegerField(default=60)    # 重试间隔(秒)
    next_retry_at = DateTimeField(null=True)     # 下次重试时间

    # NEW status
    STATUS_CHOICES 加 ('RETRYING', '重试中')
```

### 1.2 TriggerAction.config 新增字段

Webhook 类型：
```json
{
    "url": "",
    "method": "POST",
    "headers": {"Authorization": "Bearer xxx"},
    "query_params": {"key": "value"},       // NEW
    "body_tpl": "",
    "content_type": "application/json",      // NEW, default
    "timeout": 30,
    "ssl_verify": true,                      // NEW, default true
    "retry": {"max": 3, "interval": 60}      // NEW, per-action retry config
}
```

NOTIFY/OPSFLOW/MODIFY_FIELD 类型各加：
```json
"retry": {"max": 0, "interval": 60}         // max=0 = no retry
```

---

## 2. Service Layer Changes

### 2.1 process_pending() 重试逻辑

```python
@staticmethod
def process_pending():
    now = timezone.now()
    executions = select_for_update(skip_locked=True).filter(
        Q(status='PENDING') |
        Q(status='RETRYING', next_retry_at__lte=now)
    )[:50]

    for exec in executions:
        exec.status = 'PROCESSING'
        _derive_retry_config(exec)  # take max retry from all actions
        try:
            results = []
            for action in exec.trigger.actions.order_by('order'):
                result = ActionRunner.run(action, exec.ticket, ...)
                results.append(result)
                if result['status'] == 'FAILED':
                    break
            exec.action_results = results
            has_failure = any(...)
            if has_failure and exec.retry_count < exec.max_retries:
                exec.retry_count += 1
                exec.status = 'RETRYING'
                exec.next_retry_at = now + timedelta(seconds=exec.retry_interval)
            else:
                exec.status = 'FAILED' if has_failure else 'SUCCESS'
        except Exception as e:
            exec.status = 'FAILED'
        exec.save()
```

### 2.2 WebhookRunner 增强

```python
class WebhookRunner:
    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        url = config.get('url', '')
        method = config.get('method', 'POST').upper()
        timeout = config.get('timeout', 30)
        headers = dict(config.get('headers', {}))
        query_params = config.get('query_params', {})
        ssl_verify = config.get('ssl_verify', True)
        content_type = config.get('content_type', 'application/json')

        body_str = TemplateResolver.resolve(config.get('body_tpl', ''), ticket, ...)
        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            body = body_str
            if content_type == 'application/json':
                content_type = 'text/plain'

        if 'Content-Type' not in headers:
            headers['Content-Type'] = content_type

        if isinstance(body, dict) and content_type == 'application/json':
            resp = requests.request(method, url, json=body, params=query_params,
                                    headers=headers, timeout=timeout, verify=ssl_verify)
        else:
            resp = requests.request(method, url, data=body, params=query_params,
                                    headers=headers, timeout=timeout, verify=ssl_verify)

        resp.raise_for_status()
        return {'action_type': 'WEBHOOK', 'status': 'SUCCESS', 'http_status': resp.status_code}
```

---

## 3. Frontend — DesignerConfigPanel.vue Webhook 表单

NOTIFY 动作表单扩展（每个类型都会增加 retry 配置）：

```
Webhook 配置:
  URL:         [input]
  Method:      [POST/PUT/GET/DELETE/PATCH dropdown]
  Headers:     [key-value table] (自定义请求头)
  Query Params:[key-value table] (URL 查询参数)
  Content-Type:[application/json / text/plain / ... dropdown]
  Body:        [textarea]
  Timeout:     [number input, default 30]
  SSL Verify:  [checkbox, default on]

  重试配置 (所有动作类型共有):
  最大重试次数: [number input, default 0]
  重试间隔(秒): [number input, default 60]
```

---

## 4. Files Summary

| File | Action |
|------|--------|
| `backend/itsm/models/trigger.py` | TriggerExecution: +4 fields + RETRYING status |
| `backend/itsm/services/trigger_service.py` | process_pending 重试逻辑 + WebhookRunner 增强 |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | Webhook 表单增强 + retry 配置 |

**Migration:** 1 个 (TriggerExecution 加 4 个新字段)

---

## 5. Test Plan

| ID | Test |
|----|------|
| T1 | WebhookRunner: query_params 正确追加到 URL |
| T2 | WebhookRunner: ssl_verify=False 时 requests 不验证证书 |
| T3 | WebhookRunner: JSON body + application/json → json= body |
| T4 | WebhookRunner: text body → data= body |
| T5 | Retry: action 失败 + retry_count < max_retries → RETRYING |
| T6 | Retry: 达到 max_retries → FAILED |
| T7 | Retry: next_retry_at 到期后重新被取到 |
| T8 | Retry: process_pending 同时取 PENDING + 到期的 RETRYING |
