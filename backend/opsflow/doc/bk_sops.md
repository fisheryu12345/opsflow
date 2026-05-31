# bk_sops 可借鉴实现分析

> 分析日期: 2026-05-31
> 来源: bk_sops humming_bird 版本 (`bk_sops/bk-sops-release_humming_bird/`)

---

## 一、指令调度模式 (Dispatcher Pattern) — 高优先级

**源文件**: `gcloud/taskflow3/domains/dispatchers/{base,task,node}.py`

### 架构

```
EngineCommandDispatcher (基类)
  ├── TaskCommandDispatcher    — 任务级操作
  └── NodeCommandDispatcher   — 节点级操作
```

### 核心设计

- **TaskCommandDispatcher**: start / pause / resume / revoke / set_task_constants / get_task_status
- **NodeCommandDispatcher**: retry / skip / callback / forced_fail / pause_subproc / retry_subprocess / get_node_data / get_node_detail
- **双引擎兼容**: `getattr(self, f"{command}_v{engine_ver}")` 分发到 v1 (pipeline) 或 v2 (bamboo-engine) 实现
- **统一返回值**: `@ensure_return_is_dict` 装饰器 + `err_code` 枚举标准化  `{result, message, code, data}`

### 借鉴建议

OPSflow 当前缺少结构化节点操作层。可以借鉴此模式:

1. 定义 `EngineCommandDispatcher` 基类，统一错误码和返回值
2. `TaskCommandDispatcher` 封装任务生命周期 (启动/暂停/恢复/撤销)
3. `NodeCommandDispatcher` 封装节点操作 (重试/跳过/回调/强制失败)
4. 便于双引擎共存过渡

### 关键代码段

```python
def dispatch(self, command: str, operator: str) -> dict:
    if command not in self.TASK_COMMANDS:
        return {"result": False, "message": "invalid command"}
    return getattr(self, "{}_{}".format(command, self.engine_ver))(operator)
```

```python
def ensure_return_is_dict(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        dict_result = {
            "result": result.result,
            "message": result.message,
            "code": err_code.SUCCESS.code if result.result else err_code.UNKNOWN_ERROR.code,
        }
        if isinstance(result, EngineAPIResult) and result.exc:
            dict_result["message"] = "{}: {}".format(result.message, result.exc_trace)
        return dict_result
    return wrapper
```

---

## 二、自动重试策略 (Auto-Retry) — 高优先级

**源文件**: `gcloud/taskflow3/domains/auto_retry.py`

### 核心设计

- 从 `pipeline_tree` 递归遍历活动节点，读取 `auto_retry.enable/times/interval` 配置
- `bulk_create` 批量创建 `AutoRetryNodeStrategy` 记录，支持上限保护
- 状态树格式化时检测自动重试次数 (通过 `fetch_node_id__auto_retry_info_map`)

### 借鉴建议

OPSflow 可为关键节点（如交易执行、数据同步）添加类似的重试策略配置。

### 关键代码段

```python
class AutoRetryNodeStrategyCreator:
    def batch_create_strategy(self, pipeline_tree: dict):
        def _initiate_strategy(pipeline_tree: dict):
            strategies = []
            for act_id, act in pipeline_tree[PE.activities].items():
                if act["type"] == PE.SubProcess:
                    strategies.extend(_initiate_strategy(act[PE.pipeline]))
                else:
                    auto_retry = act.get("auto_retry", {})
                    enable = auto_retry.get("enable")
                    if not enable:
                        continue
                    max_retry_times = min(
                        abs(int(auto_retry.get("times", default))),
                        MAX_TIMES,
                    )
                    interval = min(
                        abs(int(auto_retry.get("interval", 0))),
                        MAX_INTERVAL,
                    )
                    strategies.append(AutoRetryNodeStrategy(...))
            return strategies
        AutoRetryNodeStrategy.objects.bulk_create(strategies)
```

---

