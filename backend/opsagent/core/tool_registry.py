# backend/opsagent/core/tool_registry.py
from opsagent.tools.base import ToolDef


_registry: dict[str, ToolDef] = {}


def register(tool_def: ToolDef) -> None:
    if tool_def.name in _registry:
        return  # already registered — idempotent re-registration is a no-op
    _registry[tool_def.name] = tool_def


def get(name: str) -> ToolDef | None:
    return _registry.get(name)


def list_all() -> list[ToolDef]:
    return list(_registry.values())


def list_names() -> list[str]:
    return list(_registry.keys())


def get_openai_schemas() -> list[dict]:
    return [t.to_openai_schema() for t in _registry.values()]


def clear() -> None:
    _registry.clear()
