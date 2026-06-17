# -*- coding: utf-8 -*-
"""Internal API views for Agent Server → Django communication.
   No authentication required — these are server-to-server endpoints.
"""

import json
import logging
import os

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import AgentInstance, AgentTaskExecution, AgentTaskResult

logger = logging.getLogger(__name__)


@csrf_exempt
def batch_results(request):
    """Agent Server 批量写回执行结果"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    results = data.get('results', [])
    for item in results:
        exec_id = item.get('exec_id')
        status = item.get('status', 'running')
        exit_code = item.get('exit_code')
        error_msg = item.get('error_msg', '')

        AgentTaskExecution.objects.filter(exec_id=exec_id).update(
            status=status,
            exit_code=exit_code,
            error_msg=error_msg or '',
        )

        seq = item.get('seq', 1)
        stdout = item.get('stdout', '')
        stderr = item.get('stderr', '')
        is_final = item.get('is_final', False)
        if stdout or stderr:
            AgentTaskResult.objects.create(
                exec_id=exec_id,
                seq=seq,
                is_final=is_final,
                stdout=stdout,
                stderr=stderr,
            )

    return JsonResponse({'code': 2000, 'data': {'processed': len(results)}, 'msg': 'success'})


@csrf_exempt
def collect_reports(request):
    """Agent Server 上报采集数据 — 写入 CMDB Neo4j"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    reports = data if isinstance(data, list) else [data]
    processed = 0
    has_process_data = False

    for item in reports:
        # Unwrap WS envelope if present (Agent Server forwards raw WS message)
        body = item.get('body') if isinstance(item.get('body'), dict) else item
        agent_id = body.get('agent_id')
        collect_type = body.get('collect_type')
        item_data = body.get('data', body)  # prefer data wrapper, fallback to flat fields

        if not collect_type:
            # Try top-level fields (direct API call)
            agent_id = item.get('agent_id', agent_id)
            collect_type = item.get('collect_type', collect_type)
            item_data = item.get('data', item_data)

        if not collect_type:
            continue

        if collect_type == 'host_info' and isinstance(item_data, dict):
            # Update AgentInstance MySQL record (used for frontend display)
            AgentInstance.objects.filter(agent_id=agent_id).update(
                hostname=item_data.get('hostname', '') or '',
                ip=item_data.get('ip', '') or '',
                os_type=item_data.get('os', '') or '',
                os_version=item_data.get('os_version', '') or '',
                arch=item_data.get('arch', '') or '',
            )
            # Sync to CMDB Neo4j
            _sync_host_to_cmdb(agent_id, item_data)
        elif collect_type == 'process':
            _sync_processes_to_cmdb(agent_id, item_data)
            has_process_data = True

        processed += 1

    # Trigger topology rebuild for process data
    if has_process_data:
        _schedule_topology_rebuild()

    return JsonResponse({'code': 2000, 'data': {'processed': processed}, 'msg': 'success'})


def _sync_host_to_cmdb(agent_id: str, data: dict):
    """将 Agent 上报的 host_info 写入 CMDB Neo4j Host 节点（优先 ip，fallback hostname）"""
    try:
        from cmdb.services.neo4j_client import graph_driver
        from uuid import uuid4
        from datetime import datetime

        hostname = data.get('hostname', '') or data.get('ip', '')
        ip = data.get('ip', '')
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        record = {
            'hostname': hostname,
            'ip': ip or '',
            'os_type': data.get('os', 'linux'),
            'os_version': data.get('os_version', ''),
            'cpu_cores': int(data.get('cpu_count', data.get('cpu_cores', 0))),
            'memory_mb': int(data.get('memory_total', data.get('memory_mb', 0))),
            'disk_gb': int(data.get('disk_total', data.get('disk_gb', 0))),
            'region': data.get('region', ''),
            'status': 'normal',
            '__model_code': 'Host',
            '__updated_at': now,
        }
        record = {k: v for k, v in record.items() if v}

        with graph_driver.session() as session:
            if ip:
                result = session.run(
                    "MERGE (h:Host {ip: $ip}) "
                    "ON CREATE SET h += $data, h.instance_id = $instance_id, h.__created_at = $now "
                    "ON MATCH SET h += $data, h.__updated_at = $now "
                    "RETURN h.hostname, h.ip, h.instance_id",
                    ip=ip, data=record, instance_id=str(uuid4()), now=now,
                )
            else:
                # Fallback: MERGE by hostname when no IP available
                result = session.run(
                    "MERGE (h:Host {hostname: $hostname}) "
                    "ON CREATE SET h += $data, h.instance_id = $instance_id, h.__created_at = $now "
                    "ON MATCH SET h += $data, h.__updated_at = $now "
                    "RETURN h.hostname, h.ip, h.instance_id",
                    hostname=hostname, data=record, instance_id=str(uuid4()), now=now,
                )
            for rec in result:
                logger.info("CMDB Host sync: agent=%s hostname=%s ip=%s instance_id=%s",
                            agent_id, rec['h.hostname'], rec['h.ip'], rec['h.instance_id'])

    except Exception as e:
        logger.warning("CMDB sync failed for agent %s: %s", agent_id, e)


