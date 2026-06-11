"""Ansible Tower HTTP 触发器 — 通过 Tower REST API 执行原子操作

执行流程:
  1. execute_atom() → POST /api/v2/job_templates/{id}/launch/ → job_id
  2. poll_job() → 自适应间隔轮询 + WebSocket 推送
  3. extract_result() → GET artifacts/events/stdout → 结构化结果
  4. context 注入 → bamboo-engine 继续调度

向后兼容:
  - 未配置 Tower URL 时自动降级为本地模拟执行 (_mock_execute)
  - 已配 Tower URL 但 localhost 时也降级（开发环境）
"""

import json
import logging
from typing import Optional

from .tower_service import (
    TowerService,
    get_tower_service,
    TowerConfigError,
    TowerTimeoutError,
)

logger = logging.getLogger(__name__)


def execute_atom(node: dict, target_hosts: Optional[list] = None,
                 execution_id: Optional[str] = None,
                 node_id: Optional[str] = None,
                 user_id: Optional[int] = None) -> dict:
    """执行一个原子节点

    1. 组装 extra_vars
    2. POST 到 Tower Job Template
    3. 主动轮询等待完成
    4. 提取结果 (artifacts / stdout / events)
    5. 返回结构化结果

    Args:
        node: {"atom_type": str, "params": dict, "id": str}
        target_hosts: 目标主机列表
        execution_id: 执行 ID（用于 WebSocket 推送）
        node_id: 节点 ID（用于 WebSocket 推送）
        user_id: 创建者用户 ID（用于 WebSocket 推送）

    Returns:
        {"stdout": str, "stderr": str, "returncode": int,
         "job_id": int, "artifacts": dict, "events": list,
         "summary": dict, "elapsed": float}
    """
    tower = get_tower_service()

    # 未配置 Tower → 降级为模拟执行
    if not tower.is_configured():
        return _mock_execute(node.get("atom_type", "shell"), node.get("params", {}))

    atom_type = node.get("atom_type", "shell")
    params = node.get("params", {})
    node_ident = node_id or node.get("id", "")

    # 组装 extra_vars
    extra_vars = tower.build_extra_vars(
        atom_type=atom_type,
        params=params,
        target_hosts=target_hosts,
    )

    try:
        # Step 1: 触发作业
        launch_result = tower.launch_job(
            extra_vars=extra_vars,
        )
        job_id = launch_result["job_id"]

        if not job_id:
            logger.error("[AnsibleTrigger] 触发作业后未获取到 job_id")
            return _mock_execute(atom_type, params)

        logger.info("[AnsibleTrigger] 作业已触发 atom=%s job_id=%s", atom_type, job_id)

        # Step 2: 主动轮询（含 WebSocket 推送）
        result = tower.poll_job(
            job_id,
            user_id=user_id,
            execution_id=execution_id,
            node_id=node_ident,
        )

        # Step 3: 组装返回
        success = result["status"] == "success"
        artifacts = result.get("artifacts", {})

        return {
            "stdout": result.get("stdout", ""),
            "stderr": "",
            "returncode": 0 if success else 1,
            "job_id": job_id,
            "artifacts": artifacts,
            "structured": result.get("structured", {}),
            "events": result.get("events", []),
            "summary": result.get("summary", {}),
            "elapsed": result.get("elapsed", 0),
        }

    except TowerTimeoutError as e:
        logger.error("[AnsibleTrigger] 轮询超时 atom=%s: %s", atom_type, e)
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "job_id": 0,
            "artifacts": {},
            "events": [],
            "summary": {},
            "elapsed": 0,
        }
    except (TowerConfigError, Exception) as e:
        logger.exception("[AnsibleTrigger] 执行失败 atom=%s", atom_type)
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "job_id": 0,
            "artifacts": {},
            "events": [],
            "summary": {},
            "elapsed": 0,
        }


def poll_job(job_id: int, execution_id: Optional[str] = None,
             node_id: Optional[str] = None,
             user_id: Optional[int] = None) -> dict:
    """轮询 Tower 作业状态（外部调用用）

    返回: {"stdout": str, "stderr": str, "returncode": int}
    """
    tower = get_tower_service()
    try:
        result = tower.poll_job(
            job_id,
            user_id=user_id,
            execution_id=execution_id,
            node_id=node_id,
        )
        success = result["status"] == "success"
        return {
            "stdout": result.get("stdout", ""),
            "stderr": "",
            "returncode": 0 if success else 1,
            "artifacts": result.get("artifacts", {}),
        }
    except (TowerTimeoutError, Exception) as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


