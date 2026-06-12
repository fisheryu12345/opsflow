# AI 文本生成原子设计 / AI Text Generation Atom

> 创建日期: 2026-06-12
> 状态: 设计草案
> 涉及 App: opsflow

---

## 1. 概述

在 OpsFlow 的插件系统中新增一个 **AI 文本生成原子**（`ai_text_gen`），允许流程中的节点调用 LLM API 生成文本内容。

### 核心能力

- 用户在节点中配置提示词（Prompt），AI 根据提示词生成文本
- 支持系统提示词（System Prompt）设定 AI 角色
- 支持 Temperature 和 Max Tokens 参数控制输出
- 输出内容可被下游节点通过变量引用 `${node_id.text}` 使用
- 复用项目现有 OPSAGENT 配置（DeepSeek 模型）

### 设计原则

- **最小变更**：只新增一个插件文件，不改现有代码
- **复用现有基础设施**：插件系统、LLM 客户端、表单渲染均已就绪
- **匹配现有插件模式**：继承 `BasePlugin`，与其他原子行为一致

---

## 2. 插件元数据

| 字段 | 值 |
|------|-----|
| `code` | `ai_text_gen` |
| `name` | AI 文本生成 |
| `name_en` | AI Text Generation |
| `group` | `AI`（新分组） |
| `version` | `v1.0` |
| `risk_level` | `low` |
| `icon` | `🤖` |
| `color` | `#6366f1` |
| `_need_schedule` | `False`（同步调用） |

---

## 3. 表单配置

| tag_code | type | 必填 | 默认值 | 说明 |
|----------|------|------|--------|------|
| `system_prompt` | textarea | 否 | "你是一个专业的运维助手..." | 设定 AI 角色和行为模式 |
| `prompt` | textarea | **是** | — | 核心提示词，支持变量引用 `${node_id.field}` |
| `temperature` | float | 否 | 0.3 | 控制输出随机性，范围 0-1 |
| `max_tokens` | int | 否 | 2048 | 最大输出长度，范围 64-8192 |

### 变量引用支持

`prompt` 字段支持 `${node_id.field}` 语法，允许引用上游节点的输出。例如：

```
分析以下磁盘使用情况并给出建议：${n1._result}

根据之前的分析结果，生成一份摘要报告：${n3.text}
```

变量解析由 `PluginService` 自动处理（通过 `get_var_types()` 返回 `{"prompt": "splice"}`）。

---

## 4. 执行逻辑

### 流程

```
execute(prompt, system_prompt, temperature, max_tokens)
  │
  ├─ 1. 获取 LLM 客户端（复用 OPSAGENT 配置）
  │    _get_llm_client() → OpenAI(base_url=OPSAGENT_BASE_URL, api_key=OPSAGENT_API_KEY)
  │
  ├─ 2. 构建 messages 数组
  │    [{"role": "system", "content": system_prompt},  ← 如有
  │     {"role": "user",   "content": prompt}]          ← 必填
  │
  ├─ 3. 调用 API
  │    client.chat.completions.create(model, messages, temperature, max_tokens)
  │
  ├─ 4. 处理结果
  │    ├─ 成功 → text, model, token用量, 耗时 → {"success": True, "data": {...}}
  │    └─ 失败 → 异常信息 → {"success": False, "error": "..."}
  │
  └─ 5. 过滤 emoji（MySQL utf8mb3 兼容）
```

### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | AI 生成的文本内容 |
| `model` | string | 使用的模型名称 |
| `input_tokens` | int | 输入 Token 数 |
| `output_tokens` | int | 输出 Token 数 |
| `latency_seconds` | float | API 响应耗时 |

### 错误处理

- API 调用超时：bamboo-engine 的 `timeout_seconds` 节点配置会兜底
- API 返回异常：`execute()` 捕获异常，返回 `success: false`，节点进入 FAILED 状态
- 空响应：DeepSeek 可能返回空 `content`，此时 `text` 为空字符串

---

## 5. 文件结构

只新增一个文件：

```
backend/opsflow/plugins/ai/
  __init__.py          ← 空文件，标记为 Python 包
  ai_text_gen.py       ← AI 文本生成插件实现
```

### `ai_text_gen.py` 完整结构