def _sync_processes_to_cmdb(agent_id: str, data: dict):
    """将 Agent 上报的 process 采集数据写入 Neo4j Process 节点 + RUNS_ON 关系"""
    processes = data.get('processes', [])
    services = data.get('services', [])
    connections = data.get('connections', [])

    try:
        from cmdb.services.neo4j_client import graph_driver
        from uuid import uuid4
        from datetime import datetime

        # Get host ip from agent or fallback to AgentCollect host_info
        host_ip = ''
        agent = AgentInstance.objects.filter(agent_id=agent_id).first()
        if agent and agent.ip:
            host_ip = agent.ip
        if not host_ip:
            collect = AgentInstance.objects.filter(agent_id=agent_id).first()
            if collect:
                pass

        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Build service PID map
        svc_map = {}
        for svc in services:
            pid = svc.get('main_pid', 0)
            if pid > 0:
                svc_map[pid] = {
                    'unit_name': svc.get('unit_name', ''),
                    'state': svc.get('state', ''),
                    'sub_state': svc.get('sub_state', ''),
                }

        # Mark registered apps from app_registry
        registered_pids = set()
        try:
            from .apps import get_registry_pids
            registered_pids = get_registry_pids(agent_id)
        except Exception:
            pass

        with graph_driver.session() as session:
            # Ensure Host node exists
            if host_ip:
                session.run(
                    "MERGE (h:Host {ip: $ip}) SET h.__updated_at = $now",
                    ip=host_ip, now=now,
                )

            current_keys = set()

            for proc in processes:
                pid = proc.get('pid', 0)
                name = proc.get('name', '') or 'unknown'
                if pid <= 0 and not name:
                    continue

                proc_key = f"{host_ip}:{pid}" if host_ip else f"noip:{pid}"
                current_keys.add(proc_key)
                cmdline = proc.get('cmdline', '') or ''
                listen_addrs = proc.get('listen_addrs', []) or []

                # Determine source
                source = proc.get('source', 'discovery')
                if pid in registered_pids:
                    source = 'agent'
                    registered = True
                else:
                    registered = proc.get('registered', False)

                props = {
                    'name': name,
                    'pid': pid,
                    'user': proc.get('user', '') or '',
                    'cmdline': cmdline[:500] if cmdline else '',
                    'cpu_percent': float(proc.get('cpu_percent', 0)),
                    'memory_mb': float(proc.get('memory_mb', 0)),
                    'status': proc.get('status', 'running'),
                    'source': source,
                    'registered': registered,
                    'listen_addrs': json.dumps(listen_addrs, ensure_ascii=False),
                    'instance_id': str(uuid4()),
                    '__model_code': 'Process',
                    '__updated_at': now,
                }

                # Attach service info if matched
                if pid in svc_map:
                    props['service_unit'] = svc_map[pid]['unit_name']
                    props['service_state'] = svc_map[pid]['state']

                if host_ip:
                    result = session.run(
                        "MERGE (p:Process {host_ip: $host_ip, pid: $pid}) "
                        "ON CREATE SET p += $props, p.__created_at = $now "
                        "ON MATCH SET p += $props, p.__updated_at = $now "
                        "RETURN p.instance_id",
                        host_ip=host_ip, pid=pid, props=props, now=now,
                    )
                    # Create RUNS_ON relationship if host exists
                    session.run(
                        "MATCH (p:Process {host_ip: $host_ip, pid: $pid}), (h:Host {ip: $host_ip}) "
                        "MERGE (p)-[r:RUNS_ON]->(h) "
                        "SET r.__updated_at = $now",
                        host_ip=host_ip, pid=pid, now=now,
                    )

            # Mark processes no longer reported as stopped
            if host_ip:
                session.run(
                    "MATCH (p:Process {host_ip: $host_ip}) "
                    "WHERE p.status <> 'stopped' AND NOT (p.host_ip = $host_ip AND p.pid IN $active_pids) "
                    "SET p.status = 'stopped', p.__updated_at = $now",
                    host_ip=host_ip, active_pids=list({p.get('pid', 0) for p in processes if p.get('pid', 0) > 0}), now=now,
                )

            # ── CALLS topology matching ──
            if host_ip and connections:
                try:
                    _match_calls_topology(session, host_ip, processes, connections, now)
                except Exception as e:
                    logger.warning("CALLS matching failed for agent %s: %s", agent_id, e)

        logger.info("CMDB Process sync: agent=%s processes=%d host_ip=%s",
                     agent_id, len(processes), host_ip)

    except Exception as e:
        logger.warning("CMDB process sync failed for agent %s: %s", agent_id, e)


