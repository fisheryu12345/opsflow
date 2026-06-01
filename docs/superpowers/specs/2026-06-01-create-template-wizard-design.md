# Create Template Wizard — 设计文档

## 背景

当前 opsflow 创建新模板只能通过模板管理页的弹窗（名称/分类/描述），或者在画布页面直接进入空白画布。缺少一个系统化的新建引导流程，分类也没有规范化管理。

参考 SubmitWizardDialog（执行提交向导）的交互模式，新建一个 CreateTemplateWizard 组件，引导用户逐步完成模板创建。

## 技术方案

### 组件架构

新建 `web/src/views/apps/opsflow/components/CreateTemplateWizard.vue`

- 基于 `el-dialog` + `el-steps` 的向导式对话框
- 与 `SubmitWizardDialog` 保持一致的 UI 风格（尺寸、步骤条、底部导航）
- 宽度 680px，顶部对齐

### 触发入口

画布页（`opsflow/index.vue`）工具栏 "New Template" 按钮 → 打开 Wizard Dialog

### Wizard 流程（2 步）

```
Step 1: 基本信息 → Step 2: 创建方式 → 创建 → 自动加载到画布
```

---

## Step 1：基本信息

| 字段 | 类型 | 必填 | 数据来源 |
|------|------|------|---------|
| 模板名称 | `el-input` | ✅ | 用户输入，最大 200 字符 |
| 分类 | `el-select` | ✅ | `GET /api/opsflow/template-categories/` |
| 描述 | `el-textarea` | ❌ | 用户输入，最大 500 字符 |

### 分类管理

**方案：方案 B — 可配置模型**

新建 `TemplateCategory` 模型：

```python
class TemplateCategory(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name="分类名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="分类编码")
    icon = models.CharField(max_length=64, blank=True, verbose_name="图标")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="启用")
```

新建 `TemplateCategoryViewSet`：
- `list` / `retrieve` — 所有人可读（登录用户）
- `create` / `update` / `destroy` — 仅 superuser
- 注册路由 `template-categories/`
- 返回带 `code`/`name`/`icon` 的列表，前端 `el-option :key="cat.code" :label="cat.name"`

**种子数据（18 个分类）：**

| code | name | icon |
|------|------|------|
| server | 🖥️ 服务器管理 | server |
| virtualization | 🎛️ 虚拟化 | virtualization |
| storage | 📦 存储管理 | storage |
| network | 🌐 网络管理 | network |
| security | 🔐 安全运维 | security |
| database | 🗄️ 数据库运维 | database |
| deploy | 🚀 应用发布 | deploy |
| backup | 🔄 备份与恢复 | backup |
| monitoring | 📊 监控告警 | monitoring |
| inspection | 🔧 巡检与合规 | inspection |
| itsm | 📋 IT服务管理 | itsm |
| automation | 🤖 自动化作业 | automation |
| notification | 🔔 通知告警 | notification |
| integration | 🔗 集成与API | integration |
| maintenance | 🛠️ 系统维护 | maintenance |
| container | 📦 容器与K8s | container |
| infrastructure | 🏗️ 基础设施 | infrastructure |
| other | ⚙️ 其他 | other |

**FlowTemplate 现有 `category` 字段**保持不变（`CharField(max_length=64)`），存分类 code。已有分类数据兼容。

---

## Step 2：创建方式

三种创建方式，radio card 样式选择：

### 2a. 空白创建
- 创建空模板（`is_draft=True`）
- 调用 `POST /api/opsflow/templates/`
- 创建后直接跳转到画布页，加载空白 start→end 流程

### 2b. AI 生成
- 文本域让用户输入自然语言描述
- 调用 `POST /api/opsflow/templates/create_from_ai/`
- 创建后跳转到画布页，加载 AI 生成的 pipeline

### 2c. 从已有模板克隆
- 下拉选择器列出当前项目 + 公共模板
- 选择后用 `GET /api/opsflow/templates/{id}/export/` 获取模板数据
- 调用 `POST /api/opsflow/templates/import_template/` 创建副本
- 创建后跳转到画布页

---

## 数据流

```
点击 New Template (DesignCanvas.vue)
  → emit('newTemplate')
  → opsflow/index.vue 显示 CreateTemplateWizard

Step 1 完成 → Step 2 选择创建方式 → 确认
  │
  ├─ 空白: POST /templates/ → 返回 {id}
  ├─ AI: POST /templates/create_from_ai/ → 返回 {id, pipeline_tree}
  └─ 克隆: GET /templates/{id}/export/ → POST /templates/import_template/ → 返回 {id}

  → opsflowStore.setCurrentTemplate({id, ...})
  → router.push('/opsflow')
  → designCanvasRef.loadPipeline(pipeline_tree)
```

---

## 后端变更

| 文件 | 变更 |
|------|------|
| `backend/opsflow/models.py` 或 `models/template.py` | 新增 `TemplateCategory` 模型 |
| `backend/opsflow/migrations/` | 自动生成 migration |
| `backend/opsflow/views/template_category_views.py` | 新增 ViewSet |
| `backend/opsflow/serializers.py` | 新增 `TemplateCategorySerializer` |
| `backend/opsflow/urls.py` | 注册 `template-categories/` 路由 |
| `backend/opsflow/management/commands/seed_template_categories.py` | 种子数据命令 |

## 前端变更

| 文件 | 变更 |
|------|------|
| `web/src/views/apps/opsflow/components/CreateTemplateWizard.vue` | 新建向导组件 |
| `web/src/views/apps/opsflow/index.vue` | 集成 Wizard，处理创建完成事件 |
| `web/src/views/apps/opsflow/components/DesignCanvas.vue` | 修改 "New Template" 按钮 emit newTemplate |
| `web/src/api/opsflow/template-categories.ts` | 新建 API 模块 |

## 验证方案

1. 点击 "New Template" 按钮 → 弹出 2 步向导
2. Step 1 不填名称 → Continue 禁用 ✅
3. Step 1 填写后进入 Step 2 → 三种创建方式可选 ✅
4. 空白创建 → 跳转画布，显示空 start→end ✅
5. AI 生成 → 输入描述 → 调用 API → 加载到画布 ✅
6. 克隆 → 显示模板列表（含公共模板）→ 创建副本 → 加载到画布 ✅
7. 分类 API → 返回 18 个分类 ✅
8. superuser 可管理分类，普通用户只读 ✅
