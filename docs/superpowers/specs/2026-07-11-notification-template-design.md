# ITSM 通知模板 — Design Spec

> **Date:** 2026-07-11
> **Status:** Design Complete (pending approval)
> **Context:** 触发器 NOTIFY 动作需要可复用的通知模板

---

## Context

当前触发器 NOTIFY 动作的通知内容（标题、正文、渠道、接收人）全部内联写在 config JSON 中，每次配置都要手写。引入通知模板管理后，预定义可复用模板，触发器选择模板即可自动填入全部通知配置。

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 模板内容范围 | 标题 + 正文 + 渠道 + 接收人 | 完整预设，选模板无需再配 |
| 管理入口 | ITSM 子 tab | 对齐 SlaPolicy/Escalation 模式 |
| 模板变量 | 复用 TemplateResolver：`${ticket_id}`, `${field.xxx}` 等 | 与触发器一致 |
| 触发器集成 | NOTIFY action 增加 template_id 下拉 | 选模板后自动填充，也可手动覆盖 |

---

## 1. Data Model

```
File: backend/itsm/models/notification_template.py (NEW)

NotificationTemplate(CoreModel):
    name = CharField(128)                             # "P1工单审批通过通知"
    name_en = CharField(128, blank=True, default='')
    project = FK → iam.Project (null=True, blank=True, on_delete=SET_NULL,
                                related_name='itsm_notification_templates')
    is_active = BooleanField(default=True)

    # Notification preset
    channels = JSONField(default=list)                # ["site", "wecom", "dingtalk", "email"]
    title_tpl = CharField(max_length=500, blank=True, default='')
    body_tpl = TextField(blank=True, default='')
    receivers = JSONField(default=list)               # ["processor", "starter", "leader"]

    class Meta:
        db_table = table_prefix + "itsm_notification_template"
        verbose_name = "通知模板"
        verbose_name_plural = verbose_name
```

---

## 2. API Layer

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/itsm/notification-templates/` | list | List templates (`?is_active=&search=`) |
| `POST /api/itsm/notification-templates/` | create | Create template |
| `GET /api/itsm/notification-templates/{id}/` | retrieve | Get template |
| `PUT /api/itsm/notification-templates/{id}/` | update | Update template |
| `DELETE /api/itsm/notification-templates/{id}/` | destroy | Delete template |

Serializer extends `CustomModelSerializer`, `Meta.fields = "__all__"`. ViewSet extends `ItsmProjectViewSet`.

---

## 3. Trigger NOTIFY Action Change

**Impact:** `DesignerConfigPanel.vue` 中 NOTIFY 动作表单，增加"选择模板"下拉框：

- 加载 `GET /api/itsm/notification-templates/?is_active=true`
- 选择模板后 → 自动填充 `title_tpl`, `body_tpl`, `channels`, `receivers` 到当前 action 的 config
- 用户仍可手动修改覆盖

**Model change:** `TriggerAction.config` 增加可选字段 `template_id`（仅前端传值、notification-runner 可选使用），或纯前端行为（选模板时写入对应字段到 config）。采用**纯前端填充**方式，不改变 `config` schema —— 选模板 = 把模板的 channels/title_tpl/body_tpl/receivers 拷贝到 action config。

---

## 4. Frontend

### 4.1 NotifTemplateList.vue (NEW)

遵循 `SlaPolicyList.vue` 表格+弹窗 CRUD 模式：

**Table**: 名称 | 渠道(标签) | 接收人(标签) | 启用(switch) | 操作

**Edit Dialog**:
- 基本信息：name, name_en, is_active switch
- 模板内容：title_tpl input, body_tpl textarea
- 渠道：el-checkbox-group（站内/企微/钉钉/邮件）
- 接收人：el-checkbox-group（处理人/提单人/组长）
- 模板变量提示：`${ticket_id}`, `${ticket_title}`, `${priority}`, `${current_state}`, `${starter_name}`, `${processor_name}`, `${field.xxx}`

### 4.2 DesignerConfigPanel.vue (MODIFY)

NOTIFY action 配置区增加模板选择器：

```
[通知模板: 下拉选择 ▾] [预览]
标题: [自动填充, 可编辑]
正文: [自动填充, 可编辑]
渠道: [自动填充, 可编辑]
接收人: [自动填充, 可编辑]
```

### 4.3 ITSM index.vue (MODIFY)

新增 `notification-templates` tab，导入 `NotifTemplateList`，加懒加载。

### 4.4 API Client

```typescript
// web/src/api/itsm/index.ts
export const notificationTemplateApi = createCrudApi('notification-templates')
```

### 4.5 i18n

Namespace: `message.notifTemplate.*` (zh-CN + en)

### 4.6 IAM Seed

新增：permission `itsm:notif_template:edit` + tab `notification-templates` + role binding。

---

## 5. Migration

单次 migration：CreateModel NotificationTemplate。无数据迁移。

---

## 6. Files Summary

| File | Action |
|------|--------|
| `backend/itsm/models/notification_template.py` | NEW |
| `backend/itsm/models/__init__.py` | MODIFY (export) |
| `backend/itsm/serializers/notification_template.py` | NEW |
| `backend/itsm/views/notification_template_views.py` | NEW |
| `backend/itsm/urls.py` | MODIFY (register) |
| `web/src/api/itsm/index.ts` | MODIFY |
| `web/src/i18n/pages/itsm/zh-cn.ts` | MODIFY |
| `web/src/i18n/pages/itsm/en.ts` | MODIFY |
| `web/src/views/apps/itsm/components/NotifTemplateList.vue` | NEW |
| `web/src/views/apps/itsm/index.vue` | MODIFY |
| `web/src/views/apps/itsm/designer/DesignerConfigPanel.vue` | MODIFY |
| `backend/iam/management/commands/seed_iam_page_configs.py` | MODIFY |

---

## 7. Test Plan

| ID | Test | Verify |
|----|------|--------|
| T1 | Template CRUD API | list/create/retrieve/update/delete |
| T2 | Template selection in trigger | Selecting template fills action config fields |
| T3 | Template variable resolution | `${ticket_id}` etc. resolved correctly at notify time |
| T4 | Manual override after template | User can modify auto-filled values |
| T5 | Frontend template management | Table + dialog CRUD works |

---

## 8. Verification

1. `python manage.py migrate` — migration clean
2. Create template in UI → appears in list
3. Open trigger editor → select template → NOTIFY action config auto-fills
4. Submit ticket with matching trigger → notification sent using selected template
