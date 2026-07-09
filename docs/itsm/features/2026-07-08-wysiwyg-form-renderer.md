# ITSM WYSIWYG 表单渲染器 + 服务目录提单流程

> 提交: a5c1083f | 日期: 2026-07-08
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

ITSM 流程设计器（`FormDesigner.vue`）支持拖拽式设计 15 种字段类型 + 网格布局 + 显示条件。但填单页面（`TicketDetail.vue`）只渲染 STRING/TEXT/SELECT 三种类型，其余回退到普通 input。设计器和填单器各自手写内联 `v-if` 渲染链，代码重复约 400 行但能力不对等。

同时，服务目录提单流程存在两个体验问题：
1. 用户看到的表单是 `ServiceItem.form_fields`（服务级覆盖字段），不是流程设计器中定义的节点字段
2. 提交后 Celery pipeline 异步执行，auto-complete 时序问题导致用户进入详情页仍看到"填单"节点

## 实现方案

### 核心架构：ItsmFormRenderer

新增 `web/src/components/ItsmFormRenderer/` 组件体系，三层结构：

```
ItsmFormField.vue          ← 单字段分发器，type → Tag 组件 (15 种)
  10 种简单字段复用 RenderForm/tags/
  5 种复杂字段新建 (Members, File, Richtext, Table, Section)

ItsmFormRenderer/index.vue ← 列表渲染器，v-for + flex-wrap 网格 + submit/cancel
  mode: 'fill' (可交互) | 'preview' (disabled) | 'design' (disabled + 操作按钮)

FormDesigner.vue           ← 设计模式: VueDraggable + ItsmFormField; 预览模式: ItsmFormRenderer
```

### 服务目录提单流程

```
ServiceDetail 加载:
  1. serviceItemApi.detail(id) → 获取服务项、workflow_id
  2. stateApi.list({ workflow, type: 'NORMAL' }) → 获取第一个 NORMAL 节点字段
  3. 合并 item.form_fields 覆盖 → nodeFormFields
  4. ItsmFormRenderer mode="fill" 渲染

提交:
  1. ItsmFormRenderer @submit → onSubmit(data)
  2. SubmitServiceItem API → _submit_flow()
     a. worklfow.create_version() → 冻结部署快照
     b. do_after_create() → TicketStatus(WAIT)
     c. do_in_state(state_id, form_data) → 同步完成第一个节点 (FINISHED)
     d. ITSMEngine.run() → 启动 pipeline
     e. poll for Schedule → Engine.activity_callback() → 推进 pipeline 过 CALLBACK
  3. 返回 ticket_id → router.push → TicketDetail
     → rebuildFlow() 读取 WorkflowVersion → 第一节点 FINISHED
     → summaryNode 显示已提交内容
     → 后续节点 (APPROVAL/SIGN) 正常显示
```

### 关键代码

**ItsmFormField — 15 种类型分发：**

```vue
<!-- ItsmFormField.vue 核心分发逻辑 -->
<component :is="tagComponent" v-bind="tagProps" v-model="val" />
```

类型映射：STRING→TagInput, TEXT→TagTextarea, INT→TagInt, DATE/DATETIME→TagDatetime,
SELECT→TagSelect, RADIO→TagRadio, CHECKBOX→TagCheckbox, MULTISELECT→TagSelect(multiple),
CASCADE→TagCascader, MEMBERS→MembersField, FILE→FileField, RICHTEXT→RichtextField,
TABLE→TableField, SECTION→SectionDivider

**后端同步 auto-complete + callback 推进：**

```python
# service_item.py _submit_flow()
# 1. 同步完成（不等 Celery）
ticket.do_in_state(first_normal_state_id, form_data, 'system')

# 2. 启动 pipeline → Celery 创建 CALLBACK Schedule
pipeline_id, tree = ITSMEngine(ticket).run(version)

# 3. poll Schedule → activity_callback() 推进 pipeline
node_id_map = (ticket.meta or {}).get('_pipeline_id_map', {})
activity_id = node_id_map.get(str(first_normal_state_key))
Engine.activity_callback(activity_id, {...})
```

**execute() 保护已完成的节点不被覆盖：**

```python
# itsm_fill execute()
existing = TicketStatus.objects.filter(ticket=ticket, state_id=state_id).first()
if existing and existing.status == 'FINISHED':
    return True  # 跳过 do_before_enter_state，等待 schedule() 完成
```

### 设计决策

- **为什么新增 ItsmFormRenderer 而不是改造 RenderForm** — 两套 Schema 不兼容（ITSM: `type: "STRING"` vs RenderForm: `type: "input"`）。新增组件改动最小、风险最低
- **为什么需要 ItsmFormField（单字段层）** — FormDesigner 设计模式用 VueDraggable 迭代字段，需要单字段渲染能力；ItsmFormRenderer 迭代列表，需要列表渲染能力。拆分单字段层让两者共享
- **为什么在 _submit_flow 同步完成 + poll callback** — bamboo-engine CALLBACK schedule 不会自动调用 schedule()，只在外部 callback 时触发。需要在 API 层主动触发以推进 pipeline
- **为什么 ticket.project 用请求上下文的 project_id** — 前端 `opsflowRequest` 拦截器按用户选定项目发送 `?project_id=X`，ticket 应归属用户当前工作上下文

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/components/ItsmFormRenderer/index.vue` | 列表渲染器 — v-for + grid + submit/cancel |
| `web/src/components/ItsmFormRenderer/ItsmFormField.vue` | 单字段分发器 — 15 种类型 → Tag 组件 |
| `web/src/components/ItsmFormRenderer/types.ts` | ItsmField 接口、layoutColMap |
| `web/src/views/apps/itsm/catalog/ServiceDetail.vue` | 服务目录提单 — 加载节点字段 + ItsmFormRenderer |
| `backend/itsm/views/service_item.py` | 同步 auto-complete + callback 推进 |
| `backend/itsm/pipeline_plugins/components.py` | execute() FINISHED 保护 |

### 关联文档

- 相关架构文档: [2026-07-07-tab-lazy-loading-refactor.md](../architecture/2026-07-07-tab-lazy-loading-refactor.md)
- 相关功能文档: [2026-07-07-hero-search-teleport.md](2026-07-07-hero-search-teleport.md)
