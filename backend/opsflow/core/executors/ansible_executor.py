"""Ansible 执行器 — 通过 Ansible Tower (AWX) REST API 执行原子

executor_type: "ansible"
底层技术: ansible_trigger → TowerService (POST /api/v2/job_templates/{id}/launch/)

执行流程:
  1. execute(): 触发 Tower Job + 主动轮询等待完成 + 提取 artifacts
  2. 返回结构化结果（含 artifacts/events/summary）供 gateway 条件求值
  3. 未配置 Tower 时自动降级为本地模拟执行

已有原子（均使用此执行器）:
  shell, disk_check, ping_test, health_check, backup_file,
  upload_file, file_copy, script_exec, nginx_reload,
  docker_deploy, java_deploy, service_control, send_alert
"""

import logging

from .base import BaseExecutor, ExecuteResult
from .. import ansible_trigger

logger = logging.getLogger(__name__)


class AnsibleExecutor(BaseExecutor):
    """Ansible 原子执行器 — 通过 Ansible Tower 异步执行 + 主动轮询"""

    executor_type = "ansible"

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行原子操作

        inputs 中:
          - _atom_type: str (原子类型名称)
          - _target_hosts: list (目标主机)
          - _execution_id: str (可选，用于 WebSocket 推送)
          - _node_id: str (可选，对应 flow_engine 中的 node_id)
          其他字段根据 atom_type 的 meta.json inputs 定义
        """
        atom_type = inputs.get("_atom_type", "")
        params = {k: v for k, v in inputs.items() if not k.startswith("_")}
        target_hosts = inputs.get("_target_hosts", [])
        execution_id = inputs.get("_execution_id", "")
        node_id = inputs.get("_node_id", "")

        node = {
            "atom_type": atom_type,
            "params": params,
            "id": node_id,
        }

        logger.info("[AnsibleExecutor] execute atom=%s hosts=%s ex_id=%s",
                    atom_type, target_hosts, execution_id)

        try:
            # 执行（触发 Tower → 轮询 → 提取结果）
            result = ansible_trigger.execute_atom(
                node, target_hosts,
                execution_id=execution_id,
                node_id=node_id,
            )
            success = result.get("returncode", 0) == 0

            return ExecuteResult(
                success=success,
                data={
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode", 0),
                    "job_id": result.get("job_id", 0),
                    # Tower 结构化结果 — 供 gateway 条件求值和 context 注入
                    "artifacts": result.get("artifacts", {}),
                    "structured": result.get("structured", {}),
                    "events": result.get("events", []),
                    "summary": result.get("summary", {}),
                    "elapsed": result.get("elapsed", 0),
                },
            )
        except Exception as e:
            logger.exception("Ansible 执行失败 atom=%s", atom_type)
            return ExecuteResult(False, {}, str(e))

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 调用 ansible_trigger.execute_rollback()"""
        atom_type = inputs.get("_atom_type", "")
        node = {
            "atom_type": atom_type,
            "params": {k: v for k, v in inputs.items() if not k.startswith("_")},
        }
        target_hosts = inputs.get("_target_hosts", [])

        try:
            result = ansible_trigger.execute_rollback(node, target_hosts)
            success = result.get("returncode", 0) == 0
            return ExecuteResult(
                success=success,
                data={
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode", 0),
                },
            )
        except Exception as e:
            logger.exception("Ansible 回滚失败 atom=%s", atom_type)
            return ExecuteResult(False, {}, str(e))
