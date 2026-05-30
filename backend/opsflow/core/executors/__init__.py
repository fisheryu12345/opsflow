"""多平台执行器 — 统一 execute() / rollback() 接口

每个执行器负责一个平台/协议的原子操作调度。
bamboo-engine 通过 AtomExecutorFactory 根据 executor_type 自动分发。
"""

from .base import BaseExecutor, ExecuteResult
from .factory import AtomExecutorFactory

__all__ = [
    "BaseExecutor",
    "ExecuteResult",
    "AtomExecutorFactory",
]
