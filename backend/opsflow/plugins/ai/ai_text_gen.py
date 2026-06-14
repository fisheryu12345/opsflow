"""
AI Text Generation Plugin — 调用 LLM 生成文本 / AI Text Generation Atom

通过复用 OPSAGENT 配置（DeepSeek API）实现 AI 文本生成。
支持系统提示词、温度参数、最大 Token 数等配置。
下游节点可通过 `${node_id.text}` 引用生成的文本内容。
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
        """调用 LLM 生成文本 / Execute AI text generation

        Args:
            prompt: 提示词（必填），支持变量引用
            system_prompt: 系统提示词，设定 AI 角色
            temperature: 温度参数 0-1，控制随机性
            max_tokens: 最大输出 token 数

        Returns:
            dict: {"success": bool, "data": {...}, "error": str}
        """
        # 前置校验
        if not prompt or not prompt.strip():
            return {"success": False, "data": {}, "error": "prompt is required"}

        # 类型安全转换（bamboo-engine 所有 inputs 存为字符串，需显式转换）
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = 0.3
        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):
            max_tokens = 2048

        from integration.services.connector_service import get_ai_connector_or_raise

        connector = get_ai_connector_or_raise()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            result = connector.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = round(time.time() - start, 2)
            text = result.get("content", "") or ""
            model = result.get("model", "unknown")
            usage = result.get("usage", {})
            # 过滤 4 字节 UTF-8（emoji），兼容 MySQL utf8mb3
            text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)

            return {
                "success": True,
                "data": {
                    "text": text,
                    "model": model,
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
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
