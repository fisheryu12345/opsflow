"""执行器基类 — 定义统一契约"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecuteResult:
    """统一执行结果"""
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""


class BaseExecutor:
    """执行器基类 — 所有平台执行器继承此类

    子类必须实现:
      - execute(inputs: dict) -> ExecuteResult
      - rollback(inputs: dict, context: dict) -> ExecuteResult
    """

    # 执行器类型标识（与 meta.json executor_type 对应）
    executor_type: str = ""

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行原子操作

        Args:
            inputs: 原子输入参数（已通过 meta.json inputs 校验）

        Returns:
            ExecuteResult: 执行结果
        """
        raise NotImplementedError

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚原子操作

        Args:
            inputs: 原子输入参数
            context: 原始 execute() 返回的 data（含执行状态、资源 ID 等）

        Returns:
            ExecuteResult: 回滚结果
        """
        raise NotImplementedError

    def validate_inputs(self, meta_inputs: list, actual_inputs: dict) -> list[str]:
        """校验输入参数（可选覆盖）

        Args:
            meta_inputs: meta.json 中定义的 inputs 列表
            actual_inputs: 实际传入的参数

        Returns:
            错误信息列表（空 = 校验通过）
        """
        errors = []
        for inp in meta_inputs:
            name = inp.get("name", "")
            if inp.get("required", False) and name not in actual_inputs:
                errors.append(f"缺少必填参数: {name}")
            # type check
            val = actual_inputs.get(name)
            if val is not None:
                expected_type = inp.get("type", "")
                if expected_type == "int" and not isinstance(val, int):
                    errors.append(f"参数 {name} 应为 int，实际为 {type(val).__name__}")
                elif expected_type == "list" and not isinstance(val, list):
                    errors.append(f"参数 {name} 应为 list，实际为 {type(val).__name__}")
        return errors
