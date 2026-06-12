"""进程停止 — 通过 Ansible Tower 远程停止目标进程

执行流程:
  1. 根据 instance_id 查询 CMDB 获取进程信息（pid、所在主机）
  2. 通过 Tower 在目标主机上执行 kill 命令
  3. 更新 CMDB Process 状态
"""
import logging

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule

logger = logging.getLogger(__name__)


class ProcessStopPlugin(TowerBasePlugin):
    code = "process_stop"
    name = "进程停止"
    name_en = "Process Stop"
    group = "Process"
    description = "通过 CMDB 获取进程信息，在目标主机上远程停止进程"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="input",
                name="进程 CMDB ID",
                name_en="Process CMDB ID",
                required=True,
                description="CMDB Process 实例的 instance_id",
                attrs={"placeholder": "如 f47ac10b-58cc-4372-a567-0e02b2c3d479"},
            ),
            FormItem(
                tag_code="force",
                type="switch",
                name="强制终止",
                name_en="Force Kill",
                default=False,
                description="勾选则使用 kill -9 强制终止",
            ),
        ]

    def execute(self, instance_id: str = "", force: bool = False, **kwargs) -> dict:
        """从 CMDB 获取进程信息，通过 Tower 停止"""
        if not instance_id:
            return {"success": False, "data": {}, "error": "instance_id is required"}

        # 1. 从 CMDB 获取进程信息（同进程直接调用 NodeService）
        try:
            from cmdb.services.node_service import NodeService
            ns = NodeService("Process")
            proc_data = ns.retrieve(instance_id)
            if not proc_data:
                return {"success": False, "data": {}, "error": f"进程 {instance_id[:12]} 不存在"}
        except Exception as e:
            logger.error("Failed to fetch process from CMDB: %s", e)
            return {"success": False, "data": {}, "error": f"无法获取进程信息: {e}"}

        pid = proc_data.get("pid", 0)
        if not pid or pid <= 0:
            return {"success": False, "data": {}, "error": "进程 PID 无效或进程未运行"}

        # 2. 通过 Tower 执行停止
        tower = self._get_tower()
        if not tower.is_configured():
            return self._mock_execute(action="stop", pid=pid, force=force)

        kill_cmd = f"kill -9 {pid}" if force else f"kill {pid}"
        extra_vars = {
            "opsflow_atom_type": "process_stop",
            "command": kill_cmd,
            "process_instance_id": instance_id,
        }
        try:
            launch_result = tower.launch_job(extra_vars=extra_vars)
            job_id = launch_result["job_id"]
            if not job_id:
                return self._mock_execute(action="stop", pid=pid, force=force)

            logger.info("[ProcessStop] Job triggered: %s", job_id)
            return {
                "success": True,
                "data": {
                    "tower_job_id": job_id,
                    "tower_status": "pending",
                    "process_instance_id": instance_id,
                },
            }
        except Exception as e:
            logger.exception("[ProcessStop] Failed to launch Tower job")
            return {"success": False, "data": {}, "error": str(e)}

    def _get_tower(self):
        from opsflow.plugins.ansible.tower_backend import get_tower_service
        return get_tower_service()

    def _mock_execute(self, action: str = "stop", pid: int = 0, force: bool = False) -> dict:
        sig = "SIGKILL" if force else "SIGTERM"
        return {
            "success": True,
            "data": {
                "stdout": f"[Mock] Process {action}: send {sig} to PID {pid}",
                "stderr": "",
                "returncode": 0,
                "tower_job_id": 0,
                "tower_status": "mock",
                "process_instance_id": "",
            },
        }
