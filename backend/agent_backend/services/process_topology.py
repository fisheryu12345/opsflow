"""进程拓扑匹配引擎

接收所有 agent 上报的 ProcessCollectBody，交叉匹配 remote_connections
与 listen_addresses，建立 Neo4j CALLS 关系。
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 简单内存锁，防止拓扑重建并发
_rebuild_lock = False


def schedule_rebuild():
    """调度一次异步拓扑重建"""
    global _rebuild_lock
    if _rebuild_lock:
        return
    _rebuild_lock = True
    try:
        from django.db import connection
        connection.close()
        rebuild_topology()
    finally:
        _rebuild_lock = False


def rebuild_topology():
    """全量重建进程拓扑：收集所有 agent 上报的进程数据，
    构建 listen_map 并交叉匹配 CALLS 关系"""
    logger.info("[Topology] Starting full rebuild")

    try:
        from agent_backend.models.collect import AgentCollect
        from agent_backend.models.agent_instance import AgentInstance
    except ImportError:
        logger.warning("[Topology] agent_backend models not available")
        return

    # 1. 读取所有 agent 最近上报的 process 采集数据
    process_collects = AgentCollect.objects.filter(
        collect_type='process',
        status='enabled',
    ).select_related('agent')

    all_processes = []  # [{agent_id, host_instance_id, processes, connections}]
    for pc in process_collects:
        data = pc.last_data or {}
        agent = pc.agent
        host_id = getattr(agent, 'host_instance_id', '') or getattr(agent, 'agent_id', '')

        entry = {
            'agent_id': agent.agent_id,
            'host_instance_id': host_id,
            'processes': data.get('processes', []),
            'connections': data.get('connections', []),
        }
        all_processes.append(entry)

    if not all_processes:
        logger.info("[Topology] No process data to process")
        return

    logger.info("[Topology] Building topology from %d agent reports", len(all_processes))

    # 2. 构建 listen_map: {ip:port → process_key}
    listen_map = {}
    process_by_key = {}  # {process_key → {name, host, pid, cmdb_id}}

    for entry in all_processes:
        for proc in entry['processes']:
            key = _proc_key(entry['host_instance_id'], proc.get('pid', 0))
            process_by_key[key] = {
                'name': proc.get('name', ''),
                'host': entry['host_instance_id'],
                'pid': proc.get('pid'),
                'source': proc.get('source', 'discovery'),
                'service_unit': proc.get('service_unit', ''),
            }
            for addr in proc.get('listen_addrs', []):
                for listen_ip in (addr.get('ip', '0.0.0.0'), '0.0.0.0'):
                    map_key = f"{listen_ip}:{addr.get('port', 0)}"
                    listen_map[map_key] = key

    # 3. 遍历所有 connections 进行匹配
    calls_found = []
    for entry in all_processes:
        src_host = entry['host_instance_id']
        for conn in entry.get('connections', []):
            map_key = f"{conn.get('remote_ip', '')}:{conn.get('remote_port', 0)}"
            dst_key = listen_map.get(map_key)
            if dst_key:
                src_key = _proc_key(src_host, conn.get('local_port', 0))
                calls_found.append({'src': src_key, 'dst': dst_key})

    # 4. 写入 Neo4j
    created = _write_calls_to_neo4j(calls_found, process_by_key)

    # 5. 差异对比：标记已消失的进程为 stopped
    _cleanup_stale_processes(all_processes)

    logger.info("[Topology] Rebuild complete: %d CALLS relationships, stale cleanup done", created)


def _cleanup_stale_processes(current_reports: list, _logger=None):
    """将本轮上报中消失的进程标记为 stopped"""
    current_keys = set()
    for entry in current_reports:
        for proc in entry.get('processes', []):
            key = _proc_key(entry['host_instance_id'], proc.get('pid', 0))
            current_keys.add(key)
    try:
        from agent_backend.models.collect import AgentCollect
        from cmdb.services.node_service import NodeService
        old_collects = AgentCollect.objects.filter(
            collect_type='process', status='enabled',
        ).exclude(last_data={})
        ns = NodeService('Process')
        for oc in old_collects:
            data = oc.last_data or {}
            host_id = getattr(oc.agent, 'host_instance_id', '') or getattr(oc.agent, 'agent_id', '')
            for proc in data.get('processes', []):
                key = _proc_key(host_id, proc.get('pid', 0))
                if key not in current_keys:
                    instance_id = proc.get('instance_id', '')
                    if instance_id:
                        try:
                            ns.update(instance_id, {'status': 'stopped'})
                        except Exception:
                            pass
    except Exception:
        pass


def _proc_key(host_id: str, pid: int) -> str:
    return f"{host_id}:{pid}"


def _write_calls_to_neo4j(calls: list, proc_map: dict) -> int:
    """将 CALLS 关系写入 Neo4j（复用现有 CMDB association service）"""
    count = 0
    try:
        from cmdb.services.association_service import AssociationService
        from cmdb.models import AssociationType

        asst_type = AssociationType.objects.filter(asst_id='CALLS').first()
        if not asst_type:
            logger.warning("[Topology] CALLS association type not found in CMDB")
            return 0

        svc = AssociationService()
        for call in calls:
            src_info = proc_map.get(call['src'])
            dst_info = proc_map.get(call['dst'])
            if not src_info or not dst_info:
                continue

            try:
                # 通过 CMDB 的 create_relation 方法写入 Neo4j
                # 如果关系已存在则跳过（幂等）
                svc.create_relation(
                    src_id=call['src'],
                    dst_id=call['dst'],
                    asst_type_id='CALLS',
                )
                count += 1
            except Exception as e:
                logger.debug("[Topology] Skip duplicate CALLS %s → %s: %s",
                             call['src'], call['dst'], e)
    except Exception as e:
        logger.exception("[Topology] Failed to write CALLS to Neo4j: %s", e)

    return count
