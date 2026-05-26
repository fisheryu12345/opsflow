# backend/opsagent/tools/base.py
import functools
from typing import Any
from opsagent.core.types import RiskLevel, ToolHandler


class ToolDef:
    __slots__ = ('name', 'description', 'parameters', 'risk_level', 'handler', 'requires_approval')

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        risk_level: RiskLevel,
        handler: ToolHandler,
        requires_approval: bool = True,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.risk_level = risk_level
        self.handler = handler
        self.requires_approval = requires_approval

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self):
        return f"ToolDef({self.name}, risk={self.risk_level.value})"


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    risk_level: RiskLevel = RiskLevel.READ,
    requires_approval: bool = True,
):
    """Decorator to register a function as a tool."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(**kwargs):
            return await func(**kwargs)

        wrapper._tooldef = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            risk_level=risk_level,
            handler=wrapper,
            requires_approval=requires_approval,
        )
        return wrapper
    return decorator
