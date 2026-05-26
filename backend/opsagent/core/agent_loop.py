# backend/opsagent/core/agent_loop.py
import json
from typing import AsyncIterator
from opsagent.core.types import AgentContext, ToolResult, SafetyDecision
from opsagent.core.tool_registry import get, get_openai_schemas
from opsagent.core.safety import assess, requires_user_approval
from opsagent.core.context import ContextManager


class AgentLoop:
    def __init__(self, llm_client, context_manager: ContextManager | None = None):
        self.llm = llm_client
        self.ctx_manager = context_manager or ContextManager()

    async def run(
        self,
        user_input: str,
        context: AgentContext,
        history: list[dict] | None = None,
        on_tool_call: callable | None = None,
        on_approval_needed: callable | None = None,
        on_response: callable | None = None,
    ) -> str:
        """Run the agent loop. Returns final text response."""
        schemas = get_openai_schemas()
        system_prompt = self.ctx_manager.build_system_prompt(context, [s["function"]["name"] for s in schemas])
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        while True:
            response = await self.llm.chat.completions.create(
                model=self.llm.model_name,
                messages=messages,
                tools=schemas,
            )
            choice = response.choices[0]

            if choice.finish_reason == "stop":
                text = choice.message.content or ""
                if on_response:
                    on_response(text)
                return text

            if choice.finish_reason == "tool_calls":
                for tc in choice.message.tool_calls:
                    tool = get(tc.function.name)
                    if tool is None:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps({"error": f"Unknown tool: {tc.function.name}"}),
                        })
                        continue

                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    assessment = assess(tool, context.env_type)
                    if on_tool_call:
                        on_tool_call(tool.name, args, assessment)

                    if requires_user_approval(assessment) and on_approval_needed:
                        approved = await on_approval_needed(tool.name, args, assessment)
                        if not approved:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps({"error": "User denied the operation"}),
                            })
                            continue

                    result: ToolResult = await tool.handler(**args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "success": result.success,
                            "output": result.output,
                            "error": result.error,
                            "metadata": result.metadata,
                        }),
                    })

            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (choice.message.tool_calls or [])
                ],
            } if choice.message.tool_calls else {
                "role": "assistant",
                "content": choice.message.content,
            })
