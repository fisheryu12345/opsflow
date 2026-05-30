"""Ansible Tower (AWX) REST API 服务封装

职责:
  - 触发 Job Template 执行 (POST /api/v2/job_templates/{id}/launch/)
  - 主动轮询作业状态（自适应间隔）
  - 提取执行结果 (set_stats artifacts / events / stdout)
  - 通过 WebSocket 推送实时状态
  - 取消运行中的作业

执行流程:
  TowerService.launch_job()  →  返回 job_id
       │
       ▼
  TowerService.poll_job()    →  自适应间隔轮询 + WebSocket 推送
       │                        ├── pending/waiting  →  灰色
       │                        ├── running          →  黄色 + 进度
       │                        ├── successful       →  绿色 + 提取 artifacts
       │                        └── failed/error/canceled →  红色
       │
       ▼
  TowerService.extract_result()  →  artifacts + events + stdout → context 注入
"""

import json
import logging
import time
from typing import Optional, Callable
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

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


class TowerService:
    """Ansible Tower (AWX) REST API 服务"""

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._config: Optional[dict] = None
        self._load_config()

    # ------------------------------------------------------------------
    # 配置与连接
    # ------------------------------------------------------------------

    def _load_config(self):
        """从 Django settings / env 加载 Tower 配置"""
        try:
            from conf.env import (
                ANSIBLE_API_URL, ANSIBLE_API_TOKEN,
                ANSIBLE_TEMPLATE_ID, ANSIBLE_VERIFY_SSL,
            )
            self._config = {
                "url": (ANSIBLE_API_URL or "").rstrip("/"),
                "token": ANSIBLE_API_TOKEN or "",
                "template_id": ANSIBLE_TEMPLATE_ID or 1,
                "verify_ssl": bool(ANSIBLE_VERIFY_SSL) if "ANSIBLE_VERIFY_SSL" in dir() else False,
            }
        except (ImportError, AttributeError):
            self._config = {
                "url": "",
                "token": "",
                "template_id": 1,
                "verify_ssl": False,
            }

    def _get_session(self) -> requests.Session:
        """获取可复用的 requests Session（含重试）"""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = (self._config["token"], "") if self._config["token"] else None
            self._session.headers.update({
                "Content-Type": "application/json",
            })
            # 自动重试适配器
            adapter = requests.adapters.HTTPAdapter(
                max_retries=requests.packages.urllib3.util.retry.Retry(
                    total=2, backoff_factor=0.5,
                    allowed_methods=["GET", "POST"],
                )
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        return self._session

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """统一的 Tower API 请求"""
        url = urljoin(self._config["url"] + "/", path.lstrip("/"))
        session = self._get_session()
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("verify", self._config["verify_ssl"])

        if self._config["token"]:
            kwargs.setdefault("headers", {})
            kwargs["headers"].setdefault("Authorization", f"Bearer {self._config['token']}")

        resp = session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def is_configured(self) -> bool:
        """Tower 是否已配置（URL 非空且非 localhost）"""
        url = self._config.get("url", "")
        return bool(url) and "localhost" not in url

    # ------------------------------------------------------------------
    # Job 生命周期
    # ------------------------------------------------------------------

    def launch_job(self, template_id: Optional[int] = None,
                   extra_vars: Optional[dict] = None) -> dict:
        """触发 Tower Job Template

        Args:
            template_id: Job Template ID（默认使用配置中的 template_id）
            extra_vars: 注入的 extra_vars 字典

        Returns:
            {"job_id": int, "status": str, "job_url": str, "related": dict}

        Raises:
            TowerConfigError: Tower 未配置
            TowerJobError: API 调用失败
        """
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
        """查询作业当前状态

        Returns:
            {"status": str, "started": str, "finished": str,
             "elapsed": float, "result_stdout": str, "failed": bool}
        """
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
        """取消运行中的作业 (POST /api/v2/jobs/{id}/cancel/)"""
        try:
            self._request("POST", f"jobs/{job_id}/cancel/")
            logger.info("[Tower] 作业已取消 job_id=%s", job_id)
            return True
        except requests.RequestException as e:
            logger.warning("[Tower] 取消失败 job_id=%s: %s", job_id, e)
            return False

    # ------------------------------------------------------------------
    # 结果提取
    # ------------------------------------------------------------------

    def get_artifacts(self, job_id: int) -> dict:
        """获取 set_stats 写入的 Artifacts (GET /api/v2/jobs/{id}/artifacts/)"""
        try:
            resp = self._request("GET", f"jobs/{job_id}/artifacts/")
            return resp.json() if resp.status_code == 200 else {}
        except requests.RequestException:
            logger.warning("[Tower] 获取 artifacts 失败 job_id=%s", job_id)
            return {}

    def get_job_events(self, job_id: int, page_size: int = 50) -> list:
        """获取作业事件列表（用于审计日志）

        Returns: [{"event": "runner_on_ok", "host": "web-01",
                    "stdout": "TASK [backup_file] ****", "counter": 1}, ...]
        """
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
        """获取作业标准输出 (format=txt)"""
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
        """提取完整的作业执行结果

        合并 artifacts / events / stdout，供 bamboo-engine context 注入。

        Returns:
            {"status": "success"/"failed",
             "artifacts": {...},
             "events": [...],
             "stdout": "...",
             "summary": {"ok": 3, "changed": 1, "failed": 0, "dark": 0}}
        """
        # 1. 获取基础状态
        status_info = self.get_job_status(job_id)
        bamboo_status = status_info["bamboo_status"]

        # 2. 获取 artifacts（set_stats 数据）
        artifacts = self.get_artifacts(job_id)

        # 3. 获取 stdout
        stdout = self.get_stdout(job_id)

        # 4. 从 stdout 末尾尝试解析单行 JSON（兼容无 set_stats 的场景）
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

        # 5. 汇总事件统计
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
            "events": events[:200],          # 最多 200 条事件
            "stdout": stdout,
            "elapsed": status_info.get("elapsed", 0),
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # 主动轮询（核心方法）
    # ------------------------------------------------------------------

    def poll_job(self, job_id: int, *,
                 timeout: int = 3600,
                 execution_id: Optional[str] = None,
                 node_id: Optional[str] = None,
                 on_status_change: Optional[Callable] = None) -> dict:
        """主动轮询 Tower 作业直到完成

        Args:
            job_id: Tower 作业 ID
            timeout: 最大等待秒数（默认 3600 = 1 小时）
            execution_id: 执行 ID（用于 WebSocket 推送）
            node_id: 节点 ID（用于 WebSocket 推送）
            on_status_change: 可选回调 (status_info: dict) → None

        Returns:
            extract_result() 的完整结果

        Raises:
            TowerTimeoutError: 轮询超时
            TowerJobError: 请求失败
        """
        start_time = time.time()
        last_status = ""

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TowerTimeoutError(
                    f"Tower Job {job_id} 轮询超时（>{timeout}秒）"
                )

            # 查询状态
            try:
                status_info = self.get_job_status(job_id)
            except requests.RequestException as e:
                logger.warning("[Tower] 轮询失败 job_id=%s: %s，继续重试", job_id, e)
                time.sleep(5)
                continue

            current_status = status_info["status"]
            bamboo_status = status_info["bamboo_status"]

            # 状态变化时触发回调 + 推送
            if current_status != last_status:
                logger.info("[Tower] 作业状态变化 job_id=%s: %s → %s (elapsed=%.1fs)",
                            job_id, last_status or "init", current_status, elapsed)
                last_status = current_status

                # 提取进度信息（从 result_stdout 粗略估算）
                stdout_text = status_info.get("result_stdout", "")
                progress = self._estimate_progress(stdout_text)

                # WebSocket 推送
                self._emit_ws_status(
                    execution_id=execution_id,
                    node_id=node_id,
                    tower_status=current_status,
                    bamboo_status=bamboo_status,
                    progress=progress,
                    artifacts={},
                )

                # 业务回调
                if on_status_change:
                    on_status_change(status_info)

            # 终止状态检测
            if current_status in ("successful", "failed", "error", "canceled"):
                logger.info("[Tower] 作业完成 job_id=%s status=%s elapsed=%.1fs",
                            job_id, current_status, elapsed)
                result = self.extract_result(job_id)
                # 推送最终状态（含 artifacts）
                self._emit_ws_status(
                    execution_id=execution_id,
                    node_id=node_id,
                    tower_status=current_status,
                    bamboo_status=result["status"],
                    progress=100,
                    artifacts=result["artifacts"],
                )
                return result

            # 自适应等待
            interval = self._get_adaptive_interval(elapsed)
            time.sleep(interval)

    @staticmethod
    def _get_adaptive_interval(elapsed: float) -> int:
        """自适应轮询间隔

        前 30 秒 → 每 3 秒（快速感知启动）
        30秒~5分钟 → 每 5 秒
        5分钟~30分钟 → 每 10 秒
        30分钟以上 → 每 30 秒
        """
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
        # 统计 "TASK [" 行数作为进度指标
        task_lines = [l for l in lines if "TASK [" in l]
        ok_lines = [l for l in lines if "ok:" in l or "changed:" in l]
        if not task_lines:
            return 0
        # 假设每个 task 对应一个 ok/changed 行
        done = len(ok_lines)
        total = max(len(task_lines), done + 1)
        return min(int(done / total * 100), 99)

    @staticmethod
    def _emit_ws_status(execution_id: Optional[str], node_id: Optional[str],
                        tower_status: str, bamboo_status: str,
                        progress: int, artifacts: dict):
        """通过 Django Channels 推送 Tower 作业状态到前端"""
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

    # ------------------------------------------------------------------
    # 便利方法 — 组装 extra_vars
    # ------------------------------------------------------------------

    @staticmethod
    def build_extra_vars(atom_type: str, params: dict,
                         target_hosts: Optional[list] = None,
                         global_vars: Optional[dict] = None) -> dict:
        """组装 Tower Job 的 extra_vars

        按 Tower (AWX) 规范，extra_vars 是扁平 JSON 字典，
        Tower 会自动注入到 Ansible playbook 的变量空间。
        """
        extra_vars = {
            "opsflow_atom_type": atom_type,
        }
        if target_hosts:
            extra_vars["opsflow_target_hosts"] = target_hosts
        if global_vars:
            extra_vars.update(global_vars)
        extra_vars.update(params)
        return extra_vars


# 全局单例
_tower_service: Optional[TowerService] = None


def get_tower_service() -> TowerService:
    """获取 TowerService 单例"""
    global _tower_service
    if _tower_service is None:
        _tower_service = TowerService()
    return _tower_service
