# Plugin 动态热加载 & 中英文双语言支持

> 提交: TBD | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

原有插件系统在 `Django AppConfig.ready()` 启动时通过 `pkgutil.walk_packages` 一次性扫描注册到全局 `PLUGIN_REGISTRY`，新增 .py 文件必须重启服务。

同时所有插件名称、描述、表单字段标签均为中文硬编码，前端切换语言后无法展示英文。

## 设计方案

### 动态热加载

采用 **文件快照 + 显式触发** 方案，无后台轮询线程：

```
PluginLoader (loader.py)
├── _snapshots: Dict[str, Tuple[float, int]]  # abs_path → (mtime, size)
├── _revision: int                             # 每次 scan() 发现新插件 +1
├── scan() → int                              # 返回本次新增数量
│   ├── rglob('*.py') 遍历 plugins/ 目录
│   ├── 跳过 __init__.py 和 __pycache__
│   ├── 对比 _snapshots：已存在 → 跳过（不支持更新已有模块）
│   ├── 新文件 → _path_to_module() 转模块路径 → importlib.import_module()
│   └── _register_from_module() 查找 BasePlugin 子类 → 写入 PLUGIN_REGISTRY
├── get_revision() → int
└── _path_to_module(file_path) → str
    # e.g. opsflow/plugins/ansible/shell.py → opsflow.plugins.ansible.shell
```

**触发入口：**
- 前端：`POST /api/opsflow/plugins/reload/` → `refresh_plugins()` → `loader.scan()` + `sync_plugin_meta_to_db()`
- CLI：`python manage.py scan_plugins` → 同上

**关键约束：**
- 原地修改 `registry.PLUGIN_REGISTRY` dict（不变更对象引用），所有 `from registry import PLUGIN_REGISTRY` 的消费者（`safety_guard.py`、`plugin_service_adapter.py`）立即可见
- 不支持更新/删除已有插件（`importlib.reload` 有副作用），仅处理新增
- `register_from_module` 按 `(code, version)` 去重，防止重复注册

### 中英文双语言

**后端数据流：**

```
Python 插件类 → sync_plugin_meta_to_db() → PluginMeta (MySQL)
├── name / name_en / description / description_en
└── form_schema: JSONField
    [{"tag_code": "smtp_host", "name": "SMTP 服务器", "name_en": "SMTP Server", ...}]
```

**BasePlugin 变更** (`backend/opsflow/plugins/base.py:8:26`):
```python
class BasePlugin:
    name: str = ""       # 中文
    name_en: str = ""    # 英文（可选）
    description: str = ""
    description_en: str = ""  # 英文（可选）
```

**FormItem 变更** (`backend/opsflow/schema/form_schema.py:38`):
```python
class FormItem(BaseModel):
    name: str             # 中文标签
    name_en: str = ""     # 英文标签（可选）
```

**同步保护逻辑** (`backend/opsflow/plugins/registry.py:128-144`):
```python
cls_name_en = getattr(cls, 'name_en', None) or ''
if cls_name_en:
    defaults['name_en'] = cls_name_en  # 仅插件类有定义时才覆盖 DB
```
旧插件类没有定义 `name_en`，backfill 写入 DB 的值不会在启动时被冲掉。

**旧插件补齐** (`backend/opsflow/management/commands/backfill_plugin_en.py`):
一次性命令，遍历所有 `PluginMeta` 记录，对 `name_en` 为空的行从 code 自动生成英文标题：
```python
# "esxi_power_on" → "ESXi Power On"（含缩写识别）
def _snake_to_title(text: str) -> str:
    parts = text.replace('-', '_').split('_')
    return ' '.join(_ABBR_MAP.get(p.lower(), p.capitalize()) for p in parts)
```
共补齐 55 个旧插件。

**前端实现**：
- API 层：`plugins.ts` 中的 `withLang()` 已删除，API 始终返回 `name` + `name_en`
- Composables：`usePluginName.ts` 已删除（过于多余），改为各组件内联：
```ts
const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))
```
- 模板：`{{ isEn && plugin.name_en ? plugin.name_en : plugin.name }}`
- PropertyPanel：加载 `form_schema` 时将 `name_en` 提升到 `name`
- PluginPickerDialog：搜索支持英文名 `displayName.toLowerCase().includes(q)`

### API 精简重构

`plugin_views.py` 从 357 行精简到 248 行：
- 删除 `_ABBR_MAP`（30 行缩写映射表）
- 删除 `_snake_to_title()`（20 行）
- 删除 `_resolve_lang()`（20 行后处理函数）
- 删除 `_fmt()` / `_fmt_detail()` / `_fmt_form_schema()`（三个 helper）
- 所有端点直接从 `PluginMeta` 读取 `name` + `name_en` 并返回
- `?lang=en` 参数不再需要（仍接受但不影响）

### 新增插件原子

**ESXi 系列**（6 个，`backend/opsflow/plugins/esxi/`）：

| 文件 | code | name_en | 说明 |
|------|------|---------|------|
| `create_snapshot.py` | `esxi_create_snapshot` | Create Snapshot | 创建快照（含内存/静默选项） |
| `revert_snapshot.py` | `esxi_revert_snapshot` | Revert to Snapshot | 恢复快照 |
| `remove_snapshot.py` | `esxi_remove_snapshot` | Remove Snapshot | 删除快照 |
| `attach_disk.py` | `esxi_attach_disk` | Attach Disk | 挂载磁盘（厚/精简/快速零置备） |
| `reconfigure_vm.py` | `esxi_reconfigure_vm` | Reconfigure VM | 修改 CPU/内存 |
| `reboot.py` | `esxi_reboot` | Reboot VM | 重启（软重启/硬重置） |

每个原子配置了 `name_en`、`description_en`、表单字段的 `name_en`，以及 `rollback()`、`get_output_schema()`。

**邮件通知**（`backend/opsflow/plugins/common/send_email.py`）：
- 支持 SMTP_SSL / STARTTLS 两种加密方式
- 支持纯文本和 HTML 正文
- 支持抄送

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/plugins/loader.py` | PluginLoader 热加载引擎 |
| `backend/opsflow/plugins/base.py` | BasePlugin 新增 name_en/description_en |
| `backend/opsflow/schema/form_schema.py` | FormItem 新增 name_en |
| `backend/opsflow/plugins/registry.py` | sync_plugin_meta_to_db 保护逻辑 |
| `backend/opsflow/views/plugin_views.py` | API 简化，去掉 _resolve_lang 等函数 |
| `backend/opsflow/management/commands/scan_plugins.py` | 热加载触发管理命令 |
| `backend/opsflow/management/commands/backfill_plugin_en.py` | 旧插件英文名补齐 |
| `backend/opsflow/plugins/common/send_email.py` | 新增邮件通知原子 |
| `backend/opsflow/plugins/esxi/*.py` | 新增 6 个 ESXi 原子 |
| `web/src/i18n/pages/opsflow/zh-cn.ts` | 扫描插件按钮 i18n key |
| `web/src/i18n/pages/opsflow/en.ts` | 英文翻译 key |

## 使用方式

- 新增插件：放 .py 文件到 `backend/opsflow/plugins/<group>/` → 打开前端插件对话框 → 点击"扫描插件"
- 语言切换：右上角切换语言 → 插件名/描述/表单字段自动切换

### 关联文档

- 相关架构文档: [plugin-view-simplify](architecture/2026-06-12-plugin-view-simplify-refactor.md)
- 相关配置文件: [backfill-plugin-en](config/2026-06-12-backfill-plugin-en-config.md)
