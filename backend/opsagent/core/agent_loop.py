# backend/opsagent/core/agent_loop.py
import json
from opsagent.core.types import AgentContext, ToolResult, SafetyDecision
from opsagent.core.tool_registry import get, get_openai_schemas
from opsagent.core.safety import assess, requires_user_approval
from opsagent.core.context import ContextManager


class AgentLoopError(Exception):
    """Raised when the agent loop encounters a fatal error."""


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
        on_error: callable | None = None,
        max_iterations: int = 20,
    ) -> str:
        """Run the agent loop. Returns final text response."""
        schemas = get_openai_schemas()
        system_prompt = self.ctx_manager.build_system_prompt(
            context, [s["function"]["name"] for s in schemas]
        )
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            try:
                response = await self.llm.chat.completions.create(
                    model=self.llm.model_name,
                    messages=messages,
                    tools=schemas,
                )
            except Exception as exc:
                if on_error:
                    on_error(f"LLM call failed: {exc}")
                raise AgentLoopError(f"LLM call failed at iteration {iteration}: {exc}") from exc

            choice = response.choices[0]

            if choice.finish_reason == "stop":
                text = choice.message.content or ""
                if on_response:
                    on_response(text)
                return text

            if choice.finish_reason == "tool_calls":
                # OpenAI API requires assistant message (with tool_calls) BEFORE tool results
                assistant_msg = {
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in (choice.message.tool_calls or [])
                    ],
                }
                messages.append(assistant_msg)

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

                    try:
                        result: ToolResult = await tool.handler(**args)
                    except Exception as exc:
                        result = ToolResult(
                            success=False,
                            output="",
                            error=f"Tool execution failed: {exc}",
                        )

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
                continue

            # Unhandled finish_reason (e.g., "length", "content_filter")
            error_text = f"Unexpected finish_reason: {choice.finish_reason}"
            if on_error:
                on_error(error_text)
            return error_text

        raise AgentLoopError(f"Exceeded max iterations ({max_iterations})")