```python
"""
AI Text Generation Plugin — 调用 LLM 生成文本 / AI Text Generation Atom

通过复用 OPSAGENT 配置（DeepSeek API）实现 AI 文本生成。
支持系统提示词、温度参数、最大 Token 数等配置。
"""
import re
import time
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem


class AiTextGenPlugin(BasePlugin):
    code = "ai_text_gen"
    name = "AI 文本生成"
    name_en = "AI Text Generation"
    group = "AI"
    description = "调用 AI 模型根据提示词生成文本内容，支持变量引用和参数调节"
    risk_level = "low"
    icon = "🤖"
    color = "#6366f1"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="system_prompt",
                type="textarea",
                name="系统提示词",
                name_en="System Prompt",
                description="设定 AI 的角色和行为模式，如「你是一个运维专家」",
                default="你是一个专业的运维助手，请根据用户的问题给出准确、清晰的回答。",
                attrs={"rows": 3, "placeholder": "例如：你是一个运维专家，擅长分析系统日志"},
            ),
            FormItem(
                tag_code="prompt",
                type="textarea",
                name="提示词",
                name_en="Prompt",
                required=True,
                description="告诉 AI 要生成什么内容，支持变量引用 ${node_id.field}",
                attrs={"rows": 6, "placeholder": "例如：分析以下磁盘使用情况并给出建议：${n1._result}"},
            ),
            FormItem(
                tag_code="temperature",
                type="input",
                name="温度参数",
                name_en="Temperature",
                description="控制输出随机性，0=精准，1=创意",
                default=0.3,
                attrs={"type": "number", "min": 0, "max": 1, "step": 0.1},
            ),
            FormItem(
                tag_code="max_tokens",
                type="int",
                name="最大 Token 数",
                name_en="Max Tokens",
                description="限制输出的最大长度",
                default=2048,
                attrs={"min": 64, "max": 8192, "step": 64},
            ),
        ]

    @classmethod
    def get_var_types(cls):
        return {"prompt": "splice"}

    def execute(self, prompt: str, system_prompt: str = "",
                temperature: float = 0.3, max_tokens: int = 2048,
                **kwargs) -> dict:
        if not prompt or not prompt.strip():
            return {"success": False, "data": {}, "error": "prompt is required"}
        
        from opsflow.core.llm_service import _get_llm_client

        client, model = _get_llm_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = round(time.time() - start, 2)
            text = response.choices[0].message.content or ""
            # 过滤 4 字节 UTF-8（emoji），兼容 MySQL utf8mb3
            text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)

            return {
                "success": True,
                "data": {
                    "text": text,
                    "model": model,
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    "latency_seconds": latency,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "text", "type": "string", "description": "AI 生成的文本内容"},
            {"name": "model", "type": "string", "description": "使用的模型名称"},
            {"name": "input_tokens", "type": "int", "description": "输入 Token 数"},
            {"name": "output_tokens", "type": "int", "description": "输出 Token 数"},
            {"name": "latency_seconds", "type": "float", "description": "API 响应耗时（秒）"},
        ]
```

---

## 6. 集成路径

本插件的集成不涉及对现有代码的任何修改，完全依赖已有的插件自动发现机制：

### 后端

| 步骤 | 涉及 | 说明 |
|------|------|------|
| 插件自动发现 | `PluginLoader.scan()` | 扫描 `plugins/ai/` 目录，注册 `AiTextGenPlugin` |
| 元数据同步 | `sync_plugin_meta_to_db()` | 写入 `PluginMeta` 表，包含 form_schema 和 output_schema |
| 表单渲染 | `<RenderForm>` | 前端自动拉取 form_schema 渲染表单 |
| 流程执行 | `PluginService.execute()` | 根据 `_atom_type='ai_text_gen'` 路由到本插件 |

### 前端

| 组件 | 说明 |
|------|------|
| `PluginPickerDialog` | AI 分组下出现 "AI 文本生成" 选项 |
| `PropertyPanel` | 选择后渲染 System Prompt / Prompt / Temperature / Max Tokens 表单 |
| 输出 Schema 面板 | 显示 text / model / input_tokens / output_tokens / latency_seconds 引用 |

### 用户操作路径

1. 在画布上添加一个节点
2. 在属性面板的插件选择器中，选择 `AI` 分组 → `AI 文本生成`
3. 填写 System Prompt（可选）和 Prompt（必填）
4. 调节 Temperature 和 Max Tokens（可选）
5. 在 Prompt 中使用 `${prev_node_id.field}` 引用上游输出
6. 下游节点引用 `${this_node_id.text}` 获取 AI 生成内容

---

## 7. 验证方式

1. **插件注册验证**：启动 Django，确认日志中出现 `AiTextGenPlugin` 注册信息
2. **API 验证**：调用 `GET /api/opsflow/plugins/detail/?code=ai_text_gen`，确认返回完整的 form_schema 和 output_schema
3. **表单渲染验证**：前端新建节点，选择 AI 文本生成，确认表单字段正确渲染
4. **执行验证**：创建一个包含 AI 文本生成节点的 pipeline，填写简单 prompt 如 "用一句话描述当前系统的健康状态"，确认执行成功，输出 text 非空
5. **变量引用验证**：AI 节点后接发送邮件节点，引用 `${ai_node_id.text}` 作为邮件内容，确认正确传递

---

## 8. 未纳入范围

- ❌ 流式输出（Streaming）— 同步调用已满足当前需求
- ❌ 多轮对话 — 单个 prompt + response 够用
- ❌ 图片/多模态输入 — 运维场景以文本为主
- ❌ 自定义模型选择（UI 上切换模型）— 复用 OPSAGENT 配置
- ❌ 异步 Celery 任务 — 短文本生成无需异步
