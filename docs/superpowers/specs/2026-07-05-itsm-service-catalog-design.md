# ITSM 服务目录（Service Catalog）设计方案

- **Date:** 2026-07-05
- **Status:** Design Approved
- **Author:** Claude

---

## Context

当前 ITSM 模块已有完整的 Workflow（流程模板引擎）、Ticket（Pipeline 驱动工单）、ServiceCategory（服务分类）、分派体系（技能组/排班/路由规则/升级）、SLA 引擎等能力，但缺少一个统一的服务目录入口。现有创建工单的流程需要用户理解"流程模板"概念，对普通用户不友好。

本设计新增**服务目录（Service Catalog）**功能，以"双视图"架构同时满足普通用户和运维管理员的需求。

### 现有基础

- **ServiceCategory** — 两级树形服务分类（已有数据模型，14 个种子分类）
- **Workflow** — 可视化 DAG 流程设计器，支持审批/填单/网关/子流程
- **Ticket** — Pipeline 驱动的工单运行时，支持审批、会签、表单填写
- **AssignRule/SkillGroup** — 路由分派体系
- **SlaPolicy** — SLA 策略定义

### 设计目标

1. **普通用户**：提供可视化的"服务市场"，浏览、搜索、选择服务，填表即提交
2. **运维管理员**：提供服务目录管理后台，配置服务项、绑定流程、控制可见性
3. **灵活模式**：服务项可绑定 Workflow（流程驱动），也可不绑定 Workflow（快捷服务）
4. **复用现有能力**：最大程度复用 Workflow/Ticket/分派/SLA 已有体系

---

## 架构概览

### 双视图

```
用户端（服务市场）
├── 分类树 + 搜索 + 卡片浏览
├── 服务详情页 → 填表单 → 提交
└── 我的工单中追踪进度

管理端（服务目录管理）
├── 服务项列表（表格 CRUD）
├── 编辑弹窗（基本信息 + 流程绑定 + 可见性 + 表单字段）
├── 分类管理（复用/增强现有 ServiceCategory）
└── 复用现有 Workflow Designer
```

### 核心流程

```
浏览服务 → 选择服务项 → 查看详情 → 填写表单 → 提交
                                                      ↓
                                ┌── 流程驱动 → WorkflowVersion + Ticket (Pipeline)
                                └── 快捷服务 → 轻量 Ticket（直接分派）
                                                      ↓
                                                我的工单中追踪
```

---

## 数据模型

### ServiceItem（新增模型）

```python
class ServiceItem(CoreModel):
    """服务项 — 服务目录的核心实体"""
    MODE_CHOICES = (
        ('flow', '流程驱动'),       # 绑定 Workflow，走完整 Pipeline
        ('lightweight', '快捷服务'), # 不绑 Workflow，直接分派
    )
    name = models.CharField(max_length=128, verbose_name="服务名称")
    description = models.TextField(blank=True, default='', verbose_name="服务描述")
    icon = models.CharField(max_length=64, null=True, blank=True, verbose_name="图标 emoji")
    cover_image = models.CharField(max_length=256, null=True, blank=True, verbose_name="封面图 URL")

    category = models.ForeignKey(
        'itsm.ServiceCategory', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_items', verbose_name="服务分类"
    )

    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default='flow', verbose_name="服务模式")
    workflow = models.ForeignKey(
        'itsm.Workflow', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="绑定流程（流程驱动模式必选）"
    )

    form_fields = models.JSONField(default=list, verbose_name="自定义表单字段定义")

    sla_policy = models.ForeignKey(
        'itsm.SlaPolicy', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="SLA 策略"
    )

    visible_to = models.CharField(
        max_length=64, default='all',
        choices=(('all', '全员'), ('role', '指定角色'), ('user', '指定用户')),
        verbose_name="可见范围"
    )
    visible_roles = models.JSONField(default=list, verbose_name="可见角色列表")
    visible_users = models.JSONField(default=list, verbose_name="可见用户列表")

    default_assignee_type = models.CharField(
        max_length=32, blank=True, default='', verbose_name="快捷服务分派方式"
    )
    default_assignee = models.CharField(
        max_length=128, blank=True, default='', verbose_name="快捷服务默认处理人"
    )

    expected_duration = models.CharField(max_length=64, blank=True, default='', verbose_name="预计时长")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
```

### 关联关系

| 关系 | 类型 | 说明 |
|---|---|---|
| ServiceItem → ServiceCategory | N:1 | 每个服务项归属一个分类 |
| ServiceItem → Workflow | N:1 | 可选绑定，多个服务可共享同一 Workflow |
| ServiceItem → Ticket | 1:N | 用户提交服务申请时创建工单 |
| ServiceItem → SlaPolicy | N:1 | 可选绑定 SLA 策略 |

### 设计决策说明

**为什么 form_fields 不直接复用 Workflow 的 Field？**
- ServiceItem 的字段是"申请表单"（用户填写的），Workflow 的字段是"节点表单"（审批人填写的）
- 两者用途不同，可能同时存在。服务项字段合并到提单节点的字段中
- 保持独立让后续可以扩展服务项专属的字段验证逻辑

