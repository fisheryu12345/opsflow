import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
import django; django.setup()

import json
from uuid import uuid4
from datetime import datetime
from cmdb.services.neo4j_client import graph_driver

def run():
    now = str(datetime.now())
    gid = str(uuid4())
    out = []

    with graph_driver.session() as session:
        # Clean
        session.run("MATCH (g:DrGroup) DETACH DELETE g")
        session.run("MATCH (a:Application) DETACH DELETE a")
        out.append("Cleaned")

        # Hosts
        hosts = {
            "host-mon-prod-01": "192.168.1.60",
            "host-mon-prod-02": "192.168.1.61",
            "host-mon-dr-01": "192.168.2.60",
        }
        for hid, ip in hosts.items():
            session.run(
                "MERGE (h:Host {instance_id: $hid}) "
                "ON CREATE SET h.ip = $ip, h.__model_code = 'Host'",
                hid=hid, ip=ip,
            )
        out.append("Hosts:3")

        # Processes
        procs_data = [
            ("nginx", 1001, "www", "running", "host-mon-prod-01",
             "nginx: master process",
             '[{"ip":"0.0.0.0","port":80,"protocol":"tcp"}]',
             '[]', 1.2, 32),
            ("nginx", 1002, "www", "running", "host-mon-prod-01",
             "nginx: worker process", "[]", "[]", 0.8, 16),
            ("monitor-api", 2001, "monitor", "running", "host-mon-prod-01",
             "/usr/local/bin/monitor-api --port=8080",
             '[{"ip":"0.0.0.0","port":8080,"protocol":"tcp"}]',
             '[]', 15.3, 256),
            ("prometheus", 3001, "monitor", "running", "host-mon-prod-02",
             "/usr/local/bin/prometheus --storage.tsdb.retention=30d",
             '[{"ip":"0.0.0.0","port":9090,"protocol":"tcp"}]',
             '[]', 25.1, 2048),
            ("redis-server", 4001, "redis", "running", "host-mon-prod-01",
             "/usr/bin/redis-server 0.0.0.0:6379",
             '[{"ip":"0.0.0.0","port":6379,"protocol":"tcp"}]',
             '[]', 0.5, 64),
            ("alertmanager", 5001, "monitor", "running", "host-mon-prod-02",
             "/usr/local/bin/alertmanager",
             '[{"ip":"0.0.0.0","port":9093,"protocol":"tcp"}]',
             '[]', 3.2, 128),
            ("grafana-server", 6001, "grafana", "running", "host-mon-prod-01",
             "/usr/sbin/grafana-server",
             '[{"ip":"0.0.0.0","port":3000,"protocol":"tcp"}]',
             '[]', 5.1, 512),
            ("nginx", 0, "www", "stopped", "host-mon-dr-01",
             "",
             '[{"ip":"0.0.0.0","port":80,"protocol":"tcp"}]',
             '[]', 0, 0),
            ("monitor-api", 0, "monitor", "stopped", "host-mon-dr-01",
             "",
             '[{"ip":"0.0.0.0","port":8080,"protocol":"tcp"}]',
             '[]', 0, 0),
            ("prometheus", 0, "monitor", "stopped", "host-mon-dr-01",
             "",
             '[{"ip":"0.0.0.0","port":9090,"protocol":"tcp"}]',
             '[]', 0, 0),
            ("redis-server", 0, "redis", "stopped", "host-mon-dr-01",
             "",
             '[{"ip":"0.0.0.0","port":6379,"protocol":"tcp"}]',
             '[]', 0, 0),
        ]

        for p in procs_data:
            iid = str(uuid4())
            hip = hosts[p[4]]
            session.run(
                "MERGE (p:Process {host_ip: $hip, pid: $pid}) "
                "ON CREATE SET p.instance_id = $iid, p.name = $nm, "
                "  p.user = $us, p.status = $st, p.cmdline = $cl, "
                "  p.cpu_percent = $cp, p.memory_mb = $mm, "
                "  p.listen_addrs = $la, p.remote_connections = $rc, "
                "  p.__model_code = 'Process', p.__created_at = $now "
                "ON MATCH SET p.status = $st, p.__updated_at = $now",
                hip=hip, pid=p[1], iid=iid, nm=p[0], us=p[2], st=p[3],
                cl=p[5], cp=p[8], mm=p[9], la=p[6], rc=p[7], now=now,
            )
            session.run(
                "MATCH (p:Process {instance_id: $iid}) "
                "MATCH (h:Host {instance_id: $hid}) "
                "MERGE (p)-[:RUNS_ON]->(h)",
                iid=iid, hid=p[4],
            )
        out.append(f"Processes:{len(procs_data)}")

        # Applications
        app_defs = [
            ("monitor_web", "192.168.1.60", "running",
             [(1001, "192.168.1.60"), (1002, "192.168.1.60")]),
            ("monitor_api", "192.168.1.60", "running",
             [(2001, "192.168.1.60")]),
            ("monitor_db", "192.168.1.61", "running",
             [(3001, "192.168.1.61")]),
            ("monitor_cache", "192.168.1.60", "running",
             [(4001, "192.168.1.60")]),
            ("alertmanager", "192.168.1.61", "running",
             [(5001, "192.168.1.61")]),
            ("grafana", "192.168.1.60", "running",
             [(6001, "192.168.1.60")]),
            ("monitor_web_cont", "192.168.2.60", "stopped",
             [(0, "192.168.2.60")]),
            ("monitor_api_cont", "192.168.2.60", "stopped",
             [(0, "192.168.2.60")]),
            ("monitor_db_cont", "192.168.2.60", "stopped",
             [(0, "192.168.2.60")]),
            ("monitor_cache_cont", "192.168.2.60", "stopped",
             [(0, "192.168.2.60")]),
        ]

        for aname, ahost, astatus, proclist in app_defs:
            session.run(
                "MERGE (a:Application {name: $nm, host_ip: $hip}) "
                "ON CREATE SET a.instance_id = $iid, a.__model_code = 'Application', "
                "  a.__created_at = $now, a.status = $st, a.registered = true "
                "ON MATCH SET a.__updated_at = $now, a.status = $st",
                nm=aname, hip=ahost, iid=str(uuid4()), now=now, st=astatus,
            )
            for pid, phost in proclist:
                try:
                    session.run(
                        "MATCH (a:Application {name: $nm, host_ip: $hip}) "
                        "MATCH (p:Process {host_ip: $phost, pid: $pid}) "
                        "MERGE (a)-[:HAS_PROCESS]->(p)",
                        nm=aname, hip=ahost, phost=phost, pid=pid,
                    )
                except Exception:
                    pass
        out.append(f"Applications:{len(app_defs)}")

        # DrGroup
        session.run(
            "MERGE (g:DrGroup {name: $nm}) "
            "ON CREATE SET g.instance_id = $iid, g.__model_code = 'DrGroup', "
            "  g.__created_at = $now, g.description = $desc, g.status = 'active' "
            "ON MATCH SET g.__model_code = 'DrGroup', g.__updated_at = $now",
            nm="监控业务", iid=gid, now=now,
            desc="监控业务容灾组（Web/API/DB/Cache/Alertmanager/Grafana）",
        )
        out.append(f"DrGroup:{gid}")

        # PROTECTED_BY
        for aname, ahost, astatus, proclist in app_defs:
            session.run(
                "MATCH (a:Application {name: $nm, host_ip: $hip}) "
                "MATCH (g:DrGroup {instance_id: $gid}) "
                "MERGE (a)-[:PROTECTED_BY]->(g)",
                nm=aname, hip=ahost, gid=gid,
            )

        # CALLS
        calls_list = [
            ("monitor_web", "192.168.1.60", "monitor_api", "192.168.1.60", 8080),
            ("monitor_api", "192.168.1.60", "monitor_db", "192.168.1.61", 9090),
            ("monitor_api", "192.168.1.60", "monitor_cache", "192.168.1.60", 6379),
            ("grafana", "192.168.1.60", "monitor_api", "192.168.1.60", 8080),
            ("grafana", "192.168.1.60", "monitor_db", "192.168.1.61", 9090),
            ("alertmanager", "192.168.1.61", "monitor_api", "192.168.1.60", 8080),
        ]
        for src, shost, dst, dhost, port in calls_list:
            session.run(
                "MATCH (src:Application {name: $src, host_ip: $shost}) "
                "MATCH (dst:Application {name: $dst, host_ip: $dhost}) "
                "MERGE (src)-[r:CALLS]->(dst) SET r.remote_port = $port",
                src=src, shost=shost, dst=dst, dhost=dhost, port=port,
            )

    print("\n".join(out))
    print(f"Use this dr_group_id: {gid}")

if __name__ == "__main__":
    run()
