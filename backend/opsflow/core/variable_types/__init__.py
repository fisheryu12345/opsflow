"""变量类型包 — 导入此模块触发所有变量类注册到 VARIABLE_REGISTRY"""

from . import common
from cmdb.variable_types import *  # noqa: F401 — CMDB 变量类型（领域归属 cmdb 子产品）
