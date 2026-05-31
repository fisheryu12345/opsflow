"""Seed the knowledge base with comprehensive IT operations knowledge entries."""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

KNOWLEDGE_ENTRIES = [
    # ======== Ansible / Automation ========
    {
        "title": "Ansible Playbook Execution Best Practices",
        "content": """1. Always test playbooks with --check mode before production execution
2. Use ansible-vault for sensitive data (passwords, API keys)
3. Organize roles by function (e.g., webserver, database, monitoring)
4. Set max_fail_percentage to prevent cascading failures
5. Use serial keyword for rolling updates (e.g., serial: 2 for 2-at-a-time)
6. Register variables to capture task output for downstream use
7. Use tags (--tags, --skip-tags) to run specific parts of playbooks
8. Employ handlers for service restarts (notify -> handler)
9. Set reasonable timeout values (default 30s, increase for slow networks)
10. Always idempotent: playbooks should produce same result on repeated runs""",
        "tags": ["ansible", "playbook", "automation", "best-practice"],
        "source": "doc",
    },
    {
        "title": "Common Ansible Failures and Solutions",
        "content": """1. "Timeout (12s)" when connecting to hosts: Check SSH connectivity, increase timeout
2. "Module not found": Ensure the module is installed on the control node
3. "Permission denied": Verify become password or become method (sudo/su)
4. "Could not find or access file": Check file paths on the remote host
5. "Unreachable host": Check network connectivity and host inventory
6. "FAILED! => {"msg": "the field 'hosts' is required"}": Check playbook syntax
7. "ERROR! 'xxx' is not a valid attribute for a Play": Follow Ansible YAML structure

Resolution: Check /var/log/ansible.log, run with -vvv verbosity""",
        "tags": ["ansible", "troubleshooting", "error", "debug"],
        "source": "incident",
    },
    # ======== Linux System Administration ========
    {
        "title": "Linux Disk Space Management",
        "content": """1. Check disk usage: df -h, df -i (inode usage)
2. Find large files: find / -type f -size +100M -exec ls -lh {} \\; 2>/dev/null
3. Clean package cache: apt-get clean / yum clean all
4. Remove old logs: journalctl --vacuum-time=7d, truncate -s 0 /var/log/*.log
5. Find and remove old kernels: dpkg --list | grep linux-image, apt-get autoremove
6. Check disk I/O: iostat -x 1, iotop
7. LVM extend: lvextend -L +10G /dev/vg/lv, resize2fs /dev/vg/lv
8. Mount options for space saving: noatime, nodiratime

Alert thresholds: Warning at 80%, Critical at 90%""",
        "tags": ["linux", "disk", "storage", "system-admin"],
        "source": "runbook",
    },
    {
        "title": "Linux Network Troubleshooting",
        "content": """1. Check connectivity: ping, traceroute, mtr
2. DNS resolution: nslookup, dig, host
3. Port availability: netstat -tlnp, ss -tlnp, lsof -i:port
4. Firewall rules: iptables -L -n, firewall-cmd --list-all (CentOS/RHEL), ufw status (Ubuntu)
5. Interface status: ip addr, ip link, ethtool eth0
6. Bandwidth usage: iftop, nload, vnstat
7. Packet capture: tcpdump -i eth0 port 80 -w capture.pcap
8. TCP connection states: ss -t state established
9. MTU issues: ping -M do -s 1472 host (test MTU size)
10. Route check: ip route get 8.8.8.8""",
        "tags": ["linux", "network", "troubleshooting", "connectivity"],
        "source": "runbook",
    },
    {
        "title": "Linux Memory & Process Management",
        "content": """1. Check memory: free -h, cat /proc/meminfo
2. Top memory processes: ps aux --sort=-%mem | head -10
3. CPU hogs: top, htop, ps aux --sort=-%cpu | head -10
4. Kill unresponsive process: kill -9 PID (SIGKILL as last resort)
5. Check swap usage: swapon --show, vmstat 1
6. OOM Killer logs: dmesg | grep -i oom, journalctl -k | grep -i oom
7. Memory leak detection: watch -n 2 'ps aux --sort=-%mem | head -5'
8. System load: uptime, cat /proc/loadavg
9. Process limits: ulimit -a, cat /etc/security/limits.conf
10. Check zombie processes: ps aux | grep -w Z""",
        "tags": ["linux", "memory", "process", "performance", "system-admin"],
        "source": "runbook",
    },
    # ======== Docker / Container ========
    {
        "title": "Docker Container Operations",
        "content": """1. List running containers: docker ps
2. List all containers: docker ps -a | grep Exited (clean with docker container prune)
3. View logs: docker logs -f --tail 100 container_name
4. Execute command: docker exec -it container_name /bin/bash
5. Inspect container: docker inspect container_name
6. Resource stats: docker stats container_name
7. Copy files: docker cp host_path container_name:container_path
8. Clean up: docker system prune -af (remove unused containers, images, networks)
9. Restart policy: --restart=always (ensure container starts on boot/docker restart)
10. Health check: HEALTHCHECK CMD curl -f http://localhost/ || exit 1

Troubleshooting: docker events (real-time events), docker logs (container stdout/stderr)""",
        "tags": ["docker", "container", "operations", "troubleshooting"],
        "source": "runbook",
    },
    # ======== Nginx / Web Server ========
    {
        "title": "Nginx Common Configurations and Troubleshooting",
        "content": """1. Test configuration before reload: nginx -t
2. Graceful reload: nginx -s reload (zero downtime)
3. Common error 502 Bad Gateway: Check upstream application server (is it running?)
4. Common error 504 Gateway Timeout: Increase proxy_read_timeout / proxy_send_timeout
5. SSL configuration: ssl_certificate, ssl_certificate_key, ssl_protocols TLSv1.2 TLSv1.3
6. Rate limiting: limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s
7. Access log location: /var/log/nginx/access.log
8. Error log location: /var/log/nginx/error.log (increase to debug level for troubleshooting)
9. Reverse proxy basic config: proxy_pass http://upstream; proxy_set_header Host $host;
10. Static file serving: alias /path/to/files; expires 30d;
11. Check open connections: curl http://localhost/nginx_status (requires stub_status module)
12. Performance tuning: worker_processes auto; worker_connections 1024; use epoll;""",
        "tags": ["nginx", "web-server", "config", "troubleshooting"],
        "source": "doc",
    },
    # ======== ESXi / VMware ========
    {
        "title": "ESXi Host Management Operations",
        "content": """1. Check host status: Connect via vCenter or direct SSH to ESXi host
2. VM power states: poweredOn, poweredOff, suspended
3. Common ESXi troubleshooting steps:
   a. Check /var/log/hostd.log for host daemon issues
   b. Check /var/log/vmkernel.log for kernel/hardware errors
   c. Check /var/log/vpxa.log for vCenter agent issues
4. Resource monitoring: esxtop (similar to Linux top but for ESXi)
5. Storage: esxcli storage vmfs extent list, vdf -h
6. Network: esxcfg-vmknic -l, esxcfg-nics -l
7. Quick health check: esxcli system health get
8. VMFS volume check: vmkfstools -P /vmfs/volumes/datastore_name
9. Snapshot management: Avoid leaving snapshots for >24-72 hours
10. Resource pool allocation: Monitor CPU ready time (>5% indicates contention)

Warning: Never remove a VMFS datastore without unmounting first!""",
        "tags": ["esxi", "vmware", "virtualization", "host-management"],
        "source": "runbook",
    },
    # ======== ServiceNow ========
    {
        "title": "ServiceNow Incident Management Workflow",
        "content": """1. Incident states: New -> In Progress -> On Hold -> Resolved -> Closed
2. Priority matrix: Based on Impact (High/Medium/Low) x Urgency (High/Medium/Low)
   - Critical (P1): Impact=High, Urgency=High -> 1-hour response
   - High (P2): Impact=High, Urgency=Medium -> 4-hour response
   - Medium (P3): Impact=Medium, Urgency=Medium -> 8-hour response
   - Low (P4): Impact=Low, Urgency=Low -> 24-hour response
3. Assignment groups: Route to correct technical team based on category
4. CI relationship mapping: Link impacted CI to incident for change impact analysis
5. Knowledge bridge: Convert resolved incidents to knowledge articles
6. SLA tracking: Each priority has defined resolution and response SLAs
7. Major incident management: P1 incidents trigger bridge call and executive notification
8. Categorization: Hardware > Software > Network > Database > Security > Other

API endpoints: /api/now/table/incident for CRUD operations""",
        "tags": ["servicenow", "incident", "itsm", "workflow"],
        "source": "doc",
    },
    # ======== Redfish / BMC ========
    {
        "title": "Redfish API Server Management Guide",
        "content": """1. Base URL: https://{bmc_ip}/redfish/v1/
2. Common endpoints:
   - /redfish/v1/Systems/{ID} - Server system info
   - /redfish/v1/Systems/{ID}/Power - Power control
   - /redfish/v1/Systems/{ID}/Thermal - Temperature sensors
   - /redfish/v1/Chassis/{ID}/Power - Power supply info
   - /redfish/v1/Managers/{ID} - BMC management controller
   - /redfish/v1/Systems/{ID}/Storage - Storage info
   - /redfish/v1/UpdateService - Firmware update
3. Power operations: POST with {"ResetType": "On"|"ForceOff"|"GracefulShutdown"|"PowerCycle"}
4. Boot override: PATCH with {"Boot": {"BootSourceOverrideTarget": "Pxe"|"Hdd"|"Cd"|"BiosSetup"}}
5. Firmware inventory: GET /redfish/v1/UpdateService/FirmwareInventory
6. Authentication: Basic auth or session token (POST /redfish/v1/SessionService/Sessions)
7. Event subscription: POST /redfish/v1/EventService/Subscriptions
8. Common response codes: 200 OK, 201 Created, 202 Accepted, 400 Bad Request, 401 Unauthorized

Default credentials often on chassis sticker; change immediately after deployment.""",
        "tags": ["redfish", "bmc", "server-management", "api", "firmware"],
        "source": "doc",
    },
    # ======== NetApp / Storage ========
    {
        "title": "NetApp ONTAP Storage Operations",
        "content": """1. Volume operations:
   - Create: volume create -vserver svm -volume vol_name -aggregate aggr -size 100g
   - Resize: volume size -vserver svm -volume vol_name -new-size 200g
   - Delete: volume delete -vserver svm -volume vol_name
   - Snapshot: snapshot create -vserver svm -volume vol_name -snapshot snap_name
2. Volume types: FlexVol (flexible), FlexGroup (scalable), InfiniteVol (discontinued)
3. QoS policies: storage qos policy-group create -policy-group pg_name -max-throughput 100MB/s
4. Efficiency features: deduplication (-space-guarantee none), compression, thin provisioning
5. Snapshot policies: Default is hourly+nightly+weekly (retain counts vary)
6. Cluster management: cluster show, node show
7. SVM (Storage VM) management: vserver create, vserver show
8. Network interfaces: network interface show (LIF management)
9. NFS export: export-policy create, export-policy rule create
10. Monitoring: event log show, statistics show -object volume

API endpoints (ONTAP 9.7+): /api/storage/volumes, /api/storage/snapshots""",
        "tags": ["netapp", "ontap", "storage", "volume", "snapshot"],
        "source": "runbook",
    },
    # ======== Dell PowerMax ========
    {
        "title": "Dell PowerMax Storage Array Management",
        "content": """1. Storage Group operations: Create/Delete/Modify via Unisphere REST API
2. Key concepts:
   - SRP (Storage Resource Pool): Defines capacity allocation
   - Service Level: Diamond > Platinum > Gold > Silver > Bronze > Optimized
   - SLO (Service Level Objective): Response time guarantees
   - Compression: Enabled by default on all-new devices
3. Volume provisioning:
   - Create volumes within a Storage Group
   - Volumes are thin-provisioned by default
   - Minimum volume size: 1GB, Maximum: 32000GB
4. SnapVX snapshots:
   - TimeFinder SnapVX for point-in-time snapshots
   - Snapshots share source allocation (space-efficient)
   - Can be linked to targets for host access
5. Performance monitoring:
   - IOPS (Read/Write), Bandwidth (MB/s), Response Time (ms)
   - Front-end ports, back-end directors, cache utilization
6. Common REST API: /univmax/restapi/management/v1/
7. SRDF for disaster recovery: Synchronous (SRDF/S) or Asynchronous (SRDF/A)

Always verify array ID before performing destructive operations!""",
        "tags": ["pmax", "powermax", "dell-emc", "storage", "san"],
        "source": "doc",
    },
    # ======== HTTP / API ========
    {
        "title": "REST API Call Best Practices",
        "content": """1. Always set reasonable timeout (default 30s, adjust per endpoint)
2. Handle HTTP status codes properly:
   - 2xx: Success (200 OK, 201 Created, 204 No Content)
   - 3xx: Redirection (follow unless you know what you're doing)
   - 4xx: Client error (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found)
   - 5xx: Server error (502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout)
3. Implement retry with exponential backoff: 1s -> 2s -> 4s -> 8s -> 16s (max 5 retries)
4. Include correlation-id in headers for request tracing
5. Set proper Content-Type header (application/json for REST APIs)
6. For large payloads, consider pagination or streaming
7. Validate SSL certificates in production (verify=True)
8. Use connection pooling (Session object in requests library)
9. Log request/response for debugging (sanitize sensitive data)
10. Monitor API response times and error rates""",
        "tags": ["http", "api", "rest", "best-practice"],
        "source": "doc",
    },
    # ======== Monitoring ========
    {
        "title": "Server Health Check Standards",
        "content": """1. CPU: Check load average vs CPU count. Warning: >70%, Critical: >90%
2. Memory: Check used % excluding cache/buffer. Warning: >80%, Critical: >90%
3. Disk: Check each mount point. Warning: >80%, Critical: >90%
4. Swap: Check swap usage. Warning: >50%, Critical: >80%
5. Network: Check interface errors/drops. Non-zero errors indicate hardware issues
6. Processes: Check critical processes (sshd, crond, rsyslog)
7. Disk I/O: Check await > 20ms indicates disk latency
8. Filesystem: Check inode usage on /var (log files can exhaust inodes)
9. Time sync: Check ntp/chrony synchronization offset < 100ms
10. SELinux status: Ensure configured policy matches requirements

Standard health endpoint: GET /health returning {"status": "healthy"} with 200 OK""",
        "tags": ["monitoring", "health-check", "system-admin", "best-practice"],
        "source": "runbook",
    },
    # ======== Database ========
    {
        "title": "MySQL/MariaDB Common Operations",
        "content": """1. Check database status: SHOW STATUS LIKE 'Threads_connected';
2. Slow query analysis: SHOW FULL PROCESSLIST; EXPLAIN SELECT ...
3. Backup: mysqldump -u root -p db_name > backup.sql
4. Restore: mysql -u root -p db_name < backup.sql
5. Disk space: SELECT table_schema, ROUND(SUM(data_length+index_length)/1024/1024, 2) AS MB
   FROM information_schema.tables GROUP BY table_schema;
6. Connection troubleshooting: Check max_connections, wait_timeout, interactive_timeout
7. Common errors:
   - "Too many connections": Increase max_connections, check application connection pooling
   - "Lock wait timeout exceeded": Check long-running transactions (SHOW ENGINE INNODB STATUS)
   - "Table is full": Check disk space or table size limits
8. Replication: SHOW SLAVE STATUS\\G, check Seconds_Behind_Master
9. Performance schema: SELECT * FROM sys.statement_analysis LIMIT 10;
10. MySQL 8.0: SHOW BINARY LOGS; PURGE BINARY LOGS BEFORE NOW() - INTERVAL 7 DAY;""",
        "tags": ["mysql", "mariadb", "database", "troubleshooting", "sql"],
        "source": "doc",
    },
    # ======== Security ========
    {
        "title": "Linux Server Security Hardening Checklist",
        "content": """1. SSH Configuration:
   - Disable root login (PermitRootLogin no)
   - Use key-based authentication only (PasswordAuthentication no)
   - Change default port (22 -> custom high port)
   - Use Fail2ban for brute force protection
2. Firewall:
   - Enable and configure: iptables/nftables/ufw/firewalld
   - Default deny inbound, allow outbound
   - Only open required ports
3. Updates:
   - Enable automatic security updates
   - Regularly audit installed packages
4. Users & Permissions:
   - Remove unused user accounts
   - Use sudo instead of direct root access
   - Apply principle of least privilege
5. Audit:
   - Enable auditd for system call monitoring
   - Monitor /var/log/auth.log for failed logins
   - Set up log forwarding to SIEM
6. File Integrity:
   - Deploy AIDE/Tripwire for critical file monitoring
   - Check /etc/passwd, /etc/shadow for unauthorized changes
7. SELinux/AppArmor: Keep enabled in enforcing mode
8. Kernel hardening: Apply sysctl settings (net.ipv4.conf.all.rp_filter=1, etc.)""",
        "tags": ["security", "hardening", "linux", "ssh", "firewall"],
        "source": "doc",
    },
    # ======== Recovery / Disaster Recovery ========
    {
        "title": "Service Recovery Playbook (Common Scenarios)",
        "content": """1. Web server down:
   a. Check nginx/apache process: systemctl status nginx
   b. Check port binding: netstat -tlnp | grep :80
   c. Check error logs: tail -100 /var/log/nginx/error.log
   d. Restart: systemctl restart nginx
   e. If still failing, check config: nginx -t

2. Database connection failure:
   a. Check process: systemctl status mysql
   b. Check port: netstat -tlnp | grep :3306
   c. Check disk space: mysql needs write space for transactions
   d. Check max_connections: SHOW VARIABLES LIKE 'max_connections'
   e. Restart: systemctl restart mysql (with caution)

3. Application not responding:
   a. Check JVM/process: ps aux | grep java
   b. Check heap usage: jstat -gc PID 1000 5
   c. Take thread dump: jstack PID > threaddump.log
   d. Check application logs: tail -100 /var/log/app/application.log
   e. Restart application service

4. Network connectivity issue:
   a. Ping gateway
   b. Check DNS resolution: nslookup hostname
   c. Check routing: ip route get destination
   d. Check firewall: iptables -L -n | grep destination
   e. Check interface status: ip link, ethtool""",
        "tags": ["recovery", "troubleshooting", "playbook", "service-down"],
        "source": "runbook",
    },
    # ======== Log Management ========
    {
        "title": "Centralized Log Management with Journald and Rsyslog",
        "content": """1. journalctl common commands:
   - View all logs: journalctl
   - Follow new logs: journalctl -f
   - By service: journalctl -u nginx.service
   - By time: journalctl --since "1 hour ago"
   - By priority: journalctl -p err -p warning
   - JSON output: journalctl -o json

2. rsyslog configuration:
   - Config files: /etc/rsyslog.conf, /etc/rsyslog.d/*.conf
   - Send to remote: *.* @remote-server:514 (UDP) / *.* @@remote-server:514 (TCP)
   - Receive from remote: $ModLoad imudp, $UDPServerRun 514

3. Log rotation: /etc/logrotate.conf, /etc/logrotate.d/*
   - Keep 30 days of logs: rotate 30
   - Compress old logs: compress
   - Post-rotate script: postrotate ... endscript

4. Log analysis patterns:
   - Failed SSH attempts: grep "Failed password" /var/log/auth.log | wc -l
   - HTTP 5xx errors: grep 'HTTP/1.1" 5' /var/log/nginx/access.log | wc -l
   - OOM events: dmesg | grep -i "out of memory"
   - Disk errors: journalctl -k | grep -i "ata.*error" """,
        "tags": ["logging", "journald", "rsyslog", "logrotate", "system-admin"],
        "source": "doc",
    },
    # ======== Backup ========
    {
        "title": "Backup Strategy and Verification",
        "content": """1. 3-2-1 Rule: 3 copies of data, 2 different media types, 1 offsite copy
2. Backup types:
   - Full backup: Complete copy (weekly)
   - Incremental backup: Changes since last backup (daily)
   - Differential backup: Changes since last full backup
3. Verification process:
   - Always verify backup integrity (checksum comparison)
   - Periodically perform restore drills (quarterly minimum)
   - Check log files for backup errors (exit code != 0 indicates failure)
4. Common backup tools:
   - Filesystem: rsync, tar, duplicity
   - Database: mysqldump, pg_dump, mongodump
   - VM: VMware snapshot + backup, Veeam, Commvault
   - Cloud: AWS S3 + Glacier for archival
5. Retention policy:
   - Daily backups: 7 days
   - Weekly backups: 4 weeks
   - Monthly backups: 12 months
   - Yearly backups: 7 years (compliance-dependent)
6. Monitoring: Alert on any backup failure within 15 minutes""",
        "tags": ["backup", "recovery", "3-2-1", "verification", "best-practice"],
        "source": "runbook",
    },
    # ======== Kubernetes / Container Orchestration ========
    {
        "title": "Kubernetes Pod Troubleshooting Guide",
        "content": """1. Pod status meanings:
   - Pending: Waiting for scheduling (check resources, node capacity)
   - Running: Pod is running normally
   - CrashLoopBackOff: App keeps crashing (check logs, config)
   - ImagePullBackOff: Cannot pull image (check image name, registry access)
   - Error: General error (describe pod for details)
   - Unknown: Node communication lost (check node status)

2. Debug commands:
   - kubectl get pods -n namespace
   - kubectl describe pod pod_name -n namespace
   - kubectl logs pod_name -n namespace
   - kubectl logs --previous pod_name -n namespace (crash logs)
   - kubectl exec -it pod_name -n namespace -- /bin/sh

3. Common issues:
   - Out of memory: Increase container memory limits, check for memory leaks
   - Image pull failure: Verify image exists, check registry credentials
   - Liveness/Readiness probe failure: Adjust probe timing/path
   - Node resource pressure: kubectl describe node, check for disk/memory pressure
   - ConfigMap/Secret not found: Verify names match, check namespace

4. Network: kubectl run busybox --image=busybox -it --rm -- sh (debug pod)""",
        "tags": ["kubernetes", "k8s", "container", "troubleshooting", "pods"],
        "source": "doc",
    },
]


class Command(BaseCommand):
    help = "Seed the ops_knowledge table with IT operations knowledge entries"

    def handle(self, *args, **options):
        from opsflow.models import OpsKnowledge

        created = 0
        skipped = 0

        for entry in KNOWLEDGE_ENTRIES:
            _, is_new = OpsKnowledge.objects.update_or_create(
                title=entry["title"],
                defaults={
                    "content": entry["content"],
                    "tags": entry["tags"],
                    "source": entry["source"],
                },
            )
            if is_new:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Knowledge base updated: {created} new, {skipped} existing"
            )
        )