def _match_calls_topology(session, host_ip, processes, connections, now):
    """Cross‑match connections against all Process listen_addrs → CREATE CALLS relationships"""
    # 1. Build listen map from ALL Process nodes in Neo4j (across all hosts)
    result = session.run(
        "MATCH (p:Process) WHERE p.listen_addrs IS NOT NULL AND p.listen_addrs <> '[]' "
        "RETURN p.host_ip, p.name, p.pid, p.listen_addrs"
    )
    listen_map = {}
    for rec in result:
        proc_host = rec['p.host_ip']
        proc_name = rec['p.name']
        proc_pid = rec['p.pid']
        try:
            addrs = json.loads(rec['p.listen_addrs']) if isinstance(rec['p.listen_addrs'], str) else (rec['p.listen_addrs'] or [])
        except (json.JSONDecodeError, TypeError):
            addrs = []
        for addr in addrs:
            ip = addr.get('ip', '0.0.0.0')
            port = addr.get('port', 0)
            entry = {'host_ip': proc_host, 'name': proc_name, 'pid': proc_pid}
            # Index all possible IP variations for this port
            for wildcard_ip in (ip, '0.0.0.0', '::', '127.0.0.1', 'localhost'):
                listen_map[f"{wildcard_ip}:{port}"] = entry

    # 2. Match each connection → CREATE CALLS (uses pid from agent connection data)
    created = 0
    for conn in connections:
        rem_ip = conn.get('remote_ip', '')
        rem_port = conn.get('remote_port', 0)
        src_pid = conn.get('pid', 0)

        if not rem_ip or not rem_port or not src_pid:
            continue

        # Find destination process by remote_ip:remote_port
        map_key = f"{rem_ip}:{rem_port}"
        dst = listen_map.get(map_key)
        if not dst:
            continue

        # Create CALLS: src → dst
        try:
            session.run(
                "MATCH (src:Process {host_ip: $src_host_ip, pid: $src_pid}) "
                "MATCH (dst:Process {host_ip: $dst_host_ip, pid: $dst_pid}) "
                "MERGE (src)-[r:CALLS]->(dst) "
                "SET r.__updated_at = $now, r.remote_port = $rem_port, r.protocol = $protocol",
                src_host_ip=host_ip, src_pid=src_pid,
                dst_host_ip=dst['host_ip'], dst_pid=dst['pid'],
                now=now, rem_port=rem_port, protocol=conn.get('protocol', 'tcp'),
            )
            created += 1
        except Exception:
            pass

    if created:
        logger.info("CALLS topology: created %d relationships for host %s", created, host_ip)


def _schedule_topology_rebuild():
    """异步触发拓扑重建"""
    try:
        from .services.process_topology import schedule_rebuild
        schedule_rebuild()
    except Exception as e:
        logger.warning("Failed to schedule topology rebuild: %s", e)


