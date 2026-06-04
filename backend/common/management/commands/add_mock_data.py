"""
Generate comprehensive mock data for all platform models.

Usage:
    python manage.py add_mock_data              # Add mock data (skip existing)
    python manage.py add_mock_data --force       # Force update existing records
    python manage.py add_mock_data --clear       # Clear all mock data first

Covers: opsflow, opsagent, cmdb, integration apps.
Idempotent — safe to re-run.
"""

import datetime
import random

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# ──────────────────────────────────────────────
#  Sample data constants
# ──────────────────────────────────────────────

SAMPLE_PROJECTS = [
    {"name": "电商平台", "desc": "核心电商业务系统运维项目"},
    {"name": "支付系统", "desc": "支付网关与清算系统运维项目"},
    {"name": "内部OA", "desc": "内部办公自动化系统运维项目"},
    {"name": "大数据平台", "desc": "数据仓库与实时计算平台运维项目"},
    {"name": "AI训练平台", "desc": "机器学习模型训练与推理平台运维项目"},
]

SAMPLE_TEMPLATE_CATEGORIES = [
    {"name": "服务器管理", "code": "server"},
    {"name": "应用部署", "code": "deploy"},
    {"name": "数据库运维", "code": "database"},
    {"name": "网络管理", "code": "network"},
    {"name": "安全巡检", "code": "security"},
    {"name": "备份恢复", "code": "backup"},
    {"name": "监控告警", "code": "monitor"},
    {"name": "容器管理", "code": "container"},
]

