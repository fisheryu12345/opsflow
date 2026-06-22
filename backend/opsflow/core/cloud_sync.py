# -*- coding: utf-8 -*-
"""阿里云 ECS → CMDB 实时同步

Pipeline 执行 ECS 操作原子后，立即同步实例状态到 CMDB :Host 节点。

用法（由 plugin_service_adapter.py 自动调用）:
    from opsflow.core.cloud_sync import sync_after_execution
    sync_after_execution(atom_type, params, result, execution_id)
"""

import json
import logging

logger = logging.getLogger(__name__)

# 需要触发同步的原子类型
SYNC_ACTIONS = {
    'aliyun_ecs_create': ('create', True),    # (action, needs_instance_id)
    'aliyun_ecs_start': ('start', True),
    'aliyun_ecs_stop': ('stop', True),
    'aliyun_ecs_restart': ('restart', True),
    'aliyun_ecs_modify': ('modify', True),
    'aliyun_ecs_delete': ('delete', True),
    'aliyun_ecs_describe': ('describe', False),   # 纯查询，跳过
    'aliyun_ecs_create_image': ('create_image', False),  # 不涉及 Host
}


def sync_after_execution(atom_type: str, params: dict, result: dict, execution_id=None):
    """Pipeline 原子执行成功后触发 CMDB 同步"""
    if atom_type not in SYNC_ACTIONS:
        return
    action, needs_id = SYNC_ACTIONS[atom_type]
    if not needs_id:
        return
    if not result.get('success'):
        return

    instance_id = result.get('data', {}).get('instance_id', '') or params.get('instance_id', '')
    region = params.get('region', '')

    if not instance_id or not region:
        logger.warning("cloud_sync: missing instance_id or region for %s", atom_type)
        return

    try:
        sync_ecs_instance(instance_id, region, action)
        logger.info("cloud_sync: %s %s synced to CMDB", action, instance_id)
    except Exception as e:
        logger.exception("cloud_sync: failed to sync %s %s: %s", action, instance_id, e)


def sync_ecs_instance(instance_id: str, region: str, action: str = 'create'):
    """将单个 ECS 实例同步到 CMDB :Host 节点"""
    from cmdb.services.neo4j_client import graph_driver
    from opsflow.plugins.aliyun_ecs._client import get_ecs_client
    from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest

    client = get_ecs_client(region)
    req = DescribeInstancesRequest()
    req.set_InstanceIds(json.dumps([instance_id]))
    resp = client.do_action_with_exception(req)
    data = json.loads(resp)
    instances = data.get('Instances', {}).get('Instance', [])
    if not instances:
        if action == 'delete':
            # 实例已释放，标记为 deleted
            _mark_host_deleted(instance_id)
        return

    inst = instances[0]
    props = {
        'cloud_instance_id': inst.get('InstanceId', ''),
        'cloud_type': 'aliyun',
        'instance_type': inst.get('InstanceType', ''),
        'ip': _get_private_ip(inst),
        'hostname': inst.get('InstanceName', '') or inst.get('HostName', '') or '',
        'region': inst.get('RegionId', ''),
        'status': inst.get('Status', ''),
        'os_type': 'linux',
        'cpu_cores': inst.get('Cpu', 0),
        'memory_mb': (inst.get('Memory', 0) or 0) * 1024,
    }

    with graph_driver.session() as session:
        session.run(
            """
            MERGE (h:Host {cloud_instance_id: $cid})
            ON CREATE SET h += $props, h.__created_at = toString(datetime()),
                          h.__model_code = 'Host'
            ON MATCH SET h += $props, h.__updated_at = toString(datetime())
            """,
            cid=instance_id, props=props,
        )
        logger.info("cloud_sync: Host %s (%s) synced, status=%s", instance_id, props['ip'], props['status'])


def _get_private_ip(inst: dict) -> str:
    """从 DescribeInstances 响应中提取私网 IP"""
    vpc = inst.get('VpcAttributes', {}) or {}
    ips = vpc.get('PrivateIpAddress', {}).get('IpAddress', [])
    return ips[0] if ips else (inst.get('PrivateIpAddress', '') or '')


def _mark_host_deleted(instance_id: str):
    """标记 Host 节点为 deleted 状态"""
    from cmdb.services.neo4j_client import graph_driver
    with graph_driver.session() as session:
        session.run(
            "MATCH (h:Host {cloud_instance_id: $cid}) "
            "SET h.status = 'deleted', h.__updated_at = toString(datetime())",
            cid=instance_id,
        )
