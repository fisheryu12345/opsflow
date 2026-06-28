"""Seed mock ITSM data"""

from django.core.management.base import BaseCommand
from itsm.models.incident import ServiceCategory,SlaPolicy,Incident,Change,ServiceRequest,Problem
from itsm.models.ticket import Ticket
import json

class Command(BaseCommand):
    help = "Seed mock ITSM data"

    def handle(self, *args, **options):
        self._create_itsm_data()
        self.stdout.write(self.style.SUCCESS("Seed complete!"))

    def _get_or_create(self, model_class, defaults_update=None, **lookup):
        """Get or create a model instance. With --force, update defaults."""
        obj, created = model_class.objects.get_or_create(defaults={}, **lookup)
        if not created and self.force:
            if defaults_update:
                for k, v in defaults_update.items():
                    setattr(obj, k, v)
                obj.save()
        elif created and defaults_update:
            for k, v in defaults_update.items():
                setattr(obj, k, v)
            obj.save()
        return obj, created

    def _random_project(self):
        import random
        if not self.project_map:
            return None
        ids = list(self.project_map.keys())
        return self.project_map[random.choice(ids)]

    def _random_template(self):
        from opsflow.models import FlowTemplate
        qs = FlowTemplate.objects.all()
        if not qs.exists():
            return None
        import random
        return random.choice(list(qs))

    # ── data creators ──

    def _create_itsm_data(self):
        """Create mock ITSM data: ServiceCategory -> SlaPolicy -> Incident/Change/Request/Problem"""
        self.stdout.write("\n>>> Creating ITSM Data ...")
        from itsm.models import ServiceCategory, SlaPolicy, Incident, Change, ServiceRequest, Problem
        from django.utils import timezone
        import datetime, uuid

        # ── Service categories (2-level tree) ──
        cat_defs = [
            {"name": "服务器运维", "code": "server-ops", "icon": "server", "children": [
                {"name": "服务器重启", "code": "server-reboot", "icon": "refresh"},
                {"name": "磁盘扩容", "code": "disk-expand", "icon": "storage"},
                {"name": "系统重装", "code": "os-reinstall", "icon": "monitor"},
            ]},
            {"name": "应用支持", "code": "app-support", "icon": "app", "children": [
                {"name": "应用部署", "code": "app-deploy", "icon": "deploy"},
                {"name": "配置修改", "code": "config-change", "icon": "setting"},
                {"name": "日志查询", "code": "log-query", "icon": "search"},
            ]},
            {"name": "网络管理", "code": "network-ops", "icon": "network", "children": [
                {"name": "VPN 申请", "code": "vpn-apply", "icon": "vpn"},
                {"name": "防火墙规则变更", "code": "firewall-change", "icon": "firewall"},
            ]},
            {"name": "数据库运维", "code": "db-ops", "icon": "database", "children": [
                {"name": "数据库备份", "code": "db-backup", "icon": "backup"},
                {"name": "SQL 审核执行", "code": "sql-exec", "icon": "sql"},
            ]},
        ]
        cat_map = {}
        for parent_def in cat_defs:
            parent, _ = ServiceCategory.objects.get_or_create(
                code=parent_def["code"],
                defaults={"name": parent_def["name"], "icon": parent_def.get("icon"), "parent": None},
            )
            cat_map[parent.code] = parent
            for idx, child_def in enumerate(parent_def.get("children", [])):
                child, _ = ServiceCategory.objects.get_or_create(
                    code=child_def["code"],
                    defaults={"name": child_def["name"], "icon": child_def.get("icon"), "parent": parent,
                              "sort_order": idx},
                )
                cat_map[child.code] = child
        self.stdout.write(f"  + {ServiceCategory.objects.count()} ServiceCategories")

        # ── SLA Policies ──
        sla_defs = [
            {"name": "P1 危急响应", "priority": "P1", "response": 15, "resolve": 60, "escalate": 5},
            {"name": "P2 高优先响应", "priority": "P2", "response": 30, "resolve": 180, "escalate": 15},
            {"name": "P3 普通响应", "priority": "P3", "response": 60, "resolve": 480, "escalate": 30},
            {"name": "P4 低优先响应", "priority": "P4", "response": 240, "resolve": 1440, "escalate": 60},
        ]
        sla_map = {}
        for sla in sla_defs:
            obj, _ = SlaPolicy.objects.get_or_create(
                priority=sla["priority"],
                defaults={
                    "name": sla["name"],
                    "response_minutes": sla["response"],
                    "resolve_minutes": sla["resolve"],
                    "escalate_minutes": sla["escalate"],
                },
            )
            sla_map[sla["priority"]] = obj
        self.stdout.write(f"  + {SlaPolicy.objects.count()} SlaPolicies")

        # ── Incidents ──
        incident_templates = [
            {"title": "线上商城首页加载超时", "priority": "P1", "source": "alert", "category": "server-ops",
             "description": "用户反馈商城首页加载超过 10s，监控确认响应时间异常"},
            {"title": "支付接口调用失败率突增", "priority": "P1", "source": "alert", "category": "app-support",
             "description": "支付网关 5xx 错误率超过 5%"},
            {"title": "数据库连接池耗尽", "priority": "P2", "source": "alert", "category": "db-ops",
             "description": "MySQL 连接数超过最大限制，大量应用连接失败"},
            {"title": "磁盘空间使用率超过 90%", "priority": "P2", "source": "alert", "category": "server-ops",
             "description": "/data 分区使用率 92%，需紧急清理"},
            {"title": "VPN 无法连接", "priority": "P3", "source": "user", "category": "vpn-apply",
             "description": "远程办公用户反馈 VPN 拨号失败"},
            {"title": "服务器防火墙规则变更申请", "priority": "P3", "source": "user", "category": "firewall-change",
             "description": "新增业务需要开放 8080 端口"},
            {"title": "Nginx 配置语法错误导致重启失败", "priority": "P2", "source": "alert", "category": "app-support",
             "description": "Nginx reload 失败，配置文件存在语法错误"},
            {"title": "K8s 节点 NotReady", "priority": "P1", "source": "alert", "category": "server-ops",
             "description": "生产集群 node-3 状态 NotReady"},
            {"title": "日志采集 Agent 离线", "priority": "P3", "source": "alert", "category": "log-query",
             "description": "5 台主机的 filebeat 日志采集器离线"},
            {"title": "SSL 证书即将到期", "priority": "P3", "source": "api", "category": "config-change",
             "description": "api.example.com 的 SSL 证书将于 7 天后到期"},
        ]
        statuses = ["new", "assigned", "in_progress", "resolved", "closed", "escalated"]
        inc_count = 0
        for i, tpl in enumerate(incident_templates):
            now = timezone.now()
            incident_id = "INC%06d" % (i + 1)
            priority = tpl["priority"]
            sla = sla_map.get(priority)
            obj, created = Incident.objects.get_or_create(
                incident_id=incident_id,
                defaults={
                    "title": tpl["title"],
                    "description": tpl["description"],
                    "priority": priority,
                    "source": tpl["source"],
                    "status": statuses[i % len(statuses)],
                    "category": cat_map.get(tpl["category"]),
                    "sla_policy": sla,
                    "sla_deadline": now + datetime.timedelta(minutes=(sla.resolve_minutes if sla else 480)),
                    "assignee": self.admin_user if i < 6 else None,
                    "cmdb_biz_id": str(getattr(self._random_project(), 'id', '1')),
                },
            )
            if created:
                inc_count += 1
        self.stdout.write(f"  + {inc_count} Incidents")

        # ── Change Requests ──
        change_templates = [
            {"title": "生产环境 Nginx 版本升级", "type": "normal", "risk": "medium",
             "desc": "将 Nginx 从 1.20 升级到 1.26，修复多个安全漏洞"},
            {"title": "MySQL 主从切换演练", "type": "standard", "risk": "low",
             "desc": "按季度计划进行 MySQL 主从切换演练"},
            {"title": "Redis 集群扩容", "type": "normal", "risk": "high",
             "desc": "增加 3 个 Redis 节点以应对业务增长"},
            {"title": "K8s 集群证书续期", "type": "emergency", "risk": "high",
             "desc": "K8s 集群证书将于 48h 后到期，需紧急续期"},
            {"title": "防火墙策略变更", "type": "standard", "risk": "low",
             "desc": "允许新业务网段访问数据库端口 3306"},
            {"title": "日志目录挂载扩容", "type": "normal", "risk": "low",
             "desc": "/var/log 分区从 100G 扩容到 200G"},
        ]
        change_statuses = ["draft", "pending_approval", "approved", "in_progress", "completed", "closed", "rolled_back"]
        chg_count = 0
        for i, tpl in enumerate(change_templates):
            now = timezone.now()
            change_id = "CHG%06d" % (i + 1)
            obj, created = Change.objects.get_or_create(
                change_id=change_id,
                defaults={
                    "title": tpl["title"],
                    "description": tpl["desc"],
                    "change_type": tpl["type"],
                    "risk_level": tpl["risk"],
                    "status": change_statuses[i % len(change_statuses)],
                    "applicant": self.admin_user,
                    "assignee": self.admin_user,
                    "planned_start": now + datetime.timedelta(days=1),
                    "planned_end": now + datetime.timedelta(days=2),
                    "rollback_plan": "备份配置后按步骤回滚至上一版本" if tpl["risk"] != "low" else "无需特殊回滚",
                },
            )
            if created:
                chg_count += 1
        self.stdout.write(f"  + {chg_count} Changes")

        # ── Service Requests ──
        request_templates = [
            {"title": "申请开通 VPN 账号", "cat": "vpn-apply",
             "desc": "新入职员工需要开通 VPN 远程办公权限"},
            {"title": "申请服务器磁盘扩容", "cat": "disk-expand",
             "desc": "应用服务器 /data 分区空间不足，申请扩容 50G"},
            {"title": "查询昨日支付接口日志", "cat": "log-query",
             "desc": "需要排查昨日 14:00-15:00 支付接口超时的请求日志"},
            {"title": "申请服务器权限", "cat": "server-ops",
             "desc": "新运维工程师需要申请 10 台生产服务器的 sudo 权限"},
            {"title": "数据库备份恢复", "cat": "db-backup",
             "desc": "需从昨日备份恢复 test_db 中误删的数据表"},
            {"title": "防火墙策略开通", "cat": "firewall-change",
             "desc": "新增应用需开通 10.0.1.0/24 到 10.0.2.0/24 的 443 端口"},
        ]
        req_statuses = ["pending", "in_progress", "fulfilled", "rejected", "cancelled"]
        req_count = 0
        for i, tpl in enumerate(request_templates):
            request_id = "REQ%06d" % (i + 1)
            status = req_statuses[i % len(req_statuses)]
            fulfilled = timezone.now() if status == "fulfilled" else None
            obj, created = ServiceRequest.objects.get_or_create(
                request_id=request_id,
                defaults={
                    "title": tpl["title"],
                    "description": tpl["desc"],
                    "status": status,
                    "category": cat_map.get(tpl["cat"]),
                    "requester": self.admin_user,
                    "assignee": self.admin_user,
                    "form_data": {"reason": tpl["desc"], "urgent": i < 2},
                    "fulfilled_at": fulfilled,
                },
            )
            if created:
                req_count += 1
        self.stdout.write(f"  + {req_count} ServiceRequests")

        # ── Problems ──
        problem_templates = [
            {"title": "支付接口间歇性超时根因分析", "priority": "P1",
             "desc": "近一周支付接口出现多次 5s 超时，需定位根因"},
            {"title": "服务器磁盘频繁写满", "priority": "P2",
             "desc": "多台应用服务器 /data 分区频繁在凌晨写满，疑似日志轮转异常"},
            {"title": "Nginx 连接数持续增长", "priority": "P3",
             "desc": "多台 Nginx 节点连接数持续增长，怀疑存在连接泄漏"},
        ]
        prob_statuses = ["new", "investigating", "root_cause_found", "resolved"]
        prob_count = 0
        for i, tpl in enumerate(problem_templates):
            problem_id = "PRB%06d" % (i + 1)
            obj, created = Problem.objects.get_or_create(
                problem_id=problem_id,
                defaults={
                    "title": tpl["title"],
                    "description": tpl["desc"],
                    "priority": tpl["priority"],
                    "status": prob_statuses[i % len(prob_statuses)],
                    "assignee": self.admin_user,
                    "root_cause": "" if i < 2 else "经排查确认是 keepalive 配置过短导致频繁重建连接",
                },
            )
            if created:
                prob_count += 1
        self.stdout.write(f"  + {prob_count} Problems")