## 三、Webhook 回调系统 — 高优先级

**源文件**: `gcloud/utils/webhook.py`, `gcloud/taskflow3/signals/handlers.py`, `gcloud/taskflow3/domains/callback.py`

### 核心设计

- **事件驱动**: 通过 Django Signal (`pipeline_end` / `activity_failed`) 触发
- **双模式**: `_url_callback()` HTTP POST 远程回调 vs `_subprocess_callback()` 子流程联动
- **幂等保护**: Redis 分布式锁防重复回调 + 版本号校验防过期回调
- **前端 UI**: `HttpCallback.vue` 配置 URL、认证方式、重试参数
- **持久化**: `TaskCallBackRecord` 模型记录每次回调请求、响应、状态

### 借鉴建议

OPSflow 缺少此机制，对交易信号触发外部通知、策略执行结果推送等场景可直接参考。

### 关键代码段

```python
class TaskCallBacker:
    def callback(self):
        if self.record.url:
            return self._url_callback()
        return self._subprocess_callback()

    def _subprocess_callback(self):
        with redis_lock(key=f"sc_{node_id}_{version}") as (ok, err):
            if not ok:
                return None  # 忽略重复回调
            node_state = runtime.get_state(node_id)
            if node_state.version != version:
                raise ValidationError("version mismatch")
            # 子流程完成后回调父流程继续执行

    def _url_callback(self):
        with redis_lock(key=f"url_callback_lock_{self.task_id}") as (ok, err):
            response = requests.post(url, json=self.extra_info)
            response.raise_for_status()
```

---

## 四、插件退役管理 (Plugin Deprecation) — 中优先级

**源文件**: `pipeline_web/plugin_management/`

### 核心设计

- `DeprecatedPlugin` 模型记录 `{code, version, phase, type}` 三元组
- `find_deprecated_plugins_in_unfold_tree()`: 先展开子流程再检测
- `find_deprecated_plugins_in_spread_tree()`: 在已展开树中递归检测
- 区分 `PLUGIN_TYPE_COMPONENT` 和 `PLUGIN_TYPE_VARIABLE`

### 借鉴建议

OPSflow 未来升级组件时可以参考此模式安全处理存量数据。

### 关键代码段

```python
def find_deprecated_plugins_in_spread_tree(tree, phases=None):
    deprecated_plugins = DeprecatedPlugin.objects.filter(phase__in=phases)
    # 按 code_version 构建集合加速匹配
    for plugin in deprecated_plugins:
        plugin_type_map[plugin.type].add(f"{plugin.code}_{plugin.version}")
    # 递归遍历树中的所有活动和变量
    return {"found": bool(...), "plugins": {"activities": [...], "variables": [...]}}
```

---

## 五、管道预览与清理 (Preview & Clean) — 中优先级

**源文件**: `pipeline_web/preview_base.py`, `pipeline_web/parser/clean.py`, `gcloud/taskflow3/apis/drf/viewsets/preview_task_tree.py`

### 核心设计

- **执行方案预览**: 根据 `scheme_id_list` 排除未被选择的节点，保留不可选节点 (`not optional`)
- **无用网关清理**: `_remove_useless_parallel()` 删除空并行网关对 (parallel → converge 无中间节点)
- **无用常量清理**: `_remove_useless_constants()` 递归追踪变量引用，只保留被引用的常量
- **节点属性分离**: `PipelineWebTreeCleaner` 支持 labels 等上层属性独立存储/还原，ID 映射后重新挂载

### 借鉴建议

OPSflow 的模板预览和常量管理系统可以借鉴这些清理策略，特别是节点属性分离存储机制。

### 关键代码段