SAMPLE_TEMPLATES = [
    {"name": "Nginx 部署流程", "category_code": "deploy",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "检查环境", "type": "task"},
                                 {"id": "n2", "label": "安装 Nginx", "type": "task"},
                                 {"id": "n3", "label": "配置 SSL", "type": "task"},
                                 {"id": "n4", "label": "启动服务", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "MySQL 备份脚本", "category_code": "backup",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "连接检测", "type": "task"},
                                 {"id": "n2", "label": "执行全量备份", "type": "task"},
                                 {"id": "n3", "label": "压缩传输", "type": "task"},
                                 {"id": "n4", "label": "校验完整性", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "服务器安全巡检", "category_code": "security",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "漏洞扫描", "type": "task"},
                                 {"id": "n2", "label": "日志审计", "type": "task"},
                                 {"id": "n3", "label": "基线检查", "type": "task"},
                                 {"id": "n4", "label": "生成报告", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "Docker 容器部署", "category_code": "container",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "拉取镜像", "type": "task"},
                                 {"id": "n2", "label": "创建网络", "type": "task"},
                                 {"id": "n3", "label": "启动容器", "type": "task"},
                                 {"id": "n4", "label": "健康检查", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "Redis 集群扩容", "category_code": "database",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "新增节点", "type": "task"},
                                 {"id": "n2", "label": "数据迁移", "type": "task"},
                                 {"id": "n3", "label": "槽位重分配", "type": "task"},
                                 {"id": "n4", "label": "验证数据", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "K8s 集群升级", "category_code": "container",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "Drain 节点", "type": "task"},
                                 {"id": "n2", "label": "升级 kubelet", "type": "task"},
                                 {"id": "n3", "label": "升级 API Server", "type": "task"},
                                 {"id": "n4", "label": "恢复调度", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "SSL 证书续期", "category_code": "server",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "检查到期日", "type": "task"},
                                 {"id": "n2", "label": "申请新证书", "type": "task"},
                                 {"id": "n3", "label": "部署证书", "type": "task"},
                                 {"id": "n4", "label": "验证 HTTPS", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "网络设备备份配置", "category_code": "network",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "SSH 登录设备", "type": "task"},
                                 {"id": "n2", "label": "导出配置", "type": "task"},
                                 {"id": "n3", "label": "版本对比", "type": "task"},
                                 {"id": "n4", "label": "归档保存", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "磁盘空间清理", "category_code": "server",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "检查磁盘使用率", "type": "task"},
                                 {"id": "n2", "label": "清理日志文件", "type": "task"},
                                 {"id": "n3", "label": "清理临时文件", "type": "task"},
                                 {"id": "n4", "label": "生成报告", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
    {"name": "监控阈值调整", "category_code": "monitor",
     "pipeline_tree": {"nodes": [{"id": "n1", "label": "分析告警趋势", "type": "task"},
                                 {"id": "n2", "label": "调整阈值参数", "type": "task"},
                                 {"id": "n3", "label": "发送通知", "type": "task"},
                                 {"id": "n4", "label": "验证告警", "type": "task"}],
                       "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}]}},
]

SAMPLE_PLUGINS = [
    {"code": "plugin.cmdb.sync_host", "name": "CMDB 主机同步", "group": "cmdb"},
    {"code": "plugin.monitor.push_alert", "name": "推送告警", "group": "monitor"},
    {"code": "plugin.deploy.helm_release", "name": "Helm Release", "group": "deploy"},
    {"code": "plugin.notify.wechat", "name": "企业微信通知", "group": "notify"},
    {"code": "plugin.notify.dingtalk", "name": "钉钉通知", "group": "notify"},
    {"code": "plugin.db.sql_execute", "name": "SQL 执行器", "group": "database"},
]

SAMPLE_ENVIRONMENTS = [
    {"name": "生产环境", "slug": "production", "env_type": "production"},
    {"name": "预发布环境", "slug": "staging", "env_type": "staging"},
    {"name": "测试环境", "slug": "testing", "env_type": "canary"},
    {"name": "开发环境", "slug": "development", "env_type": "development"},
]

SAMPLE_KNOWLEDGE = [
    {"title": "Nginx 常见问题排查", "content": "1. 检查配置语法: nginx -t\n2. 查看 error.log\n3. 检查端口占用: ss -tlnp | grep 80\n4. 重载配置: nginx -s reload", "tags": ["nginx", "web"]},
    {"title": "MySQL 性能优化指南", "content": "1. 启用慢查询日志\n2. 检查索引使用情况\n3. 优化 JOIN 查询\n4. 调整 innodb_buffer_pool_size", "tags": ["mysql", "database", "performance"]},
    {"title": "Docker 故障排查流程", "content": "1. docker ps -a 检查容器状态\n2. docker logs <container>\n3. docker inspect <container>\n4. 检查宿主机资源使用", "tags": ["docker", "container"]},
    {"title": "K8s Pod 排错指南", "content": "1. kubectl describe pod <name>\n2. kubectl logs <pod>\n3. kubectl exec -it <pod> -- sh\n4. 检查 Events 和 Status", "tags": ["k8s", "container"]},
    {"title": "Redis 缓存雪崩处理", "content": "1. 设置随机过期时间\n2. 本地缓存兜底\n3. 限流降级\n4. 异步重建缓存", "tags": ["redis", "cache"]},
    {"title": "Linux 系统性能分析", "content": "1. top/htop 查看进程\n2. iostat 分析磁盘 IO\n3. vmstat 查看内存\n4. netstat/ss 查看网络连接", "tags": ["linux", "performance"]},
]

SAMPLE_INTEGRATIONS = [
    {"code": "prometheus", "name": "Prometheus 监控", "category": "monitor",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}}},
    {"code": "grafana", "name": "Grafana 可视化", "category": "monitor",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "api_key": {"type": "string"}}}},
    {"code": "jenkins", "name": "Jenkins CI/CD", "category": "cicd",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "token": {"type": "string"}}}},
    {"code": "gitlab", "name": "GitLab 代码仓库", "category": "scm",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "token": {"type": "string"}}}},
    {"code": "elasticsearch", "name": "Elasticsearch 日志", "category": "log",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "index_prefix": {"type": "string"}}}},
    {"code": "ansible", "name": "Ansible 自动化", "category": "automation",
     "config_schema": {"type": "object", "properties": {"url": {"type": "string"}, "token": {"type": "string"}}}},
]

SAMPLE_CMDB_MODELS = [
    {"code": "server", "name": "服务器", "category": "host",
     "fields": [{"name": "ip", "label": "IP 地址", "field_type": "ip"},
                {"name": "os", "label": "操作系统", "field_type": "string"},
                {"name": "cpu_cores", "label": "CPU 核数", "field_type": "integer"},
                {"name": "memory_gb", "label": "内存(GB)", "field_type": "integer"},
                {"name": "disk_gb", "label": "磁盘(GB)", "field_type": "integer"}]},
    {"code": "database", "name": "数据库实例", "category": "custom",
     "fields": [{"name": "engine", "label": "数据库引擎", "field_type": "string"},
                {"name": "version", "label": "版本", "field_type": "string"},
                {"name": "port", "label": "端口", "field_type": "integer"},
                {"name": "role", "label": "角色", "field_type": "enum"}]},
]


