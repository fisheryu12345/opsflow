"""测试执行器 — 后台打印当前时间，用于流程引擎功能验证

executor_type: "test"
不依赖任何外部系统，纯粹用于测试 bamboo-engine 流程控制（串行/条件/并行/汇聚）。

测试场景:
  - 串行: A → B → C，检查节点是否依次 completed
  - 条件: test(fail=true) → ExclusiveGateway → success/failure 分支
  - 并行: ParallelGateway → test + test + test → ConvergeGateway
"""

import logging
from datetime import datetime

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class TestExecutor(BaseExecutor):
    """测试执行器 — 打印当前时间，不执行任何真实操作"""

    executor_type = "test"

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行测试原子

        inputs:
          - message: str (可选，附加消息，默认 "hello")
          - fail: bool (可选，是否模拟失败，默认 False)
        """
        message = inputs.get("message", "hello")
        should_fail = inputs.get("fail", False)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        log_line = f"[TestAtom] {timestamp} | message={message} | fail={should_fail}"
        logger.info(log_line)
        print(log_line)  # 确保 Celery worker 日志可见

        # 模拟执行耗时（让 WebSocket 推送可观察）
        import time
        time.sleep(1)

        return ExecuteResult(
            success=not should_fail,
            data={
                "timestamp": timestamp,
                "message": message,
                "stdout": log_line,
                "returncode": 0 if not should_fail else 1,
            },
        )

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 仅记录日志"""
        logger.info("[TestAtom] rollback被执行 timestamp=%s",
                    datetime.now().isoformat())
        return ExecuteResult(True, {"rollback": True})