```python
class PipelineWebTreeCleaner:
    def clean(self, pipeline_tree, with_subprocess=False):
        """清理 pipeline_tree 的节点部分上层属性，独立存储"""
        nodes_attr = {}
        all_nodes = get_all_nodes(pipeline_tree)
        for node_id, node in all_nodes.items():
            attr = node.pop(PWE.labels, None)
            if attr:
                nodes_attr.setdefault(node_id, {}).update({PWE.labels: attr})

    def to_web(self, nodes_attr, pipeline_tree):
        """将独立存储的节点属性还原到任务树中"""
        all_nodes = get_all_nodes(pipeline_tree, with_subprocess)
        for node_id, node in all_nodes.items():
            node.update(nodes_attr.get(node_id, {}))
```

```python
class PipelineTemplateWebPreviewer:
    @staticmethod
    def preview_pipeline_tree_exclude_task_nodes(pipeline_tree, exclude_task_nodes_id):
        """根据执行方案排除节点，返回预览树"""
        # 跳过被排除的节点 (重连上下游)
        for act_id in exclude_task_nodes_id:
            act = pipeline_tree[PE.activities].pop(act_id)
            _ignore_act(act, locations, lines, pipeline_tree)
        # 删除空的并行网关
        _remove_useless_parallel(pipeline_tree, lines, locations)
        # 清理未引用常量
        _remove_useless_constants(exclude_task_nodes_id, pipeline_tree)
```

---

## 六、前端 SVG 画布 — 可参考

**源目录**: `frontend/desktop/src/components/common/TemplateCanvas/`

### 特点

- 使用**纯 SVG**（非 X6 / G6 等第三方库），手写节点渲染、连线、拖放
- 按类型拆分的 NodeTemplate: `TaskNode` / `BranchGateway` / `ParallelGateway` / `ConvergeGateway` / `Subflow`
- 完整工具链: 左侧 PalettePanel 拖拽面板 → 画布编排 → 右侧 NodeConfig 配置面板
- 全局变量管理: 引用追踪、克隆、预览、系统变量

### OPSflow 现状

已使用 X6 作为图编辑引擎，但以下场景可参考:
- **轻量级只读预览** — SVG 绘制比 X6 实例化更轻
- **子流程节点显示** — 内嵌显示子流程缩略图

---

## 七、Pipeline 格式转换与验证 — 已有基础

**源文件**: `pipeline_web/parser/format.py`, `pipeline_web/parser/validator.py`

### 核心设计

- `format_web_data_to_pipeline()`: 前端树 → 标准管道树
- `classify_constants()`: 分离 `data_inputs` 和 `acts_outputs`
- `validate_web_pipeline_tree()`: 三层验证
  - JSON Schema 结构验证 (`Draft4Validator`)
  - constants key pattern 正则校验
  - 环检测 (可容忍自环)

### 借鉴建议

OPSflow 核心已做格式转换，但缺 JSON Schema 层级的输入验证，可补充。

```python
def validate_web_pipeline_tree(web_pipeline_tree):
    # 1. JSON Schema 校验
    valid = Draft4Validator(WEB_PIPELINE_SCHEMA)
    # 2. Key pattern 校验
    for key, const in constants.items():
        if not KEY_PATTERN_RE.match(key):
            errors.append(f"invalid key: {key}")
    # 3. 环检测 + 常量交叉验证
    validate_pipeline_tree_constants(constants)
    validate_pipeline_tree(web_pipeline_tree, cycle_tolerate=True)
```

---

## 八、NodeAttr 属性注册模式 — 参考

**源文件**: `pipeline_web/core/abstract.py`

### 核心设计

```python
class NodeAttr(metaclass=NodeAttrMeta):
    @classmethod
    def register_template_attr(cls, key, attr):
        """注册模板级节点属性"""
    @classmethod
    def register_instance_attr(cls, key, attr):
        """注册实例级节点属性"""

# 通过元类自动收集所有子类
class MyCustomAttr(NodeAttr):
    code = "my_attr"
    type = "string"
    default = ""
```

### 借鉴建议

适合 OPSflow 组件系统设计，让第三方插件能注册自己的属性。
