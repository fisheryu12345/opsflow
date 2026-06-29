# SLA 引擎字段名不匹配修复

> 提交: (待提交) | 日期: 2026-06-30
> 涉及 App: itsm
> 类型: 修复

---

## 问题

`SlaEngine.start_ticket_sla()` 中引用了 `policy.handle_time` 和 `policy.reply_time`，但 `SlaPolicy` 模型定义的实际字段名为 `response_minutes` 和 `resolve_minutes`。运行时触发 `AttributeError`。

## 修复

修改 `sla_engine.py:40-41`：

```python
# 修复前
handle_deadline = now + timedelta(minutes=policy.handle_time)
reply_deadline = now + timedelta(minutes=policy.reply_time)

# 修复后
handle_deadline = now + timedelta(minutes=policy.response_minutes)
reply_deadline = now + timedelta(minutes=policy.resolve_minutes)
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/services/sla_engine.py` | 修正字段引用名 |