def execute_rollback(node: dict, target_hosts: Optional[list] = None,
                     execution_id: Optional[str] = None,
                     node_id: Optional[str] = None) -> dict:
    """执行插件回滚 — 从插件注册中心获取插件并调用 rollback 方法"""
    from opsflow.plugins.registry import get_plugin
    atom_type = node.get("atom_type", "")
    plugin_cls = get_plugin(atom_type)
    if plugin_cls:
        try:
            plugin = plugin_cls()
            params = node.get("params", {}).copy()
            result = plugin.rollback(context={}, **params)
            if result.get("success"):
                return {
                    "stdout": json.dumps(result.get("data", {}), ensure_ascii=False),
                    "stderr": "",
                    "returncode": 0,
                    "job_id": 0,
                    "artifacts": result.get("data", {}),
                    "events": [],
                    "summary": {"ok": 1, "changed": 0, "failed": 0, "dark": 0, "skipped": 0},
                    "elapsed": 0,
                }
        except Exception as e:
            logger.exception("[AnsibleTrigger] 回滚执行失败 atom=%s", atom_type)
            return {
                "stdout": "", "stderr": str(e), "returncode": -1,
                "job_id": 0, "artifacts": {}, "events": [],
                "summary": {}, "elapsed": 0,
            }
    return {
        "stdout": "", "stderr": "无可用的回滚策略", "returncode": -1,
        "job_id": 0, "artifacts": {}, "events": [],
        "summary": {}, "elapsed": 0,
    }


def _mock_execute(atom_type: str, params: dict) -> dict:
    """本地模拟执行 — 用于开发/调试阶段

    当 Tower 未配置或 URL 指向 localhost 时自动降级。
    模拟结果包含结构化数据，便于前端开发和 gateway 条件测试。
    """
    mock_outputs = {
        "shell": (
            f"模拟执行 shell 命令: {params.get('command', '')}"
        ),
        "disk_check": (
            "Filesystem      Size  Used Avail Use%\n"
            "/dev/sda1       100G   45G   55G  45%"
        ),
        "ping_test": (
            f"PING {params.get('target_host', 'localhost')} ... "
            "64 bytes received, 0% loss"
        ),
        "service_control": (
            f"模拟 {params.get('action', 'status')} "
            f"服务 {params.get('service', '')}"
        ),
        "health_check": '{"status": "healthy", "response_time_ms": 120}',
        "backup_file": (
            f"模拟备份 {params.get('src', '')} → "
            f"{params.get('backup_dir', '/backup')}/"
        ),
        "upload_file": (
            f"模拟上传 {params.get('src', '')} → "
            f"{params.get('dest', '')}"
        ),
        "file_copy": (
            f"模拟复制 {params.get('src', '')} → "
            f"{params.get('dest', '')}"
        ),
        "script_exec": (
            f"模拟执行脚本 ({params.get('script_type', 'bash')}): "
            f"{params.get('script_content', '')[:50]}..."
        ),
        "nginx_reload": '{"config_valid": true, "reload_success": true}',
        "docker_deploy": (
            f'模拟部署 Docker: {params.get("image", "")} → '
            f'{params.get("container_name", "")}'
        ),
        "java_deploy": (
            f'模拟部署 Java: {params.get("artifact_path", "")} → '
            f'{params.get("target_path", "/opt/app")}'
        ),
        "send_alert": (
            f'模拟发送告警 [{params.get("channel", "wecom")}]: '
            f'{params.get("title", "")}'
        ),
    }

    output = mock_outputs.get(
        atom_type,
        f"模拟执行 {atom_type}: {json.dumps(params, ensure_ascii=False)}",
    )

    return {
        "stdout": output,
        "stderr": "",
        "returncode": 0,
        "job_id": 0,
        "artifacts": {},
        "events": [],
        "summary": {"ok": 1, "changed": 1, "failed": 0, "dark": 0, "skipped": 0},
        "elapsed": 0.5,
    }
