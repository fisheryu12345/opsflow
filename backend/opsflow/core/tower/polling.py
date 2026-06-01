"""Ansible Tower — 主动轮询与状态推送"""
import logging
import time
from typing import Optional, Callable

import requests
from opsflow.core.tower.base import ADAPTIVE_POLL_SCHEDULE, TowerTimeoutError

logger = logging.getLogger(__name__)


class TowerPollingMixin:
    """Tower 轮询管理 — 自适应轮询、进度估算、WebSocket 推送"""

    def poll_job(self, job_id: int, *,
                 timeout: int = 3600,
                 execution_id: Optional[str] = None,
                 node_id: Optional[str] = None,
                 on_status_change: Optional[Callable] = None) -> dict:
        """主动轮询 Tower 作业直到完成"""
        start_time = time.time()
        last_status = ""

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TowerTimeoutError(
                    f"Tower Job {job_id} 轮询超时（>{timeout}秒）"
                )

            try:
                status_info = self.get_job_status(job_id)
            except requests.RequestException as e:
                logger.warning("[Tower] 轮询失败 job_id=%s: %s，继续重试", job_id, e)
                time.sleep(5)
                continue

            current_status = status_info["status"]
            bamboo_status = status_info["bamboo_status"]

            if current_status != last_status:
                logger.info("[Tower] 作业状态变化 job_id=%s: %s → %s (elapsed=%.1fs)",
                            job_id, last_status or "init", current_status, elapsed)
                last_status = current_status

                stdout_text = status_info.get("result_stdout", "")
                progress = self._estimate_progress(stdout_text)

                self._emit_ws_status(
                    execution_id=execution_id,
                    node_id=node_id,
                    tower_status=current_status,
                    bamboo_status=bamboo_status,
                    progress=progress,
                    artifacts={},
                )

                if on_status_change:
                    on_status_change(status_info)

            if current_status in ("successful", "failed", "error", "canceled"):
                logger.info("[Tower] 作业完成 job_id=%s status=%s elapsed=%.1fs",
                            job_id, current_status, elapsed)
                result = self.extract_result(job_id)
                self._emit_ws_status(
                    execution_id=execution_id,
                    node_id=node_id,
                    tower_status=current_status,
                    bamboo_status=result["status"],
                    progress=100,
                    artifacts=result["artifacts"],
                )
                return result

            interval = self._get_adaptive_interval(elapsed)
            time.sleep(interval)

    @staticmethod
    def _get_adaptive_interval(elapsed: float) -> int:
        """自适应轮询间隔"""
        for max_time, interval in ADAPTIVE_POLL_SCHEDULE:
            if elapsed < max_time:
                return interval
        return 30

    @staticmethod
    def _estimate_progress(stdout_text: str) -> int:
        """从 stdout 文本粗略估算进度 (0~100)"""
        if not stdout_text:
            return 0
        lines = stdout_text.strip().split("\n")
        task_lines = [l for l in lines if "TASK [" in l]
        ok_lines = [l for l in lines if "ok:" in l or "changed:" in l]
        if not task_lines:
            return 0
        done = len(ok_lines)
        total = max(len(task_lines), done + 1)
        return min(int(done / total * 100), 99)

    @staticmethod
    def _emit_ws_status(execution_id: Optional[str], node_id: Optional[str],
                        tower_status: str, bamboo_status: str,
                        progress: int, artifacts: dict):
        """通过 Channels 推送 Tower 作业状态到前端"""
        if not execution_id or not node_id:
            return
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"execution_{execution_id}",
                {
                    "type": "tower_job_update",
                    "node_id": node_id,
                    "tower_status": tower_status,
                    "bamboo_status": bamboo_status,
                    "progress": progress,
                    "artifacts": artifacts,
                },
            )
        except Exception as e:
            logger.warning("[Tower] WebSocket 推送失败: %s", e)

    @staticmethod
    def build_extra_vars(atom_type: str, params: dict,
                         target_hosts: Optional[list] = None,
                         global_vars: Optional[dict] = None) -> dict:
        """组装 Tower Job 的 extra_vars"""
        extra_vars = {
            "opsflow_atom_type": atom_type,
        }
        if target_hosts:
            extra_vars["opsflow_target_hosts"] = target_hosts
        if global_vars:
            extra_vars.update(global_vars)
        extra_vars.update(params)
        return extra_vars
