# -*- coding: utf-8 -*-
"""AppConfig for agent app"""

from django.apps import AppConfig


class AgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent_backend'
    verbose_name = 'Agent 管理 (Agent)'


def get_registry_pids(agent_id: str) -> set:
    """查询已注册应用的 PID（通过 Neo4j 匹配进程名/命令）"""
    from .models import AgentInstance
    agent = AgentInstance.objects.filter(agent_id=agent_id).first()
    if not agent:
        return set()
    tags = agent.tags or {}
    apps = tags.get('registered_apps', [])
    if not apps:
        return set()

    try:
        from cmdb.services.neo4j_client import graph_driver
        host_ip = agent.ip or ''
        if not host_ip:
            return set()

        pids = set()
        with graph_driver.session() as session:
            for app in apps:
                app_name = app.get('name', '')
                app_cmd = app.get('command', '')
                if not app_name:
                    continue
                if app_cmd:
                    cmd_basename = app_cmd.split('/')[-1].split()[0] if app_cmd else ''
                    result = session.run(
                        "MATCH (p:Process {host_ip: $host_ip, status: 'running'}) "
                        "WHERE p.name = $name OR p.cmdline CONTAINS $cmd_basename "
                        "RETURN DISTINCT p.pid AS pid",
                        host_ip=host_ip, name=app_name, cmd_basename=cmd_basename,
                    )
                else:
                    result = session.run(
                        "MATCH (p:Process {host_ip: $host_ip, name: $name, status: 'running'}) "
                        "RETURN DISTINCT p.pid AS pid",
                        host_ip=host_ip, name=app_name,
                    )
                for rec in result:
                    pids.add(rec['pid'])
        return pids
    except Exception:
        return set()
