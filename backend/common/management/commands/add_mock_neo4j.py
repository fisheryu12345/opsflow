"""
Generate mock Neo4j CMDB topology data (graph nodes + relationships).

Usage:
    python manage.py add_mock_neo4j                  # Create mock graph data
    python manage.py add_mock_neo4j --clear          # Delete all existing nodes first
    python manage.py add_mock_neo4j --scale=small    # small / medium (default) / large

Creates a realistic CMDB topology:
  Biz  ->  Set  ->  Module  ->  Host  ->  Process
plus cross-process DEPENDS_ON relationships.

Uses the current Cypher-based CMDB service layer (NodeService + graph_driver).
"""

import logging
import random
import uuid
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

SCALES = {
    "small":  (2, 2, 2, 2, 2),
    "medium": (3, 3, 3, 3, 2),
    "large":  (5, 4, 4, 5, 3),
}

BIZ_NAMES = [
    "电商平台", "支付系统", "内部OA", "大数据平台", "AI训练平台",
    "物联网平台", "视频直播", "在线教育",
]

SET_TEMPLATES = [
    {"name_tpl": "{biz}-生产集群", "env": "生产"},
    {"name_tpl": "{biz}-测试集群", "env": "测试"},
    {"name_tpl": "{biz}-容灾集群", "env": "生产"},
    {"name_tpl": "{biz}-开发集群", "env": "开发"},
    {"name_tpl": "{biz}-灰度集群", "env": "测试"},
]

MODULE_TEMPLATES = [
    {"name_tpl": "{biz}-WEB", "svc": "web"},
    {"name_tpl": "{biz}-API网关", "svc": "lb"},
    {"name_tpl": "{biz}-数据库", "svc": "db"},
    {"name_tpl": "{biz}-缓存", "svc": "cache"},
    {"name_tpl": "{biz}-消息队列", "svc": "mq"},
    {"name_tpl": "{biz}-定时任务", "svc": "other"},
]

PROCESS_DEFS = [
    {"name": "nginx",    "port": 80,   "protocol": "http", "deps": []},
    {"name": "app-server", "port": 8080, "protocol": "http", "deps": ["redis", "mysql"]},
    {"name": "mysql",    "port": 3306, "protocol": "tcp",  "deps": []},
    {"name": "redis",    "port": 6379, "protocol": "tcp",  "deps": []},
    {"name": "rabbitmq", "port": 5672, "protocol": "tcp",  "deps": ["mysql"]},
    {"name": "tomcat",   "port": 8000, "protocol": "http", "deps": ["redis", "mysql"]},
    {"name": "prometheus", "port": 9090, "protocol": "http", "deps": []},
    {"name": "grafana",  "port": 3000, "protocol": "http", "deps": ["prometheus"]},
    {"name": "elasticsearch", "port": 9200, "protocol": "http", "deps": []},
    {"name": "kibana",   "port": 5601, "protocol": "http", "deps": ["elasticsearch"]},
    {"name": "zookeeper","port": 2181, "protocol": "tcp",  "deps": []},
    {"name": "kafka",    "port": 9092, "protocol": "tcp",  "deps": ["zookeeper"]},
]

OS_TYPES = ["linux", "linux", "linux", "linux", "windows"]
OS_VERSIONS = ["CentOS 7.9", "Ubuntu 22.04", "Debian 11", "AlmaLinux 9", "Rocky 8"]
REGIONS = ["cn-hangzhou", "cn-beijing", "cn-shanghai", "cn-shenzhen", "cn-qingdao"]


