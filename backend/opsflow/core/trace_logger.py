"""节点轨迹日志写入器 — 每个节点独立的 JSON Lines 日志文件

目录结构:
  {LOG_DIR}/opsflow/tasks/{execution_id}/
    ├── {node_id}.log    # 每个节点独立日志文件
    └── metadata.json    # 执行元数据（仅创建时写入一次）

日志格式 (JSON Lines):
  {"timestamp":"...","node_id":"...","event":"output","data":{...}}
  {"timestamp":"...","node_id":"...","event":"error","data":{...}}

事件类型: state | output | error | tower | tower_event | retry
"""

import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

TRACE_LOG_ROOT = "opsflow"  # settings.LOG_DIR 下的子目录


def _get_trace_dir(execution_id) -> str:
    """获取执行实例的日志目录路径"""
    return os.path.join(settings.LOG_DIR, TRACE_LOG_ROOT, "tasks", str(execution_id))


class NodeTraceLogger:
    """节点轨迹日志写入器

    为每个执行实例创建独立目录，每个节点写入独立 .log 文件。
    所有文件操作通过 try/except 降级，不抛异常影响主流程。
    """

    def __init__(self, execution_id):
        self.execution_id = execution_id
        self.log_dir = _get_trace_dir(execution_id)
        self._ensure_dir()

    # -- Public API -----------------------------------------------------------

    def log(self, node_id: str, event: str, data: dict):
        """写入一条结构化日志事件

        Args:
            node_id: 节点 ID
            event: 事件类型 (state/output/error/tower/tower_event/retry)
            data: 事件数据 dict
        """
        log_path = os.path.join(self.log_dir, f"{node_id}.log")
        entry = {
            "timestamp": self._now(),
            "node_id": node_id,
            "event": event,
            "data": data,
        }
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            logger.warning(
                "[TraceLogger] write failed for %s: %s", log_path, e
            )

    def log_state(self, node_id: str, from_state: str, to_state: str):
        """记录节点状态变更"""
        self.log(node_id, "state", {"from": from_state, "to": to_state})

    def log_output(self, node_id: str, outputs: dict):
        """记录节点执行输出"""
        self.log(node_id, "output", outputs)

    def log_error(self, node_id: str, error: str, stderr: str = ""):
        """记录节点执行错误"""
        self.log(node_id, "error", {"error": error, "stderr": stderr})

    def log_tower(self, node_id: str, job_data: dict):
        """记录 Tower 作业状态变更"""
        self.log(node_id, "tower", job_data)

    def log_tower_event(self, node_id: str, event_data: dict):
        """记录 Tower 作业详细事件（host 粒度）"""
        self.log(node_id, "tower_event", event_data)

    def log_retry(self, node_id: str, retry_count: int, reason: str = ""):
        """记录节点重试"""
        self.log(
            node_id, "retry", {"retry_count": retry_count, "reason": reason}
        )

    # -- Read ---------------------------------------------------------------

    def read_log(self, node_id: str) -> list[dict]:
        """读取节点日志文件，按行解析为 JSON 列表

        Returns:
            日志条目列表，文件不存在或解析失败返回空列表
        """
        log_path = os.path.join(self.log_dir, f"{node_id}.log")
        if not os.path.exists(log_path):
            return []
        entries = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "[TraceLogger] read failed for %s: %s", log_path, e
            )
        return entries

    def get_log_file_path(self, node_id: str) -> str:
        """获取节点日志文件的完整路径"""
        return os.path.join(self.log_dir, f"{node_id}.log")

    # -- Metadata ------------------------------------------------------------

    def write_metadata(self, metadata: dict):
        """写入执行元数据（仅文件不存在时创建）"""
        meta_path = os.path.join(self.log_dir, "metadata.json")
        if os.path.exists(meta_path):
            return
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, default=str, indent=2)
        except OSError as e:
            logger.warning(
                "[TraceLogger] metadata write failed: %s", e
            )

    # -- Helpers -------------------------------------------------------------

    def _ensure_dir(self):
        """确保日志目录存在"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except OSError as e:
            logger.warning(
                "[TraceLogger] mkdir failed for %s: %s", self.log_dir, e
            )

    @staticmethod
    def _now() -> str:
        from django.utils import timezone
        return timezone.now().isoformat()