class Command(BaseCommand):
    help = "Generate comprehensive mock data for all platform models"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update existing records')
        parser.add_argument('--clear', action='store_true', help='Clear all mock data first')

    def handle(self, *args, **options):
        self.force = options.get('force', False)
        self.clear = options.get('clear', False)

        # Resolve default user
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.first()
        if not self.admin_user:
            raise CommandError("No users found — run migrations and create a superuser first.")

        self.project_map = {}

        self.stdout.write("=" * 60)
        self.stdout.write("OpsFlow Platform — Mock Data Generator")
        self.stdout.write("=" * 60)

        # ── Step 1: OpsProject ──
        self._create_projects()

        # ── Step 2: Template Categories ──
        self._create_template_categories()

        # ── Step 3: FlowTemplates + Nodes + Versions ──
        self._create_templates()

        # ── Step 4: Plugins ──
        self._create_plugins()

        # ── Step 5: Schedule Plans ──
        self._create_schedules()

        # ── Step 6: Webhooks ──
        self._create_webhooks()

        # ── Step 7: OpsKnowledge ──
        self._create_knowledge()

        # ── Step 8: ApiToken ──
        self._create_api_tokens()

        # ── Step 9: Environment Variables ──
        self._create_env_vars()

        # ── Step 10: Executions ──
        self._create_executions()

        # ── Step 11: Execution Schemes ──
        self._create_execution_schemes()

        # ── Step 12: ITSM Data ──
        self._create_itsm_data()

        # ── Step 13: OpsAgent Data ──
        self._create_opsagent_data()

        # ── Step 14: Integration Connectors ──
        self._create_integrations()

        # ── Step 14: CMDB Model Definitions ──
        self._create_cmdb_models()

        # ── Step 15: Audit / Operation Records ──
        self._create_audit_records()

        self.stdout.write(self.style.SUCCESS("\nAll mock data created successfully!"))

    # ── helpers ──

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

    def _create_projects(self):
        self.stdout.write("\n>>> Creating Projects ...")
        from opsflow.models import OpsProject, ProjectMember
        for p in SAMPLE_PROJECTS:
            obj, created = self._get_or_create(OpsProject, name=p["name"])
            if created or self.force:
                obj.owner = self.admin_user
                obj.save(update_fields=['owner'] if not created else [])
            self.project_map[obj.id] = obj
            # add project member
            ProjectMember.objects.get_or_create(project=obj, user=self.admin_user, defaults={'role': 'admin'})
            self.stdout.write(f"  {'+' if created else ' '} Project: {p['name']}")

    def _create_template_categories(self):
        self.stdout.write("\n>>> Creating Template Categories ...")
        from django.db.utils import IntegrityError
        from opsflow.models import TemplateCategory
        existing_codes = set(TemplateCategory.objects.values_list('code', flat=True))
        existing_names = set(TemplateCategory.objects.values_list('name', flat=True))
        for c in SAMPLE_TEMPLATE_CATEGORIES:
            if c["code"] in existing_codes:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (exists)")
                continue
            if c["name"] in existing_names:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (name exists, skip)")
                continue
            try:
                obj = TemplateCategory.objects.create(code=c["code"], name=c["name"])
                self.stdout.write(f"  + Category: {obj.name} ({obj.code})")
            except IntegrityError as e:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (skip: {e})")

    def _create_templates(self):
        self.stdout.write("\n>>> Creating Templates + Nodes + Versions ...")
        from opsflow.models import FlowTemplate, TemplateNode, TemplateVersion

        for i, t in enumerate(SAMPLE_TEMPLATES):
            proj = self._random_project()
            obj, created = self._get_or_create(
                FlowTemplate, name=t["name"],
                defaults_update={
                    "project": proj,
                    "category": t["category_code"],
                    "pipeline_tree": t["pipeline_tree"],
                    "is_draft": False,
                    "description": f"{t['name']} — auto-generated mock template",
                    "version": 1,
                }
            )
            if created:
                obj.created_by = self.admin_user
                obj.save(update_fields=['created_by'])
            self.stdout.write(f"  {'+' if created else ' '} Template: {t['name']}")

            # Create template nodes
            if created or self.force:
                for node in t["pipeline_tree"].get("nodes", []):
                    TemplateNode.objects.get_or_create(
                        template=obj,
                        node_id=node["id"],
                        defaults={"node_type": node.get("type", "task"), "label": node.get("label", "")},
                    )

            # Create version
            TemplateVersion.objects.get_or_create(
                template=obj, version=1,
                defaults={
                    "created_by": self.admin_user,
                    "pipeline_tree": t["pipeline_tree"],
                },
            )

    def _create_plugins(self):
        self.stdout.write("\n>>> Creating Plugins ...")
        from opsflow.models import PluginMeta
        for p in SAMPLE_PLUGINS:
            obj, created = self._get_or_create(PluginMeta, code=p["code"], name=p["name"], group=p["group"],
                                                defaults_update={"risk_level": "low", "is_active": True})
            self.stdout.write(f"  {'+' if created else ' '} Plugin: {p['name']}")

    def _create_schedules(self):
        self.stdout.write("\n>>> Creating Schedule Plans ...")
        from opsflow.models import SchedulePlan
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:5])
        for i, t in enumerate(templates[:3]):
            obj, created = self._get_or_create(
                SchedulePlan, template=t, name=f"{t.name} 每日执行",
                defaults_update={
                    "schedule_type": "cron",
                    "cron_expr": "0 3 * * *",
                    "project": self._random_project(),
                    "created_by": self.admin_user,
                }
            )
            self.stdout.write(f"  {'+' if created else ' '} Schedule: {obj.name}")

    def _create_webhooks(self):
        self.stdout.write("\n>>> Creating Webhook Configs ...")
        from opsflow.models import WebhookConfig, FlowTemplate
        templates = list(FlowTemplate.objects.all()[:5])
        webhook_defs = [
            {"name": "企业微信通知", "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock-key"},
            {"name": "钉钉机器人", "url": "https://oapi.dingtalk.com/robot/send?access_token=mock-token"},
            {"name": "飞书机器人", "url": "https://open.feishu.cn/open-apis/bot/v2/hook/mock"},
        ]
        for t in templates[:3]:
            for w in webhook_defs:
                obj, created = self._get_or_create(
                    WebhookConfig, template=t, name=w["name"], url=w["url"],
                    defaults_update={"created_by": self.admin_user},
                )
                if created:
                    self.stdout.write(f"  + Webhook: {w['name']} -> {t.name}")

    def _create_knowledge(self):
        self.stdout.write("\n>>> Creating Knowledge Base ...")
        from opsflow.models import OpsKnowledge
        for k in SAMPLE_KNOWLEDGE:
            obj, created = self._get_or_create(
                OpsKnowledge, title=k["title"],
                defaults_update={"content": k["content"], "tags": k["tags"], "source": "doc"},
            )
            self.stdout.write(f"  {'+' if created else ' '} Knowledge: {k['title']}")

    def _create_api_tokens(self):
        self.stdout.write("\n>>> Creating API Tokens ...")
        import uuid
        from opsflow.models import ApiToken
        tokens = [
            {"name": "CMDB 同步 Token", "allowed_actions": ["cmdb.sync"]},
            {"name": "监控告警 Token", "allowed_actions": ["monitor.push_alert"]},
            {"name": "CI/CD Token", "allowed_actions": ["execution.create", "execution.start"]},
        ]
        for t in tokens:
            obj, created = self._get_or_create(
                ApiToken, name=t["name"],
                defaults_update={
                    "token": uuid.uuid4().hex[:32],
                    "created_by": self.admin_user,
                    "allowed_actions": t["allowed_actions"],
                },
            )
            self.stdout.write(f"  {'+' if created else ' '} ApiToken: {t['name']}")

    def _create_env_vars(self):
        self.stdout.write("\n>>> Creating Environment Variables ...")
        from opsflow.models import ProjectEnvironmentVariable
        env_vars = [
            {"key": "NGINX_HOME", "value": "/usr/local/nginx", "var_type": "input"},
            {"key": "MYSQL_ROOT_PASSWORD", "value": "******", "var_type": "password"},
            {"key": "JAVA_HOME", "value": "/usr/lib/jvm/java-11", "var_type": "input"},
            {"key": "LOG_RETENTION_DAYS", "value": "30", "var_type": "int"},
            {"key": "ALERT_WEBHOOK_URL", "value": "https://alert.example.com/hook", "var_type": "input"},
        ]
        projects = list(self.project_map.values())
        for proj in projects[:3]:
            for ev in env_vars:
                obj, created = self._get_or_create(
                    ProjectEnvironmentVariable, project=proj, key=ev["key"],
                    defaults_update={"value": ev["value"], "var_type": ev["var_type"]},
                )
                if created:
                    self.stdout.write(f"  + EnvVar: {ev['key']} -> {proj.name}")

    def _create_executions(self):
        self.stdout.write("\n>>> Creating Executions ...")
        from opsflow.models import FlowTemplate, FlowExecution, ExecutionNode
        from opsflow.models.execution import NodeExecutionTrace
        templates = list(FlowTemplate.objects.all()[:6])
        statuses = ["completed", "running", "failed", "paused", "cancelled"]
        for i, t in enumerate(templates):
            status = statuses[i % len(statuses)]
            now = timezone.now()
            started = now - datetime.timedelta(hours=random.randint(1, 72))
            ended = now if status == "running" else started + datetime.timedelta(minutes=random.randint(5, 60))
            exec_obj, created = FlowExecution.objects.get_or_create(
                template=t,
                status=status,
                created_by=self.admin_user,
                defaults={
                    "project": self._random_project(),
                    "state_tree": {},
                    "context": {"dry_run": False},
                    "template_snapshot": {
                        "pipeline_tree": t.pipeline_tree,
                        "target_hosts": [],
                        "global_vars": {},
                        "template_version": t.version,
                    },
                },
            )
            if created:
                # Create execution nodes
                nodes_data = (t.pipeline_tree or {}).get("nodes", [])
                for nd in nodes_data:
                    ExecutionNode.objects.get_or_create(
                        execution=exec_obj, node_id=nd["id"],
                        defaults={"node_type": nd.get("type", "task"), "status": status if status != "running" else "completed"},
                    )
                self.stdout.write(f"  + Execution #{exec_obj.id} ({t.name}): {status}")
            else:
                self.stdout.write(f"    Execution #{exec_obj.id} ({t.name}): {status} (exists)")

    def _create_execution_schemes(self):
        self.stdout.write("\n>>> Creating Execution Schemes ...")
        from opsflow.models import ExecutionScheme
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:4])
        scheme_names = ["快速执行方案", "全量部署方案", "灰度发布方案", "回滚方案"]
        for i, t in enumerate(templates):
            name = scheme_names[i % len(scheme_names)]
            obj, created = self._get_or_create(
                ExecutionScheme, template=t, name=name,
                defaults_update={
                    "project": self._random_project(),
                    "created_by": self.admin_user,
                    "excluded_nodes": [],
                },
            )
            self.stdout.write(f"  {'+' if created else ' '} Scheme: {name} -> {t.name}")

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

    def _create_opsagent_data(self):
        self.stdout.write("\n>>> Creating OpsAgent Data ...")

        # EnvironmentContext
        from opsagent.models import EnvironmentContext, Session, AuditRecord, AgentMemory
        env_map = {}
        for e in SAMPLE_ENVIRONMENTS:
            obj, created = self._get_or_create(EnvironmentContext, name=e["name"], slug=e["slug"],
                                                defaults_update={"env_type": e["env_type"]})
            env_map[obj.slug] = obj
            self.stdout.write(f"  {'+' if created else ' '} EnvContext: {e['name']}")

        # Sessions
        session_data = [
            {"mode": "repl", "operator": "superadmin"},
            {"mode": "oneshot", "operator": "superadmin"},
        ]
        import uuid
        for s in session_data:
            obj, created = self._get_or_create(
                Session, session_id=uuid.uuid4().hex[:16], mode=s["mode"],
                defaults_update={"operator": s["operator"], "environment": env_map.get("production")},
            )
            if created:
                self.stdout.write(f"  + Session: {obj.session_id[:12]}... ({s['mode']})")

        # AgentMemory
        memory_data = [
            {"memory_type": "conversation", "title": "Nginx 部署问答", "content": "用户询问 Nginx 部署步骤，提供了标准部署流程。"},
            {"memory_type": "conversation", "title": "MySQL 备份配置", "content": "用户要求配置 MySQL 自动备份策略。"},
            {"memory_type": "feedback", "title": "操作审批反馈", "content": "用户对高危操作确认流程表示满意。"},
        ]
        for m in memory_data:
            obj, created = self._get_or_create(
                AgentMemory, memory_type=m["memory_type"], title=m["title"],
                defaults_update={"content": m["content"]},
            )
            self.stdout.write(f"  {'+' if created else ' '} AgentMemory: {m['title']}")

    def _create_integrations(self):
        self.stdout.write("\n>>> Creating Integration Connectors ...")
        from integration.models import ConnectorDefinition, ConnectorInstance, ConnectorCredential
        import uuid

        for i, c in enumerate(SAMPLE_INTEGRATIONS):
            obj, created = self._get_or_create(
                ConnectorDefinition, code=c["code"], name=c["name"],
                defaults_update={
                    "category": c["category"],
                    "config_schema": c["config_schema"],
                    "is_active": True,
                    "version": "1.0",
                },
            )
            self.stdout.write(f"  {'+' if created else ' '} ConnectorDef: {c['name']}")

            # Create an instance for each
            if created or self.force:
                inst, _ = ConnectorInstance.objects.get_or_create(
                    definition=obj, name=f"{c['name']} 实例",
                    defaults={"status": "connected", "is_active": True},
                )
                self.stdout.write(f"    + Instance: {inst.name}")

        # ── AI Provider Definitions (using seed_connector_definitions style) ──
        AI_PROVIDERS = [
            {
                "code": "openai",
                "name": "OpenAI",
                "config": {"api_base": "https://api.openai.com/v1", "model": "gpt-4o", "max_tokens": 4096},
                "instance_name": "OpenAI 生产实例",
            },
            {
                "code": "deepseek",
                "name": "DeepSeek",
                "config": {"api_base": "https://api.deepseek.com/v1", "model": "deepseek-chat", "max_tokens": 4096},
                "instance_name": "DeepSeek 主实例",
            },
            {
                "code": "anthropic",
                "name": "Anthropic Claude",
                "config": {"api_base": "https://api.anthropic.com", "model": "claude-sonnet-4-20250514", "max_tokens": 4096},
                "instance_name": "Claude 生产实例",
            },
            {
                "code": "tongyi_qwen",
                "name": "通义千问 (Qwen)",
                "config": {"api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "max_tokens": 4096},
                "instance_name": "通义千问实例",
            },
        ]

        for ap in AI_PROVIDERS:
            try:
                definition = ConnectorDefinition.objects.get(code=ap["code"])
            except ConnectorDefinition.DoesNotExist:
                self.stdout.write(f"    AI def '{ap['code']}' not seeded yet — run seed_connector_definitions first")
                continue

            inst, inst_created = ConnectorInstance.objects.get_or_create(
                definition=definition, name=ap["instance_name"],
                defaults={
                    "config": ap["config"],
                    "status": "unknown",
                    "is_active": True,
                },
            )
            if inst_created:
                self.stdout.write(f"  + AI Instance: {ap['instance_name']}")

            # Create a mock credential for each AI instance
            cred_name = f"{ap['code']}_api_key"
            mock_key = f"sk-mock-{uuid.uuid4().hex[:16]}"
            from integration.services.credential_service import encrypt_credential
            cred_val = encrypt_credential(mock_key)
            cred, cred_created = ConnectorCredential.objects.get_or_create(
                instance=inst,
                name="api_key",
                defaults={
                    "cred_type": "token",
                    "encrypted_value": cred_val,
                    "remark": f"Mock API key for {ap['name']}",
                },
            )
            if cred_created:
                self.stdout.write(f"    + Credential: api_key for {ap['name']}")

    def _create_cmdb_models(self):
        self.stdout.write("\n>>> Creating CMDB Model Definitions ...")
        from cmdb.models import ModelDefinition, ModelField
        for m in SAMPLE_CMDB_MODELS:
            obj, created = self._get_or_create(
                ModelDefinition, code=m["code"], name=m["name"],
                defaults_update={"category": m["category"]},
            )
            self.stdout.write(f"  {'+' if created else ' '} ModelDef: {m['name']} ({m['code']})")
            for f in m["fields"]:
                f_obj, f_created = self._get_or_create(
                    ModelField, model_definition=obj, name=f["name"],
                    defaults_update={"label": f["label"], "field_type": f["field_type"]},
                )
                if f_created:
                    self.stdout.write(f"    + Field: {f['label']}")

    def _create_audit_records(self):
        self.stdout.write("\n>>> Creating Operation Records ...")
        from opsflow.models import OperationRecord, OpsLog
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:3])
        actions = ["create", "update", "publish", "execute", "approve"]
        count = 0
        for t in templates:
            for idx, action in enumerate(actions):
                # Use unique detail + resource_id to avoid MultipleObjectsReturned
                detail = {"template_name": t.name, "version": t.version, "action_index": idx}
                op, created = OperationRecord.objects.get_or_create(
                    action=action,
                    resource_type="template",
                    resource_id=str(t.id),
                    operator=self.admin_user,
                    defaults={"detail": detail},
                )
                if created:
                    count += 1
        self.stdout.write(f"  + Created {count} OperationRecords")
