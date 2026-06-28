# 模板冲突提示设计 — 悲观锁方案

> **版本:** v1.0  
> **日期:** 2026-06-28  
> **状态:** 设计完成，待评审

---

## 1. 设计目标

防止多人同时编辑同一 FlowTemplate 导致数据相互覆盖。采用**悲观锁**机制：用户打开模板编辑时加锁，保存/退出时释放，其他用户尝试编辑时提示锁信息。

---

## 2. 核心概念

### 锁的生命周期

```
用户 A 打开画布 → 后端创建锁 → 用户 A 编辑
                          ↓ 每 30 秒心跳续约
用户 B 尝试打开 → 检查锁存在 → 提示"A 正在编辑" → 禁止进入
                          ↓
用户 A 保存/退出 → 释放锁
                          ↓
用户 B 可重新尝试 → 锁不存在 → 允许进入
                          ↓
用户强关浏览器 → 60 秒无心跳 → 锁自动释放（Cron 清扫）
```

### 实时性

通过前端轮询（非 WebSocket）检测锁状态。原因：
- OPSflow 当前 WebSocket 仅用于执行监控，无协作基础设施
- 悲观锁的核心价值是"保存时不覆盖"而非"实时协作"
- 等真正需要实时协作（如 Google Docs 式协同编辑）时再升级到 WebSocket

---

## 3. 数据模型

```python
# backend/opsflow/models/template.py 新增

class TemplateLock(models.Model):
    """模板编辑锁 — 打开画布时创建，保存/退出时释放，心跳超时自动清除"""

    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.CASCADE, unique=True,
        related_name='edit_lock',
        verbose_name="Template",
        help_text="被锁定的模板 / Locked template"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="Locked By",
        help_text="持有锁的用户 / User holding the lock"
    )
    locked_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Locked At",
        help_text="锁定时间 / When the lock was acquired"
    )
    heartbeat = models.DateTimeField(
        auto_now=True, verbose_name="Heartbeat",
        help_text="最近心跳时间 / Last heartbeat from the lock holder"
    )

    class Meta:
        db_table = 'ops_template_lock'
        verbose_name = "Template Lock"

    def is_expired(self, timeout_seconds=60) -> bool:
        """心跳超时判断"""
        if not self.heartbeat:
            return True
        delta = timezone.now() - self.heartbeat
        return delta.total_seconds() > timeout_seconds
```

---

## 4. API 端点

### 4.1 获取锁 `POST /api/opsflow/templates/{id}/acquire_lock/`

**请求：** 无 body

**成功响应 (201)：**
```json
{
  "code": 2000,
  "data": {
    "template_id": 42,
    "locked_by": { "id": 1, "username": "alice" },
    "locked_at": "2026-06-28T10:00:00Z"
  }
}
```

**冲突响应 (409)：**
```json
{
  "code": 4000,
  "msg": "模板正在被 alice 编辑，请稍后再试",
  "data": {
    "locked_by": { "id": 1, "username": "alice" },
    "locked_at": "2026-06-28T10:00:00Z"
  }
}
```

### 4.2 释放锁 `POST /api/opsflow/templates/{id}/release_lock/`

**请求：** 无 body（后端从 request.user 确定释放谁的锁）

**成功 (200)：** 锁被删除

**Idempotent：** 锁不存在时也返回 200（安全幂等）

### 4.3 心跳 `POST /api/opsflow/templates/{id}/heartbeat_lock/`

**请求：** 无 body

**成功 (200)：** 更新 `heartbeat = now()`

**锁过期 (410)：** 锁超时，返回提示（前端应停止编辑）

---

## 5. 后端改动

### 5.1 ViewSet 新增 action

```python
# backend/opsflow/views/template_views.py

class FlowTemplateViewSet(
    ...
    ProjectFilteredViewSet,
):
    # ... 现有代码 ...

    @action(detail=True, methods=['post'])
    def acquire_lock(self, request, pk=None):
        """获取模板编辑锁"""
        template = self.get_object()
        lock, created = TemplateLock.objects.get_or_create(
            template=template,
            defaults={'user': request.user},
        )
        if created:
            return DetailResponse(data=lock_info(lock), msg='Lock acquired')
        
        # 锁已存在：检查是否可覆盖（同一用户 / 超时）
        if lock.user == request.user:
            lock.heartbeat = timezone.now()
            lock.save(update_fields=['heartbeat'])
            return DetailResponse(data=lock_info(lock), msg='Lock refreshed')
        
        if lock.is_expired():
            # 超时锁，强制转移
            lock.user = request.user
            lock.locked_at = timezone.now()
            lock.heartbeat = timezone.now()
            lock.save(update_fields=['user', 'locked_at', 'heartbeat'])
            return DetailResponse(data=lock_info(lock), msg='Expired lock transferred')
        
        # 真正的冲突
        return ErrorResponse(
            msg=f'Template is being edited by {lock.user.username}',
            code=4000,
            data=lock_info(lock),
        )

    @action(detail=True, methods=['post'])
    def release_lock(self, request, pk=None):
        """释放模板编辑锁"""
        TemplateLock.objects.filter(
            template_id=pk, user=request.user
        ).delete()
        return DetailResponse(msg='Lock released')

    @action(detail=True, methods=['post'])
    def heartbeat_lock(self, request, pk=None):
        """锁心跳"""
        lock = TemplateLock.objects.filter(template_id=pk, user=request.user).first()
        if not lock:
            return ErrorResponse(msg='No active lock found', code=4000)
        if lock.is_expired():
            lock.delete()
            return ErrorResponse(msg='Lock expired', code=410)
        lock.heartbeat = timezone.now()
        lock.save(update_fields=['heartbeat'])
        return DetailResponse(msg='Heartbeat updated')
```

### 5.2 锁定保护

