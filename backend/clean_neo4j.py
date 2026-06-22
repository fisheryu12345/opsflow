"""Clean up invalid Neo4j data, keep only DR mock data"""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
import django; django.setup()
from cmdb.services.neo4j_client import graph_driver

with graph_driver.session() as session:
    # 1. Delete Process nodes not part of DR mock
    r = session.run(
        "MATCH (p:Process) WHERE NOT p.host_ip IN ['192.168.1.60','192.168.1.61','192.168.2.60'] "
        "DETACH DELETE p RETURN count(*) AS cnt"
    )
    print("Deleted Process:", r.single()["cnt"])

    # 2. Delete non-mock Hosts
    r = session.run(
        "MATCH (h:Host) WHERE NOT h.instance_id IN ['host-mon-prod-01','host-mon-prod-02','host-mon-dr-01'] "
        "DETACH DELETE h RETURN count(*) AS cnt"
    )
    print("Deleted Host:", r.single()["cnt"])

    # 3. Delete extra Application nodes
    keep = ['monitor_web','monitor_api','monitor_db','monitor_cache',
            'alertmanager','grafana',
            'monitor_web_cont','monitor_api_cont','monitor_db_cont','monitor_cache_cont']
    keep_str = ",".join(f"'{k}'" for k in keep)
    r = session.run(
        f"MATCH (a:Application) WHERE NOT a.name IN [{keep_str}] "
        f"DETACH DELETE a RETURN count(*) AS cnt"
    )
    print("Deleted Application:", r.single()["cnt"])

    # 4. Summary
    print("\n=== Remaining ===")
    r = session.run("MATCH (n) RETURN labels(n)[0] AS l, count(*) AS cnt ORDER BY cnt DESC")
    for rec in r:
        print(f"  {rec['l']}: {rec['cnt']}")

    r = session.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS cnt ORDER BY cnt DESC")
    print("\n=== Remaining Relationships ===")
    for rec in r:
        print(f"  {rec['t']}: {rec['cnt']}")
