# ITSM 服务目录（Service Catalog）

> 提交: 88b61c0f | 日期: 2026-07-05
> 涉及 App: itsm, iam
> 类型: 功能新增

---

## 背景

ITSM 已有 Workflow（流程模板引擎）、Ticket（Pipeline 驱动工单）、ServiceCategory（服务分类）、分派体系和 SLA 引擎等完整能力，但缺少一个统一的服务目录入口。用户创建工单需要先理解"流程模板"概念，体验不够直观。

本次新增**服务目录（Service Catalog）**功能，以"双视图"架构同时满足普通用户和运维管理员的需求。

## 实现方案

### 核心架构

```
ServiceItem（新增模型）
├── name, description, icon, mode（flow/lightweight）
├── category → ServiceCategory（分类归属）
├── workflow → Workflow（可选绑定流程）
├── form_fields（自定义表单字段定义）
├── visible_to/visible_roles/visible_users（可见性控制）
├── default_assignee（快捷服务分派配置）
└── expected_duration, sort_order, is_active
```

支持两种服务模式：
- **流程驱动（flow）**：绑定 Workflow，用户提交 → 创建 WorkflowVersion 快照 → 创建 Ticket → 启动 Pipeline
- **快捷服务（lightweight）**：不绑定 Workflow，用户提交 → 创建轻量 Ticket → 直接分派

### 关键代码

**ServiceItem 模型：**
```python
# backend/itsm/models/service_item.py
class ServiceItem(CoreModel):
    MODE_CHOICES = (('flow', '流程驱动'), ('lightweight', '快捷服务'))
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=64, null=True, blank=True)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default='flow')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, ...)
    workflow = models.ForeignKey(Workflow, on_delete=models.SET_NULL, null=True, blank=True)
    form_fields = models.JSONField(default=list)
    visible_to = models.CharField(max_length=64, default='all')
    ...
```

**Submit（服务申请提交）：**
```python
# backend/itsm/views/service_item.py
@action(methods=['POST'], detail=True)
def submit(self, request, pk=None):
    service_item = self.get_object()
    if service_item.mode == 'flow':
        version = workflow.create_version(operator=user.id)
        ticket = Ticket.objects.create(workflow_version=version, ...)
        engine = ITSMEngine(ticket)
        engine.run(operator=user.id, form_data=form_data)
    else:
        ticket = Ticket.objects.create(current_status='assigned', ...)
```

**前端服务市场（ServiceMarket.vue）：**
- 左侧分类树（从 ServiceCategory 构建）
- 右侧卡片网格（显示图标、名称、描述、模式标签、预计时长）
- 搜索 + 模式筛选（全部/流程驱动/快捷服务）

**前端服务详情（ServiceDetail.vue）：**
- 服务头部信息 + 描述 + 动态渲染表单字段
- 支持 TEXT/SELECT/RADIO/CHECKBOX 等字段类型
- 提交后调用 SubmitServiceItem API

**前端管理后台（ServiceAdmin.vue）：**
- 服务项表格 CRUD
- 编辑弹窗（名称/分类/模式/流程绑定/可见性/状态）
- 只读预览弹窗（模拟用户视角的表单渲染）

### 数据流

```
管理员创建服务项 → 配置表单字段 → 关联 Workflow
用户浏览服务市场 → 选择服务项 → 填写表单 → 提交
  → flow 模式：Workflow.create_version() → Ticket.create() → ITSMEngine.run()
  → lightweight 模式：Ticket.create(current_status='assigned')
  → 返回 ticket_id，用户在工单中追踪
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 表单字段存储 | ServiceItem.form_fields（JSON） | 与 Workflow 字段分离，申请表单 vs 审批表单不同用途 |
| 可见性控制 | visible_to 简单模型 | 初期够用，后续可对接 IAM 细粒度权限 |
| 服务模式 | flow + lightweight 双模式 | flow 用于有审批流程的场景，lightweight 用于简单请求 |
| Tab 控制 | IAM page-permissions API | 服务市场全员可见，管理后台仅 admin |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/service_item.py` | ServiceItem 模型定义 |
| `backend/itsm/serializers/service_item.py` | 序列化器（含 submit 验证） |
| `backend/itsm/views/service_item.py` | ViewSet + submit action |
| `backend/itsm/urls.py` | 注册 service-items 路由 |
| `web/src/views/apps/itsm/catalog/ServiceMarket.vue` | 服务市场浏览页面 |
| `web/src/views/apps/itsm/catalog/ServiceDetail.vue` | 服务详情+申请表单页面 |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 服务管理后台 |
| `backend/itsm/management/commands/seed_itsm.py` | 12 个 Mock 服务项种子数据 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 新增 IAM tab 和权限配置 |

## 使用方式

- **普通用户**：打开 ITSM → 点击"服务市场"Tab → 浏览分类 → 选服务 → 填表提交
- **管理员**：打开 ITSM → 点击"服务目录管理"Tab → 管理服务项
- **API**：`GET /api/itsm/service-items/` 列出可用服务，`POST /api/itsm/service-items/:id/submit/` 提交申请