在 `update` 方法中检查锁，防止直接调 API 绕过：

```python
def update(self, request, *args, **kwargs):
    # 检查编辑锁（superuser 不受限、自己持有锁不受限）
    if not request.user.is_superuser:
        lock = TemplateLock.objects.filter(template_id=kwargs.get('pk')).first()
        if lock and lock.user != request.user and not lock.is_expired():
            return ErrorResponse(msg=f'Locked by {lock.user.username}', code=4000)
    return super().update(request, *args, **kwargs)
```

### 5.3 定时清理过期锁

```python
# backend/opsflow/management/commands/clean_expired_locks.py
# 每分钟执行一次
class Command(BaseCommand):
    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(seconds=60)
        deleted, _ = TemplateLock.objects.filter(heartbeat__lt=cutoff).delete()
        self.stdout.write(f"Cleaned {deleted} expired locks")
```

合并到现有 `scheduler_service.py` 的定时任务（与 timeout check 同级）。

---

## 6. 前端改动

### 6.1 打开模板时的锁检查

```typescript
// web/src/views/apps/opsflow/index.vue
// onSelectTemplate 加入 acquire_lock 调用

async function onSelectTemplate(id: any) {
  if (!id) return
  
  // 尝试获取锁
  try {
    await AcquireLock(id)
    isLockedByMe.value = true
  } catch (e: any) {
    if (e?.response?.status === 409) {
      const data = e.response.data.data
      ElMessageBox.alert(
        `模板正在被 ${data.locked_by?.username || '其他用户'} 编辑，请稍后再试。`,
        '模板已被锁定',
        { type: 'warning', confirmButtonText: '确定' }
      )
      return  // 不加载画布
    }
  }
  
  // 继续加载模板（现有逻辑）
  // ...
}
```

### 6.2 心跳保活

```typescript
// index.vue — 锁成功后启动心跳

let heartbeatTimer: number | null = null

function startHeartbeat(templateId: number) {
  heartbeatTimer = window.setInterval(async () => {
    try {
      await HeartbeatLock(templateId)
    } catch {
      // 心跳失败 → 可能锁已过期 → 提示用户
      ElMessage.warning('编辑锁已过期，请重新打开模板')
      isLockedByMe.value = false
      stopHeartbeat()
    }
  }, 30000)  // 30 秒一次
}

function stopHeartbeat() {
  if (heartbeatTimer !== null) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}
```

### 6.3 保存/退出时释放锁

```typescript
// index.vue — onSaveDraft 成功/失败后释放
async function onSaveDraft(data: any) {
  try {
    await UpdateTemplate(selectedTemplateId.value, { pipeline_tree: data })
    ElMessage.success('已保存')
    await ReleaseLock(selectedTemplateId.value)
  } catch (e: any) {
    ElMessage.error('保存失败')
  }
}

// 页面关闭/路由离开时释放
onBeforeUnmount(() => {
  if (selectedTemplateId.value) {
    stopHeartbeat()
    ReleaseLock(selectedTemplateId.value).catch(() => {})
  }
})
```

### 6.4 API 封装

```typescript
// web/src/views/apps/opsflow/api/templates.ts
export const AcquireLock = createMutation('POST', 'templates/{id}/acquire_lock/')
export const ReleaseLock = createMutation('POST', 'templates/{id}/release_lock/')
export const HeartbeatLock = createMutation('POST', 'templates/{id}/heartbeat_lock/')
```

---

## 7. 前端 API 请求封装

```typescript
// web/src/views/apps/opsflow/api/templates.ts
// 使用已有的 createMutation 工厂函数

export const AcquireLock = (id: number) => request.post(`/api/opsflow/templates/${id}/acquire_lock/`)
export const ReleaseLock = (id: number) => request.post(`/api/opsflow/templates/${id}/release_lock/`)
export const HeartbeatLock = (id: number) => request.post(`/api/opsflow/templates/${id}/heartbeat_lock/`)
```

---

## 8. 改动文件清单

| 层次 | 文件 | 改动 |
|:----:|------|------|
| 模型 | `backend/opsflow/models/template.py` | 新增 `TemplateLock` 模型 |
| 迁移 | 自动生成 | `makemigrations` 自动生成 |
| 视图 | `backend/opsflow/views/template_views.py` | 新增 `acquire_lock/release_lock/heartbeat_lock` 三个 action; `update` 增加锁检查 |
| URL | `backend/opsflow/urls.py` | action 路由由 router 自动注册，无需手动添加 |
| 管理命令 | `backend/opsflow/management/commands/clean_expired_locks.py` | 清扫过期锁 |
| 前端 API | `web/src/views/apps/opsflow/api/templates.ts` | 3 个 API 函数 |
| 前端页面 | `web/src/views/apps/opsflow/index.vue` | `onSelectTemplate` 获取锁；心跳保活；保存/退出释放；`onBeforeUnmount` 清理 |
| 调度 | `backend/opsflow/core/scheduler_service.py` | 注册 clean_expired_locks 定时任务（可选） |

---

## 9. 设计决策记录

| # | 决策 | 选择 | 理由 |
|---|------|------|------|
| 1 | 锁类型 | 悲观锁（编辑时加锁） | 用户要求 B |
| 2 | 锁作用域 | 整个模板 | 用户选择 A |
| 3 | 锁超时 | 60 秒无心跳自动释放 | 防死锁 |
| 4 | 心跳间隔 | 30 秒 | 60s 超时的 1/2，留有缓冲 |
| 5 | 冲突用户提示 | 弹窗+不允许进入 | 用户选择 A |
| 6 | 超时锁处理 | 强制转移给新请求者，不保留 | 避免死锁堆叠 |
| 7 | 锁信息展示 | 显示 locked_by.username | 用户知道找谁协调 |