**为什么 visible_to 用简单角色模型而非完整 IAM？**
- 初期需求是控制"谁可以看到这个服务"，不需要完整的权限矩阵
- 后续可以迭代对接 IAM 的细粒度权限

---

## 后端实现

### 新增文件

| 文件 | 内容 |
|---|---|
| `backend/itsm/models/service_item.py` | ServiceItem 模型定义 |
| `backend/itsm/serializers/service_item.py` | ServiceItem 序列化器 |
| `backend/itsm/views/service_item.py` | ServiceItemViewSet + submit 动作 |

### 修改文件

| 文件 | 变更 |
|---|---|
| `backend/itsm/models/__init__.py` | 导出 ServiceItem |
| `backend/itsm/urls.py` | 注册 `service-items` 路由 |
| `backend/itsm/views/ticket_views.py` | 支持从 ServiceItem 创建工单 |
| `backend/itsm/services/workflow_builder.py` | 合并 ServiceItem 表单字段到提单节点 |

### API 端点

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/itsm/service-items/` | 登录用户 | 服务项列表（按可见性过滤） |
| GET | `/api/itsm/service-items/:id/` | 登录用户 | 服务项详情 |
| POST | `/api/itsm/service-items/` | 管理员 | 创建服务项 |
| PATCH | `/api/itsm/service-items/:id/` | 管理员 | 更新服务项 |
| DELETE | `/api/itsm/service-items/:id/` | 管理员 | 删除服务项 |
| POST | `/api/itsm/service-items/:id/submit/` | 登录用户 | 提交服务申请 |

### 提交申请逻辑（submit action）

```
def submit(request, pk):
    service_item = get_object_or_404(ServiceItem, pk=pk, is_active=True)
    form_data = request.data.get('form_data', {})

    # 1. 校验表单（可选验证）
    validate_form_fields(service_item.form_fields, form_data)

    if service_item.mode == 'flow':
        # 2a. 流程驱动模式
        workflow = service_item.workflow
        version = workflow.create_version(operator=request.user)
        ticket = Ticket.objects.create(
            workflow_version=version,
            itsm_type=workflow.itsm_type,
            title=form_data.get('title', service_item.name),
            meta={'service_item_id': service_item.id, 'form_data': form_data},
            ...
        )
        submit_ticket(ticket.id)  # 启动 Pipeline
    else:
        # 2b. 快捷服务模式
        ticket = Ticket.objects.create(
            current_status='assigned',
            meta={'service_item_id': service_item.id, 'form_data': form_data, 'is_lightweight': True},
            ...
        )
        # 直接分派
        assign_ticket(ticket, service_item.default_assignee)

    return Response({'ticket_id': ticket.id, 'sn': ticket.sn})
```

---

## 前端实现

### 新增文件

| 文件 | 内容 |
|---|---|
| `web/src/views/apps/itsm/catalog/ServiceMarket.vue` | 服务市场（浏览页面） |
| `web/src/views/apps/itsm/catalog/ServiceDetail.vue` | 服务详情（申请表单页面） |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 服务管理后台 |

### 修改文件

| 文件 | 变更 |
|---|---|
| `web/src/views/apps/itsm/index.vue` | 新增 `service-market` 和 `service-admin` 两个 Tab |
| `web/src/api/itsm/index.ts` | 新增 `serviceItemApi` 和 `SubmitServiceItem` |

### UI 设计

**服务市场：** 左侧分类树 + 右侧卡片网格。卡片显示图标、名称、描述、模式标签、预计时长。

**服务详情（申请表）：** 服务元信息头部 + 动态渲染的表单字段（标题、用途、规格等）+ 底部审核链路预览 + 提交按钮。

**服务管理后台：** 表格列表 + 顶部操作栏 + 编辑弹窗（基本信息、服务配置、可见性、表单字段）。

---

## 实施计划

### Phase 1：核心功能（3-4 天）

1. ServiceItem 模型 + 数据迁移
2. ServiceItem 序列化器
3. ServiceItemViewSet + submit action + 路由注册
4. 前端 API 层
5. 服务市场页面（分类树 + 卡片浏览）
6. 服务详情页（表单 + 提交）
7. ITSM 首页集成新 Tab

### Phase 2：管理后台（2-3 天）

8. 服务管理列表页 + 编辑弹窗
9. 分类管理增强（树形 CRUD）
10. 可见性控制对接 IAM

### Phase 3：增强（后续迭代）

- 服务申请量统计 + 热门服务排行
- 服务评价
- 服务项版本管理
- 服务 SLA 看板
- 服务依赖关系图

---

## 验证方式

1. **单元测试：** ServiceItem 模型创建、查询、可见性过滤
2. **集成测试：** 提交服务申请 → 验证 Ticket 创建成功、Pipeline 启动
3. **前端验证：** 服务市场浏览 → 选择服务 → 填表单 → 提交 → 在我的工单看到新工单
4. **权限验证：** 管理员能看到管理 Tab，普通用户看不到
