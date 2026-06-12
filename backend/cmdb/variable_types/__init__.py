"""CMDB 变量类型包 — 导入此模块触发变量类注册到 VARIABLE_REGISTRY"""
from . import query  # noqa: F401 — CmdbQueryVariable
from . import topology  # noqa: F401 — CmdbTopologyVariable
from . import count  # noqa: F401 — CmdbCountVariable
