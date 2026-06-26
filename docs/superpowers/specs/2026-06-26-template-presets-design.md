# Template Presets — 模板预设快速创建

> 日期: 2026-06-26 | 类型: 功能设计 | 涉及 App: opsflow

## 目标

在 CreateTemplateWizard 的 AI 对话输入框下方提供预设提示词标签，用户点击即可填充提示词快速生成流程模板。支持 5 种机制 10 个场景。管理员可通过 Django Admin 增删改。

## 设计

### Model

```python
class TemplatePreset(models.Model):
    name = CharField(max_length=64)
    name_en = CharField(max_length=128, blank=True)
    icon = CharField(max_length=8)  # emoji
    prompt = TextField()
    prompt_en = TextField(blank=True)
    category = CharField(max_length=64, blank=True)  # serial, loop, parallel, gateway, loopback
    sort_order = IntegerField(default=0)
    is_active = BooleanField(default=True)
```

### API

`GET /api/opsflow/templates/presets/` → 返回所有 is_active=True 的 preset，按 sort_order 排序。

### Seed Data（10 个预设）

1. 数据备份+校验 (💾 serial)
2. 安全基线巡检 (🛡️ serial)
3. 磁盘空间告警 (💿 exclusive_gateway)
4. 服务健康+自愈 (🏥 exclusive_gateway)
5. 多机房并行部署 (🌐 parallel)
6. 并行重启+验证 (⏯ parallel)
7. ECS 批量创建 (⚡ loop_a)
8. 批量磁盘巡检 (🔍 loop_a)
9. 补丁滚动部署 (🔧 loop_b)
10. ECS 创建+等待就绪 (⏳ loop_b)

### 前端

CreateTemplateWizard 在 AI 输入框下方加载 preset 列表，渲染为横向排列的标签。点击标签填入输入框。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/models/template.py` | TemplatePreset 模型 |
| `backend/opsflow/views/template_views.py` | presets 端点 |
| `web/.../CreateTemplateWizard.vue` | 预设标签 UI |
