"""Ansible Tower (AWX) 服务常量与异常"""

# Tower 状态 → bamboo-engine 状态映射
TOWER_TO_BAMBOO_STATUS = {
    "pending": "pending",
    "waiting": "running",
    "running": "running",
    "successful": "success",
    "failed": "failed",
    "error": "failed",
    "canceled": "failed",
}

ADAPTIVE_POLL_SCHEDULE = [
    (30, 3),       # 前 30 秒：每 3 秒
    (300, 5),      # 30秒~5分钟：每 5 秒
    (1800, 10),    # 5分钟~30分钟：每 10 秒
    (float("inf"), 30),  # 超过 30 分钟：每 30 秒
]


class TowerConfigError(Exception):
    """Tower 配置错误"""


class TowerJobError(Exception):
    """Tower 作业执行错误"""


class TowerTimeoutError(Exception):
    """Tower 作业轮询超时"""
