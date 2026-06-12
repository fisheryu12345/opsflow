"""进程状态检查 — 通过 Ansible Tower 检查远程进程状态

输出:
  - status: running / stopped
  - pid: 进程 PID
  - cpu_percent: CPU 使用率
  - memory_mb: 内存占用
  - listen_addresses: 当前监听端口
  - remote_connections: 当前活跃连接
"""
import logging

from opsflow.plugins.ansible.tower_backend.base_plugin import TowerBasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule

logger = logging.getLogger(__name__)


class ProcessStatusPlugin(TowerBasePlugin):
    code = "process_status"
    name = "进程状态检查"
    name_en = "Process Status"
    group = "Process"
    description = "检查远程进程的运行状态和资源占用"
    risk_level = "low"

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
        ]

    def execute(self, instance_id: str = "", **kwargs) -> dict:
        """检查远程进程状态"""
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
        process_name = proc_data.get("name", "unknown")

        # 2. 通过 Tower 执行进程检查
        tower = self._get_tower()
        if not tower.is_configured():
            return self._mock_execute(name=process_name, pid=pid)

        check_cmd = f"ps -p {pid} -o pid,user,%cpu,%mem,args --no-headers 2>/dev/null || echo 'NOT_RUNNING'"
        if not pid or pid <= 0:
            check_cmd = f"pgrep -x {process_name} || echo 'NOT_RUNNING'"

        extra_vars = {
            "opsflow_atom_type": "process_status",
            "command": check_cmd,
            "process_instance_id": instance_id,
        }
        try:
            launch_result = tower.launch_job(extra_vars=extra_vars)
            job_id = launch_result["job_id"]
            if not job_id:
                return self._mock_execute(name=process_name, pid=pid)

            logger.info("[ProcessStatus] Job triggered: %s", job_id)
            return {
                "success": True,
                "data": {
                    "tower_job_id": job_id,
                    "tower_status": "pending",
                    "process_instance_id": instance_id,
                },
            }
        except Exception as e:
            logger.exception("[ProcessStatus] Failed to launch Tower job")
            return {"success": False, "data": {}, "error": str(e)}

    def schedule(self, context: dict, **kwargs) -> bool | None:
        """覆盖父类 schedule，解析 ps 输出为结构化字段"""
        tower_job_id = context.get("tower_job_id")
        if not tower_job_id:
            return False

        tower = self._get_tower()
        try:
            status_info = tower.get_job_status(tower_job_id)
            current_status = status_info["status"]

            if current_status in ("successful",):
                result = tower.extract_result(tower_job_id)
                stdout = result.get("stdout", "")
                # 解析 ps 输出
                if "NOT_RUNNING" in stdout or not stdout.strip():
                    context.update({
                        "status": "stopped", "pid": 0,
                        "cpu_percent": 0, "memory_mb": 0,
                        "listen_addresses": [], "remote_connections": [],
                    })
                else:
                    # ps output: "PID USER %CPU %MEM ARGS"
                    parts = stdout.strip().split()
                    context.update({
                        "status": "running" if parts else "stopped",
                        "pid": int(parts[0]) if len(parts) > 0 else 0,
                        "cpu_percent": float(parts[2]) if len(parts) > 2 else 0,
                        "memory_mb": round(float(parts[3]) if len(parts) > 3 else 0, 1),
                    })
                context["tower_status"] = "success"
                return True
            elif current_status in ("failed", "error", "canceled"):
                return False
            else:
                return None
        except Exception as e:
            logger.warning("[ProcessStatus] Poll error: %s", e)
            return None

    def _get_tower(self):
        from opsflow.plugins.ansible.tower_backend import get_tower_service
        return get_tower_service()

    def _mock_execute(self, name: str = "", pid: int = 0) -> dict:
        return {
            "success": True,
            "data": {
                "status": "running" if pid > 0 else "stopped",
                "pid": pid,
                "cpu_percent": 2.5,
                "memory_mb": 128,
                "stdout": f"[Mock] Process {name} status check: {'running' if pid > 0 else 'stopped'}",
                "tower_job_id": 0,
                "tower_status": "mock",
            },
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "status", "type": "string", "description": "进程状态 running/stopped"},
            {"name": "pid", "type": "int", "description": "进程 PID"},
            {"name": "cpu_percent", "type": "float", "description": "CPU 使用率"},
            {"name": "memory_mb", "type": "float", "description": "内存占用(MB)"},
        ]
