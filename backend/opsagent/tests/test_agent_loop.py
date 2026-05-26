# backend/opsagent/tests/test_agent_loop.py
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from opsagent.core.agent_loop import AgentLoop
from opsagent.core.types import AgentContext, RiskEnv, ToolResult, RiskAssessment, SafetyDecision
from opsagent.core.tool_registry import register, clear, get
from opsagent.tools.base import ToolDef


class _FakeChatCompletion:
    def __init__(self, content="", tool_calls=None, finish_reason="stop"):
        self.choices = [self]
        self.message = MagicMock()
        self.message.content = content
        self.message.tool_calls = tool_calls or []
        self.finish_reason = finish_reason


class _FakeLLM:
    def __init__(self, responses=None):
        self.model_name = "fake-model"
        self.responses = responses or []
        self.call_count = 0
        self.chat = MagicMock()
        self.chat.completions = MagicMock()

    async def _create(self, **kwargs):
        resp = self.responses[self.call_count] if self.call_count < len(self.responses) else _FakeChatCompletion()
        self.call_count += 1
        return resp


@pytest.fixture(autouse=True)
def clear_registry():
    clear()
    yield
    clear()


@pytest.mark.asyncio
async def test_agent_loop_text_only():
    llm = _FakeLLM(responses=[_FakeChatCompletion(content="Hello, how can I help?")])
    agent = AgentLoop(llm_client=llm)
    llm.chat.completions.create = AsyncMock(side_effect=llm._create)

    ctx = AgentContext(session_id="t1", operator="tester")
    result = await agent.run("hi", ctx)

    assert "Hello" in result


@pytest.mark.asyncio
async def test_agent_loop_with_tool_call():
    call_count = [0]

    async def _my_tool(**kwargs):
        call_count[0] += 1
        return ToolResult(success=True, output="executed")

    td = ToolDef(
        name="test_echo", description="Echo test",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level=RiskEnv.DEVELOPMENT, handler=_my_tool,
    )
    from opsagent.core.types import RiskLevel
    td.risk_level = RiskLevel.READ
    register(td)

    tc = MagicMock()
    tc.id = "call_1"
    tc.type = "function"
    tc.function = MagicMock()
    tc.function.name = "test_echo"
    tc.function.arguments = json.dumps({})

    llm = _FakeLLM(responses=[
        _FakeChatCompletion(tool_calls=[tc], finish_reason="tool_calls"),
        _FakeChatCompletion(content="Done!", finish_reason="stop"),
    ])
    llm.chat.completions.create = AsyncMock(side_effect=llm._create)

    ctx = AgentContext(session_id="t2", operator="tester")
    agent = AgentLoop(llm_client=llm)
    result = await agent.run("do it", ctx)

    assert call_count[0] == 1
    assert "Done" in result
