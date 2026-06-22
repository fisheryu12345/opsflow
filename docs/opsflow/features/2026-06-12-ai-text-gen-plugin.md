# AI 文本生成插件 / AI Text Generation Atom

> 提交: df82a1c9 | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

OpsFlow 已有 40+ 标准插件覆盖了 shell、文件操作、部署、监控、CMDB 等场景，但缺少 AI 能力。新增 `ai_text_gen` 插件，允许流程中的节点调用 LLM（DeepSeek）生成文本内容，实现智能化的文本生成、分析、总结等场景。

## 实现方案

### 核心架构

新增一个标准 `BasePlugin` 子类，放在 `opsflow/plugins/ai/` 新分组下，复用现有的插件发现/注册/执行全链路：

```
用户配置 → FormItem(system_prompt, prompt, temperature, max_tokens)
                ↓
PluginLoader 自动发现 → AiTextGenPlugin 注册到 PLUGIN_REGISTRY
                ↓
PluginService.execute() → 路由到 AiTextGenPlugin.execute()
                ↓
_get_llm_client() → OpenAI(DeepSeek) → chat.completions.create()
                ↓
返回 {"text": "...", "model": "...", "input_tokens": N, ...}
```

### 关键代码

**插件类结构** (`backend/opsflow/plugins/ai/ai_text_gen.py`):

```python
class AiTextGenPlugin(BasePlugin):
    code = "ai_text_gen"
    name = "AI 文本生成"
    group = "AI"       # 全新分组
    risk_level = "low"
    icon = "🤖"
    color = "#6366f1"
```

**执行逻辑** — 同步调用 DeepSeek API，复用已有的 OPSAGENT 配置：

```python
def execute(self, prompt, system_prompt="", temperature=0.3, max_tokens=2048, **kwargs):
    # 1. 类型安全转换（bamboo-engine 所有 inputs 为字符串）
    temperature = float(temperature)  # str("0.1") → float(0.1)
    max_tokens = int(max_tokens)      # str("2048") → int(2048)

    # 2. 调用 LLM
    client, model = _get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 3. 返回结构化结果
    return {
        "success": True,
        "data": {
            "text": response.choices[0].message.content,
            "model": model,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "latency_seconds": elapsed,
        }
    }
```

### 设计决策

1. **同步调用而非异步**：LLM 生成通常 <30s，bamboo-engine 的 `timeout_seconds` 节点超时已能兜底，不需要 `_need_schedule` 异步轮询
2. **复用 OPSAGENT 配置**：不新增 API Key 配置，避免用户管理多套凭据
3. **类型安全转换**：由于 bamboo-engine 的 `DataInput.value` 全部存为字符串，`execute()` 中显式 `float()` / `int()` 转换参数，避免 DeepSeek API 400 错误
4. **Emoji 过滤**：`re.sub(r'[\U00010000-\U0010FFFF]', '', text)` 过滤 4 字节 Unicode，兼容 MySQL utf8mb3

### 数据流

```
用户在前端填写 Prompt → PropertyPanel 渲染 FormItem
    → 存入 pipeline_tree.node.params
    → build_bamboo_pipeline() 转为 DataInput
    → celery worker 执行
    → PluginService.execute() 提取 _atom_type=ai_text_gen
    → get_plugin("ai_text_gen") → AiTextGenPlugin
    → AiTextGenPlugin.execute() → _get_llm_client() → DeepSeek API
    → 结果写入 data.outputs(text/model/input_tokens/...)
    → _promote_results() 写入 execution.context._node_outputs
    → trace 页面展示输出 / 下游节点 ${node_id.text} 引用
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/plugins/ai/__init__.py` | AI 插件包标记 |
| `backend/opsflow/plugins/ai/ai_text_gen.py` | AiTextGenPlugin 实现，140 行 |
| `backend/opsflow/core/llm_service.py` | 复用 `_get_llm_client()` 获取 OpenAI 客户端 |
| `docs/superpowers/specs/2026-06-12-ai-text-gen-atom-design.md` | 完整设计规范 |

## 使用方式

1. 在流程设计器中添加新节点
2. 属性面板插件选择器 → `AI` 分组 → `AI 文本生成`
3. 填写 System Prompt（可选，默认"你是一个专业的运维助手"）
4. 填写 Prompt（必填），支持 `${node_id.field}` 引用上游变量
5. 调节 Temperature（默认 0.3 精准模式）和 Max Tokens（默认 2048）
6. 下游节点通过 `${this_node_id.text}` 引用 AI 输出内容