class Command(BaseCommand):
    help = "Generate mock Neo4j CMDB topology data (graph nodes + relationships)"

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all CMDB nodes first')
        parser.add_argument('--scale', type=str, default='medium', choices=['small', 'medium', 'large'],
                            help='Scale of mock data (default: medium)')

    def handle(self, *args, **options):
        from cmdb.services.neo4j_client import graph_driver
        from django.conf import settings

        self.scale_key = options['scale']
        clear = options.get('clear', False)

        if self.scale_key not in SCALES:
            raise CommandError(f"Invalid scale: {self.scale_key}")

        # Verify Neo4j connection
        try:
            with graph_driver.session() as s:
                s.run("RETURN 1").single()
            self.stdout.write(f"  Neo4j connected (scale={self.scale_key})")
        except Exception as e:
            raise CommandError(f"Neo4j connection failed: {e}")

        if clear:
            self._clear_all()

        num_biz, sets_per_biz, mods_per_set, hosts_per_mod, procs_per_host = SCALES[self.scale_key]

        self.stdout.write("=" * 60)
        self.stdout.write(f"CMDB Mock Data Generator — scale={self.scale_key}")
        self.stdout.write("=" * 60)

        self._create_topology(graph_driver, num_biz, sets_per_biz, mods_per_set, hosts_per_mod, procs_per_host)

        total_hosts = num_biz * sets_per_biz * mods_per_set * hosts_per_mod
        total_procs = total_hosts * procs_per_host
        self.stdout.write(self.style.SUCCESS(
            f"\nNeo4j mock data created! "
            f"Biz={num_biz}, Set={num_biz*sets_per_biz}, "
            f"Module={num_biz*sets_per_biz*mods_per_set}, "
            f"Host={total_hosts}, Process={total_procs}"
        ))

    # ── Clear ─────────────────────────────────────

    def _clear_all(self):
        self.stdout.write("\n>>> Clearing existing CMDB nodes ...")
        from cmdb.services.neo4j_client import graph_driver
        with graph_driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        self.stdout.write(self.style.SUCCESS("  All CMDB nodes deleted."))

    # ── Topology ───────────────────────────────────

    def _create_topology(self, gd, num_biz, spb, mps, hpm, pph):
        biz_names = BIZ_NAMES[:num_biz]
        ip_base = 1
        now = datetime.utcnow().isoformat()

        for bi, biz_name in enumerate(biz_names):
            biz_id = str(uuid.uuid4())
            with gd.session() as s:
                s.run(
                    "CREATE (n:Biz {instance_id: $id, __model_code: 'Biz', __created_at: $now, "
                    "name: $name, lifecycle: $lifecycle, operator: $op, description: $desc})",
                    id=biz_id, now=now, name=biz_name,
                    lifecycle="生产" if bi < 3 else random.choice(["生产", "测试", "开发"]),
                    op="admin", desc=f"{biz_name} — 核心业务系统"
                )
            self.stdout.write(f"\n[Biz] {biz_name}")

            for si in range(spb):
                st = SET_TEMPLATES[si % len(SET_TEMPLATES)]
                set_name = st["name_tpl"].format(biz=biz_name)
                set_id = str(uuid.uuid4())
                with gd.session() as s:
                    s.run(
                        "CREATE (n:Set {instance_id: $id, __model_code: 'Set', __created_at: $now, "
                        "name: $name, env_type: $env, description: $desc})",
                        id=set_id, now=now, name=set_name, env=st["env"],
                        desc=f"{biz_name} {st['env']}环境集群"
                    )
                    s.run(
                        "MATCH (b:Biz {instance_id: $bid}) MATCH (s:Set {instance_id: $sid}) "
                        "CREATE (b)-[:CONTAINS {rel_id: $rid, __asst_type: 'CONTAINS', __created_at: $now}]->(s)",
                        bid=biz_id, sid=set_id, rid=str(uuid.uuid4()), now=now
                    )
                self.stdout.write(f"  ├─[Set] {set_name}")

                for mi in range(mps):
                    mt = MODULE_TEMPLATES[mi % len(MODULE_TEMPLATES)]
                    mod_name = mt["name_tpl"].format(biz=biz_name)
                    mod_id = str(uuid.uuid4())
                    with gd.session() as s:
                        s.run(
                            "CREATE (n:Module {instance_id: $id, __model_code: 'Module', __created_at: $now, "
                            "name: $name, service_type: $svc, description: $desc})",
                            id=mod_id, now=now, name=mod_name, svc=mt["svc"],
                            desc=f"{biz_name} {mt['svc']} 模块"
                        )
                        s.run(
                            "MATCH (s:Set {instance_id: $sid}) MATCH (m:Module {instance_id: $mid}) "
                            "CREATE (s)-[:CONTAINS {rel_id: $rid, __asst_type: 'CONTAINS', __created_at: $now}]->(m)",
                            sid=set_id, mid=mod_id, rid=str(uuid.uuid4()), now=now
                        )
                    self.stdout.write(f"    ├─[Module] {mod_name}")

                    for hi in range(hpm):
                        host_ip = f"10.0.{bi}.{ip_base}"
                        hostname = f"node-{biz_name.lower()}-{mod_name.lower()}-{hi+1}"
                        ip_base += 1
                        host_id = str(uuid.uuid4())
                        with gd.session() as s:
                            s.run(
                                "CREATE (n:Host {instance_id: $id, __model_code: 'Host', __created_at: $now, "
                                "ip: $ip, hostname: $hostname, os_type: $os, os_version: $osv, "
                                "cpu_cores: $cpu, memory_mb: $mem, disk_gb: $disk, "
                                "status: $status, agent_status: $agent, region: $region})",
                                id=host_id, now=now, ip=host_ip, hostname=hostname,
                                os=random.choice(OS_TYPES), osv=random.choice(OS_VERSIONS),
                                cpu=random.choice([4, 8, 16, 32, 64]),
                                mem=random.choice([8192, 16384, 32768, 65536]),
                                disk=random.choice([100, 200, 500, 1000]),
                                status=random.choices(
                                    ["normal", "normal", "normal", "alarm", "offline", "maintenance"],
                                    weights=[70, 15, 5, 5, 3, 2]
                                )[0],
                                agent=random.choices(["online", "online", "online", "offline", "unknown"],
                                                     weights=[75, 15, 5, 3, 2])[0],
                                region=REGIONS[si % len(REGIONS)],
                            )
                            s.run(
                                "MATCH (m:Module {instance_id: $mid}) MATCH (h:Host {instance_id: $hid}) "
                                "CREATE (m)-[:CONTAINS {rel_id: $rid, __asst_type: 'CONTAINS', __created_at: $now}]->(h)",
                                mid=mod_id, hid=host_id, rid=str(uuid.uuid4()), now=now
                            )
                        self.stdout.write(f"      ├─[Host] {hostname} ({host_ip})")

                        # Processes on this host
                        procs = random.sample(PROCESS_DEFS, min(pph, len(PROCESS_DEFS)))
                        proc_ids = {}
                        for pd in procs:
                            proc_id = str(uuid.uuid4())
                            proc_ids[pd["name"]] = proc_id
                            with gd.session() as s:
                                s.run(
                                    "CREATE (n:Process {instance_id: $id, __model_code: 'Process', __created_at: $now, "
                                    "name: $name, port: $port, protocol: $proto, "
                                    "status: $status, version: $ver})",
                                    id=proc_id, now=now, name=pd["name"],
                                    port=pd["port"] + random.randint(0, 2),
                                    proto=pd["protocol"],
                                    status=random.choices(
                                        ["running", "running", "running", "stopped", "error"],
                                        weights=[80, 10, 5, 3, 2]
                                    )[0],
                                    ver=f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
                                )
                                s.run(
                                    "MATCH (h:Host {instance_id: $hid}) MATCH (p:Process {instance_id: $pid}) "
                                    "CREATE (h)-[:RUNS {rel_id: $rid, __asst_type: 'RUNS', __created_at: $now}]->(p)",
                                    hid=host_id, pid=proc_id, rid=str(uuid.uuid4()), now=now
                                )
                            self.stdout.write(f"        ├─[Process] {pd['name']}:{pd['port']}")

                        # Intra-host DEPENDS_ON
                        for pd in procs:
                            for dep in pd.get("deps", []):
                                if dep in proc_ids:
                                    with gd.session() as s:
                                        s.run(
                                            "MATCH (a:Process {instance_id: $aid}) "
                                            "MATCH (b:Process {instance_id: $bid}) "
                                            "CREATE (a)-[:DEPENDS_ON {rel_id: $rid, __asst_type: 'DEPENDS_ON', __created_at: $now}]->(b)",
                                            aid=proc_ids[pd["name"]], bid=proc_ids[dep],
                                            rid=str(uuid.uuid4()), now=now
                                        )

        # Cross-host dependencies
        self._add_cross_host_deps(gd)
        self.stdout.write("\n>>> Cross-service dependency links added.")

    def _add_cross_host_deps(self, gd):
        with gd.session() as s:
            s.run("""
                MATCH (app:Process {name: 'app-server'})
                MATCH (redis:Process {name: 'redis'})
                WHERE app <> redis
                WITH app, redis LIMIT 20
                MERGE (app)-[:DEPENDS_ON {rel_id: randomUUID(), __asst_type: 'DEPENDS_ON',
                       __created_at: toString(datetime())}]->(redis)
            """)
            s.run("""
                MATCH (app:Process {name: 'app-server'})
                MATCH (mysql:Process {name: 'mysql'})
                WHERE app <> mysql
                WITH app, mysql LIMIT 20
                MERGE (app)-[:DEPENDS_ON {rel_id: randomUUID(), __asst_type: 'DEPENDS_ON',
                       __created_at: toString(datetime())}]->(mysql)
            """)
            s.run("""
                MATCH (kafka:Process {name: 'kafka'})
                MATCH (zk:Process {name: 'zookeeper'})
                WHERE kafka <> zk
                WITH kafka, zk LIMIT 15
                MERGE (kafka)-[:DEPENDS_ON {rel_id: randomUUID(), __asst_type: 'DEPENDS_ON',
                       __created_at: toString(datetime())}]->(zk)
            """)
