# FcDesigner 设置面板 + 预设联动 + 全屏拉伸

> 提交: a47ec942 | 日期: 2026-07-13
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

ITSM 表单设计器（`<fc-designer>`）在项目中使用后，需要以下增强：
1. **设计器设置面板** — 运行时控制 FcDesigner 各功能模块显隐（右侧面板、工具栏、菜单组、功能开关等）
2. **预设联动** — 设计器中 select/radio/checkbox 组件可直接调用预设管理中的选项数据
3. **全屏 + 拉伸** — 设计器支持全屏模式和自由拖拽调整高度

## 实现方案

### 核心架构

```
FcFormDesigner.vue (wrapper)
  ├── fc-designer (FcDesigner实例)
  │     ├── #handle slot → 全屏/取消/保存按钮
  │     └── :config="designerConfig" (reactive)
  ├── FcDesignerSettingsPanel.vue (左侧滑出面板)
  └── Resize handle (底部拖拽条)

fcExtensions.ts
  ├── designerConfig (reactive, 双层持久化 localStorage + DB)
  ├── FcDesignerSettings model (按Business级别)
  ├── MAKE_OPTIONS_RULE: 扩展 _optionType control面板
  │     ├── value=2: "从预设加载" 下拉 + TableOptions
  │     ├── value=4/5: 添加 placeholder 样例
  └── Custom DragRules (select/radio/checkbox)
        ├── hidden field: itsmPresetId (数据绑定)
        ├── watch: itsmPresetId → 加载预设数据
        └── Control panel: 表格配置内嵌 preset selector
```

### 关键代码

**设计器设置持久化** (`fcExtensions.ts`):
```ts
const STORAGE_KEY = 'fc_designer_settings'
const SHOW_KEYS = ['showConfig', 'showBaseForm', ...] // 20+ 开关

export const designerConfig = reactive<Config>({ ...DEFAULT_CONFIG })

export async function initDesignerSettings() {
  // 1. localStorage hit → instant load
  // 2. localStorage miss → fetch DB (resolved to business_id via project_id)
  // 3. DB miss → code defaults
}

export function saveDesignerSettings() {
  // Sync write localStorage + async PUT to /api/itsm/fc-designer-settings/
}
```

**菜单设置 — 两层控制** (`FcDesignerSettingsPanel.vue`):
```ts
// Master: hiddenMenu (adds/removes group name)
function toggleMenu(group, visible) { ... }

// Sub-component: hiddenItem (adds/removes component name)
function toggleItem(name, visible) { ... }
```

**预设联动 — DragRule watch** (`fcExtensions.ts`):
```ts
function onPresetWatch({ rule, value }) {
  const opts = presetDataMap.get(Number(value))
  rule.options = data
  rule.props.options = data
  // setRule + triggerActive to refresh canvas + panel
  const rules = d.getRule()
  d.setRule(rules)
  d.triggerActive(activeRule)
}
```

**Backend: FcDesignerSettings model**:
```python
class FcDesignerSettings(CoreModel):
    business = FK('iam.Business')  # per-business, not per-user
    value = JSONField(default=dict)
    # unique_together: (business,)
```

**API resolves business_id from project_id**:
```python
class FcDesignerSettingsView(APIView):
    def _resolve_business(self, project_id):
        p = Project.objects.only('business_id').get(id=project_id)
        return str(p.business_id) if p.business_id else None
```

### 数据流

```
FcFormDesigner mount:
  initDesignerSettings() → localStorage/DB → designerConfig (reactive)
  presetApi.list({preset_type:'options'}) → presetOptionList + presetDataMap

User opens settings:
  齿轮按钮 → FcDesignerSettingsPanel (el-drawer)
  toggle switch → designerConfig[key] = ! → saveDesignerSettings()
    → localStorage (sync) + PUT /api/itsm/fc-designer-settings/ (async)

User selects preset:
  _optionType=2 → control panel shows "从预设加载" dropdown
  select preset → field binds to itsmPresetId → watch fires
  onPresetWatch → load options → setRule + triggerActive → panel reopens with data
```

### 设计决策

- **为什么用 `reactive()` + `setRule` + `triggerActive`** — `componentRule` 只能追加字段无法替换 `_optionType` control；`on.change` 在 control 面板内不可靠。DragRule `watch` 是 FcDesigner 原生支持的规则变更监听机制
- **为什么设置存到 Business 而非 User** — 设计器设置是业务级别偏好，同业务线所有项目和用户应共享同一套配置
- **为什么 localStorage + DB 双层** — localStorage 提供毫秒级快速启动，DB 提供跨设备和跨浏览器的持久化源
- **为什么 preset 选择器放 control 面板而非独立字段** — 避免属性面板字段冗余，将 preset 自然整合到 options 配置流程中

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/.../designer/FcDesignerSettingsPanel.vue` | 20+开关设置面板，localStorage/DB持久化 |
| `web/.../designer/fcExtensions.ts` | 核心配置：reactive config, DragRules, preset logic |
| `web/.../designer/FcFormDesigner.vue` | Designer wrapper: fullscreen, resize, preset loading |
| `backend/itsm/models/fc_designer.py` | FcDesignerSettings model (per-business) |
| `backend/itsm/views/fc_designer_settings.py` | GET/PUT API, project_id→business_id resolver |
| `backend/itsm/urls.py` | `/api/itsm/fc-designer-settings/` 路由 |

## 使用方式

1. 打开 ITSM 表单设计器 → 默认全屏
2. 点击左下齿轮 → 左侧滑出设置面板 → 调整开关
3. 选项类型选"表格配置" → "从预设加载"下拉 → 选择预设 → 选项自动填充
4. 右上角全屏按钮 → 切换全屏/非全屏
5. 底部拖拽条 → 自由调整高度
