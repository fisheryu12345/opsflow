"""Ansible Tower — 作业生命周期管理"""
import json
import logging

import requests
from opsflow.core.tower.base import TowerConfigError, TowerJobError, TOWER_TO_BAMBOO_STATUS

logger = logging.getLogger(__name__)


class TowerJobMixin:
    """Tower 作业管理 — 启动、查询、取消、结果提取"""

    def launch_job(self, template_id=None, extra_vars=None) -> dict:
        """触发 Tower Job Template"""
        if not self.is_configured():
            raise TowerConfigError("Tower 未配置或 URL 为 localhost")

        tid = template_id or self._config["template_id"]
        payload = {}
        if extra_vars:
            payload["extra_vars"] = json.dumps(extra_vars, ensure_ascii=False)

        try:
            resp = self._request(
                "POST", f"job_templates/{tid}/launch/",
                json=payload,
            )
            result = resp.json()
            job_id = result.get("id") or result.get("job", 0)
            logger.info("[Tower] 作业已触发 template=%s job_id=%s", tid, job_id)
            return {
                "job_id": int(job_id) if job_id else 0,
                "status": result.get("status", "pending"),
                "job_url": result.get("url", ""),
                "related": result.get("related", {}),
            }
        except requests.RequestException as e:
            logger.exception("[Tower] 触发作业失败 template=%s", tid)
            raise TowerJobError(f"触发 Tower Job 失败: {e}") from e

    def get_job_status(self, job_id: int) -> dict:
        """查询作业当前状态"""
        resp = self._request("GET", f"jobs/{job_id}/")
        job = resp.json()
        status = job.get("status", "unknown")
        return {
            "status": status,
            "bamboo_status": TOWER_TO_BAMBOO_STATUS.get(status, "pending"),
            "started": job.get("started", ""),
            "finished": job.get("finished", ""),
            "elapsed": job.get("elapsed", 0.0),
            "failed": job.get("failed", False),
            "result_stdout": job.get("result_stdout", ""),
            "related": job.get("related", {}),
        }

    def cancel_job(self, job_id: int) -> bool:
        """取消运行中的作业"""
        try:
            self._request("POST", f"jobs/{job_id}/cancel/")
            logger.info("[Tower] 作业已取消 job_id=%s", job_id)
            return True
        except requests.RequestException as e:
            logger.warning("[Tower] 取消失败 job_id=%s: %s", job_id, e)
            return False

    def get_artifacts(self, job_id: int) -> dict:
        """获取 set_stats 写入的 Artifacts"""
        try:
            resp = self._request("GET", f"jobs/{job_id}/artifacts/")
            return resp.json() if resp.status_code == 200 else {}
        except requests.RequestException:
            logger.warning("[Tower] 获取 artifacts 失败 job_id=%s", job_id)
            return {}

    def get_job_events(self, job_id: int, page_size: int = 50) -> list:
        """获取作业事件列表（用于审计日志）"""
        events = []
        page = 1
        try:
            while True:
                resp = self._request(
                    "GET", f"jobs/{job_id}/job_events/",
                    params={"page": page, "page_size": page_size},
                )
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break
                for ev in results:
                    events.append({
                        "event": ev.get("event", ""),
                        "host": ev.get("host_name", ""),
                        "stdout": ev.get("stdout", ""),
                        "counter": ev.get("counter", 0),
                        "failed": ev.get("failed", False),
                    })
                if not data.get("next"):
                    break
                page += 1
        except requests.RequestException:
            logger.warning("[Tower] 获取 job_events 失败 job_id=%s", job_id)
        return events

    def get_stdout(self, job_id: int, max_length: int = 5000) -> str:
        """获取作业标准输出"""
        try:
            resp = self._request(
                "GET", f"jobs/{job_id}/stdout/",
                params={"format": "txt"},
            )
            text = resp.text
            return text[:max_length] if len(text) > max_length else text
        except requests.RequestException:
            return ""

    def extract_result(self, job_id: int) -> dict:
        """提取完整的作业执行结果"""
        status_info = self.get_job_status(job_id)
        bamboo_status = status_info["bamboo_status"]

        artifacts = self.get_artifacts(job_id)
        stdout = self.get_stdout(job_id)

        structured = {}
        try:
            lines = stdout.strip().split("\n")
            for line in reversed(lines):
                stripped = line.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    structured = json.loads(stripped)
                    break
        except (json.JSONDecodeError, IndexError):
            pass

        events = self.get_job_events(job_id)
        summary = {"ok": 0, "changed": 0, "failed": 0, "dark": 0, "skipped": 0}
        for ev in events:
            event_name = ev.get("event", "")
            if "on_ok" in event_name:
                summary["ok"] += 1
            elif "on_changed" in event_name:
                summary["changed"] += 1
            elif "on_failed" in event_name:
                summary["failed"] += 1
            elif "on_skipped" in event_name:
                summary["skipped"] += 1
            elif "on_dark" in event_name:
                summary["dark"] += 1

        return {
            "status": bamboo_status,
            "artifacts": artifacts,
            "structured": structured,
            "events": events[:200],
            "stdout": stdout,
            "elapsed": status_info.get("elapsed", 0),
            "summary": summary,
        }
