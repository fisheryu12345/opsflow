# SLA 暂停/恢复计时增强

> 提交: 847774f9 | 日期: 2026-07-05
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

此前 SLA 引擎的暂停/恢复逻辑存在两个问题：

1. **暂停不记录时间** — `pause_ticket_sla()` 只更新状态为 `paused`，不记录暂停时刻，导致恢复时无法准确计算扣除时间
2. **重启覆盖计时器** — `start_ticket_sla()` 使用 `update_or_create`，审批节点多次触发 SLA start 会重置已有计时器

本次修复这两问题，使 SLA 暂停/恢复可准确计时。

## 实现方案

### SlaTask 新增 paused_at 字段

```python
# backend/itsm/models/sla.py
class SlaTask(CoreModel):
    paused_at = models.DateTimeField(null=True, blank=True, verbose_name="暂停时间")
```

### pause_ticket_sla 记录暂停时间

```python
@staticmethod
def pause_ticket_sla(ticket):
    now = timezone.now()
    SlaTask.objects.filter(ticket=ticket, task_status='running').update(
        task_status='paused',
        paused_at=now,  # 记录暂停时刻
    )
```

### resume_ticket_sla 用暂停时长补偿 deadline

```python
@staticmethod
def resume_ticket_sla(ticket):
    sla = SlaTask.objects.filter(ticket=ticket, task_status='paused').first()
    if sla:
        now = timezone.now()
        pause_duration = (now - sla.paused_at) if sla.paused_at else timedelta(0)
        if sla.deadline:
            sla.deadline = sla.deadline + pause_duration  # 补偿暂停时长
        if sla.reply_deadline:
            sla.reply_deadline = sla.reply_deadline + pause_duration
        sla.task_status = 'running'
        sla.save(update_fields=['deadline', 'reply_deadline', 'task_status'])
```

### start_ticket_sla 改用 get_or_create

```python
@staticmethod
def start_ticket_sla(ticket):
    # get_or_create 而非 update_or_create — 不覆盖已有计时器
    sla_task, created = SlaTask.objects.get_or_create(
        ticket=ticket,
        defaults={...}
    )
    if not created and sla_task.task_status == 'paused':
        SlaEngine.resume_ticket_sla(ticket)  # 恢复暂停的 SLA
```

### 数据流

```
工单暂停 → pause_ticket_sla() → 记录 paused_at = now()
工单恢复 → resume_ticket_sla() → compensation = now() - paused_at
                                → SLA.deadline += compensation
工单运行中新审批节点触发 → start_ticket_sla() get_or_create → 已存在不覆盖
                                                   ↕ 如果 paused → resume
```

### 关联文档

- 相关调试记录: [SLA Engine Field Mismatch Fix](../debug/2026-06-30-sla-engine-field-mismatch-fix.md)

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/sla.py:46` | SlaTask.paused_at 字段 |
| `backend/itsm/services/sla_engine.py:51-80` | pause/resume/start 逻辑 |