@csrf_exempt
def agent_register(request):
    """Agent Server 上报 Agent 注册 — 自动创建或更新 AgentInstance（无认证）"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    agent_id = data.get('agent_id')
    if not agent_id:
        return JsonResponse({'error': 'agent_id required'}, status=400)

    from django.utils import timezone
    now = timezone.now()
    AgentInstance.objects.update_or_create(
        agent_id=agent_id,
        defaults={
            'hostname': data.get('hostname', '') or '',
            'ip': data.get('ip', '') or '',
            'os_type': data.get('os_type', '') or '',
            'os_version': data.get('os_version', '') or '',
            'arch': data.get('arch', '') or '',
            'agent_version': data.get('agent_version', '') or '',
            'status': 'online',
            'last_heartbeat': now,
        },
    )
    logger.info("Agent registered via Server: %s hostname=%s ip=%s", agent_id, data.get('hostname'), data.get('ip'))
    return JsonResponse({'code': 2000, 'data': {'agent_id': agent_id}, 'msg': 'registered'})


@csrf_exempt
def agent_apps(request):
    """注册/注销/列出 Agent 应用 — 同时存 Django DB + 转发 Agent Server"""
    agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:18080')

    if request.method == 'GET':
        agent_id = request.GET.get('agent_id')
        if not agent_id:
            return JsonResponse({'code': 4000, 'msg': 'agent_id required'})

        apps = []
        try:
            agent = AgentInstance.objects.filter(agent_id=agent_id).first()
            if agent:
                tags = agent.tags or {}
                apps = tags.get('registered_apps', [])

                # Enrich with running status from Neo4j Process data
                host_ip = agent.ip or ''
                if host_ip and apps:
                    try:
                        from cmdb.services.neo4j_client import graph_driver
                        with graph_driver.session() as session:
                            for app in apps:
                                app_name = app.get('name', '')
                                if not app_name:
                                    continue
                                # Extract binary basename from command for cmdline fallback matching
                                command = app.get('command', '') or ''
                                cmd_basename = os.path.basename(command.split()[0]) if command.strip() else ''
                                result = session.run(
                                    """
                                    MATCH (p:Process {host_ip: $host_ip, status: 'running'})
                                    WHERE p.name = $name
                                       OR ($cmd_basename <> '' AND (p.name CONTAINS $cmd_basename OR p.cmdline CONTAINS $cmd_basename))
                                    RETURN count(p) > 0 AS is_running
                                    """,
                                    host_ip=host_ip, name=app_name, cmd_basename=cmd_basename,
                                )
                                record = result.single()
                                app['running'] = record['is_running'] if record else False
                    except Exception:
                        pass
        except Exception:
            pass

        return JsonResponse({'code': 2000, 'data': {'apps': apps}, 'msg': 'ok'})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'code': 4000, 'msg': 'invalid json'})
        action = data.get('action', 'register')
        agent_id = data.get('agent_id', '')
        name = data.get('name', '')
        command = data.get('command', '')
        if not agent_id or not name:
            return JsonResponse({'code': 4000, 'msg': 'agent_id and name required'})

        try:
            agent = AgentInstance.objects.filter(agent_id=agent_id).first()
            if not agent:
                return JsonResponse({'code': 4000, 'msg': 'agent not found'})

            tags = dict(agent.tags or {})
            apps = list(tags.get('registered_apps', []))

            if action == 'register':
                app_names = {a['name'] for a in apps if isinstance(a, dict)}
                if name not in app_names:
                    apps.append({
                        'name': name, 'command': command,
                        'user': data.get('user', ''),
                        'stop_command': data.get('stop_command', ''),
                        'pid_file': data.get('pid_file', ''),
                        'auto_restart': data.get('auto_restart', False),
                    })
            elif action == 'unregister':
                apps = [a for a in apps if not isinstance(a, dict) or a.get('name') != name]

            tags['registered_apps'] = apps
            agent.tags = tags
            agent.save(update_fields=['tags'])

            import requests as _req
            payload = {
                'agent_id': agent_id, 'name': name, 'command': command,
                'user': data.get('user', ''), 'stop_command': data.get('stop_command', ''),
                'pid_file': data.get('pid_file', ''), 'auto_restart': data.get('auto_restart', False),
            }
            if action == 'register':
                _req.post(f"{agent_server_url}/api/v1/apps/register", json=payload, timeout=3)
            else:
                _req.post(f"{agent_server_url}/api/v1/apps/unregister",
                          json={'agent_id': agent_id, 'name': name}, timeout=3)
        except Exception as e:
            logger.warning("app action failed: %s", e)

        return JsonResponse({'code': 2000, 'data': {'apps': apps}, 'msg': f'app {action}ed'})

    return JsonResponse({'error': 'method not allowed'}, status=405)
