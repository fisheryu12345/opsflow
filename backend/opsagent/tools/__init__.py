# backend/opsagent/tools/__init__.py
import importlib
import pkgutil


def _has_tooldef(obj) -> bool:
    return hasattr(obj, '_tooldef') and obj._tooldef is not None


def auto_discover():
    """Scan this package and register all @tool decorated functions."""
    from opsagent.core.tool_registry import register

    package = __package__ or 'opsagent.tools'
    for _, module_name, _ in pkgutil.iter_modules(__path__, prefix=package + '.'):
        mod = importlib.import_module(module_name)
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if _has_tooldef(attr):
                register(attr._tooldef)
