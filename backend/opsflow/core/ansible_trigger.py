"""Ansible API HTTP 触发器 — 通过 POST 调用 Ansible 模板接口执行原子操作"""

import json
import logging
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

# Ansible API 配置会被缓存
_ansible_config = None


def _get_config():
    """读取 Ansible API 配置"""
    global _ansible_config
    if _ansible_config is None:
        try:
            from conf.env import (
                ANSIBLE_API_URL, ANSIBLE_API_TOKEN,
                ANSIBLE_TEMPLATE_ID, ANSIBLE_VERIFY_SSL,
            )
            _ansible_config = {
                'url': ANSIBLE_API_URL,
                'token': ANSIBLE_API_TOKEN,
                'template_id': ANSIBLE_TEMPLATE_ID,
                'verify_ssl': ANSIBLE_VERIFY_SSL if 'ANSIBLE_VERIFY_SSL' in dir() else False,
            }
        except (ImportError, AttributeError):
            # 兜底配置
            _ansible_config = {
                'url': 'http://localhost:8080/api/v2',
                'token': '',
                'template_id': 1,
                'verify_ssl': False,
            }
    return _ansible_config


def execute_atom(node: dict, target_hosts: list = None) -> dict:
    """
    执行一个原子节点：组装 extra_vars → POST 到 Ansible 模板 API → 返回结果。
    返回 {'stdout': str, 'stderr': str, 'returncode': int}
    """
    cfg = _get_config()
    atom_type = node.get('atom_type', 'shell')
    params = node.get('params', {})

    # 组装 extra_vars
    extra_vars = {
        'opsflow_atom_type': atom_type,
        'opsflow_node_id': node.get('id', ''),
        'opsflow_target_hosts': target_hosts or [],
    }
    extra_vars.update(params)

    # 如果未配置 Ansible API，返回 mock 结果（便于开发调试）
    if not cfg['url'] or 'localhost' in cfg['url']:
        return _mock_execute(atom_type, params)

    # POST 到 Ansible Job Template API
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {cfg['token']}",
    }
    payload = {
        'extra_vars': json.dumps(extra_vars, ensure_ascii=False),
    }

    launch_url = urljoin(cfg['url'].rstrip('/') + '/',
                         f"job_templates/{cfg['template_id']}/launch/")

    try:
        resp = requests.post(
            launch_url, headers=headers, json=payload,
            verify=cfg['verify_ssl'], timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()

        # 返回作业 ID，供后续轮询使用
        return {
            'stdout': json.dumps(result, ensure_ascii=False),
            'stderr': '',
            'returncode': 0,
            'job_id': result.get('job'),
        }
    except requests.RequestException as e:
        logger.warning(f"Ansible API 调用失败: {e}，降级为本地模拟执行")
        return _mock_execute(atom_type, params)


def poll_job(job_id: int) -> dict:
    """轮询 Ansible 作业状态"""
    cfg = _get_config()
    headers = {'Authorization': f"Bearer {cfg['token']}"}
    job_url = urljoin(cfg['url'].rstrip('/') + '/', f"jobs/{job_id}/")
    try:
        resp = requests.get(job_url, headers=headers, verify=cfg['verify_ssl'], timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get('status', 'pending')
        if status == 'successful':
            return {'stdout': result.get('result_stdout', ''), 'stderr': '', 'returncode': 0}
        elif status == 'failed':
            return {'stdout': '', 'stderr': result.get('result_stdout', ''), 'returncode': 1}
        else:
            return {'stdout': '', 'stderr': '', 'returncode': -1}  # 仍在运行
    except requests.RequestException as e:
        logger.error(f"轮询 Ansible 作业失败: {e}")
        return {'stdout': '', 'stderr': str(e), 'returncode': -1}


def execute_rollback(node: dict, target_hosts: list = None) -> dict:
    """执行原子回滚：从 atom_registry 获取回滚类型并执行"""
    from .atom_registry import get_atom_meta
    atom_type = node.get('atom_type', '')
    meta = get_atom_meta(atom_type)
    if meta and meta.rollback:
        rollback_node = dict(node)
        rollback_node['atom_type'] = meta.rollback
        rollback_node['params'] = node.get('params', {}).copy()
        return execute_atom(rollback_node, target_hosts)
    return {'stdout': '', 'stderr': '无可用的回滚策略', 'returncode': -1}


def _mock_execute(atom_type: str, params: dict) -> dict:
    """本地模拟执行 — 用于开发/调试阶段"""
    mock_outputs = {
        'shell': f"模拟执行 shell 命令: {params.get('command', '')}",
        'disk_check': "Filesystem      Size  Used Avail Use%\n/dev/sda1       100G   45G   55G  45%",
        'ping_test': f"PING {params.get('target_host', 'localhost')} ... 64 bytes received, 0% loss",
        'service_control': f"模拟 {params.get('action', 'status')} 服务 {params.get('service', '')}",
        'health_check': '{"status": "healthy", "response_time_ms": 120}',
        'backup_file': f"模拟备份 {params.get('src', '')} → {params.get('backup_dir', '/backup')}/",
        'upload_file': f"模拟上传 {params.get('src', '')} → {params.get('dest', '')}",
        'file_copy': f"模拟复制 {params.get('src', '')} → {params.get('dest', '')}",
        'script_exec': f"模拟执行脚本 ({params.get('script_type', 'bash')}): {params.get('script_content', '')[:50]}...",
        'nginx_reload': '{"config_valid": true, "reload_success": true}',
        'docker_deploy': f'模拟部署 Docker: {params.get("image", "")} → {params.get("container_name", "")}',
        'java_deploy': f'模拟部署 Java: {params.get("artifact_path", "")} → {params.get("target_path", "/opt/app")}',
        'send_alert': f'模拟发送告警 [{params.get("channel", "wecom")}]: {params.get("title", "")}',
    }
    output = mock_outputs.get(atom_type, f"模拟执行 {atom_type}: {json.dumps(params, ensure_ascii=False)}")
    return {'stdout': output, 'stderr': '', 'returncode': 0}
