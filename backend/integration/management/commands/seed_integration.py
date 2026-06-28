"""Seed connector definitions"""

from django.core.management.base import BaseCommand
from integration.models.connector import ConnectorDefinition

class Command(BaseCommand):
    help = "Seed connector definitions"

    def handle(self, *args, **options):
        self._seed_connector_definitions()
        self.stdout.write(self.style.SUCCESS("Seed complete!"))

    def _seed_connector_definitions(self):
        from integration.models.connector import ConnectorDefinition

        # Helper: build config_schema with a simple list of {key, title, type, required, default}
        def _schema(fields: list) -> dict:
            props = {}
            required = []
            for f in fields:
                ftype = f.get("type", "string")
                schema_type = "string"
                if ftype == "int":
                    schema_type = "integer"
                elif ftype == "bool":
                    schema_type = "boolean"
                elif ftype == "select":
                    schema_type = "string"
                props[f["key"]] = {
                    "type": schema_type,
                    "title": f["title"],
                    "default": f.get("default", ""),
                    "description": f.get("desc", ""),
                }
                if f.get("select_options"):
                    props[f["key"]]["enum"] = f["select_options"]
                if f.get("required", False):
                    required.append(f["key"])
            return {"type": "object", "properties": props, "required": required}

        connectors = [
            # ─── Cloud ───
            {"code": "aliyun_ecs", "name": "阿里云 ECS", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "地域", "default": "cn-hangzhou", "required": True},
                 {"key": "endpoint", "title": "Endpoint", "default": "ecs.aliyuncs.com"},
             ])},
            {"code": "tencent_cvm", "name": "腾讯云 CVM", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "地域", "default": "ap-guangzhou", "required": True},
             ])},
            {"code": "huawei_ecs", "name": "华为云 ECS", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "区域", "default": "cn-east-3"},
             ])},
            {"code": "aws_ec2", "name": "AWS EC2", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Region", "default": "us-east-1", "required": True},
             ])},
            {"code": "azure_vm", "name": "Azure VM", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Location", "default": "eastus"},
             ])},
            {"code": "gcp_compute", "name": "GCP Compute Engine", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Region", "default": "us-central1"},
                 {"key": "project_id", "title": "Project ID", "required": True},
             ])},
            # ─── Notification ───
            {"code": "aliyun_sms", "name": "阿里云短信", "category": "notification",
             "config_schema": _schema([
                 {"key": "sign_name", "title": "短信签名", "required": True},
             ])},
            {"code": "wecom_bot", "name": "企业微信 Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook 地址", "required": True},
             ])},
            {"code": "dingtalk_bot", "name": "钉钉 Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook 地址", "required": True},
             ])},
            {"code": "email_smtp", "name": "邮件 (SMTP)", "category": "notification",
             "config_schema": _schema([
                 {"key": "smtp_host", "title": "SMTP 服务器", "required": True},
                 {"key": "smtp_port", "title": "端口", "type": "int", "default": 465},
                 {"key": "from_address", "title": "发件地址", "required": True},
             ])},
            {"code": "slack", "name": "Slack", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook URL", "required": True},
                 {"key": "channel", "title": "默认频道", "default": "#general"},
             ])},
            {"code": "teams", "name": "Microsoft Teams", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook URL", "required": True},
             ])},
            {"code": "telegram_bot", "name": "Telegram Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "bot_token", "title": "Bot Token", "required": True},
                 {"key": "chat_id", "title": "默认 Chat ID"},
             ])},
            # ─── Auth ───
            {"code": "ldap", "name": "LDAP 认证源", "category": "auth",
             "config_schema": _schema([
                 {"key": "host", "title": "LDAP 服务器", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 389},
                 {"key": "base_dn", "title": "Base DN", "required": True},
             ])},
            {"code": "oauth2_oidc", "name": "OAuth2 / OIDC", "category": "auth",
             "config_schema": _schema([
                 {"key": "issuer_url", "title": "Issuer URL", "required": True},
                 {"key": "authorization_endpoint", "title": "授权端点"},
                 {"key": "token_endpoint", "title": "Token 端点"},
             ])},
            {"code": "saml_idp", "name": "SAML IdP", "category": "auth",
             "config_schema": _schema([
                 {"key": "entity_id", "title": "Entity ID", "required": True},
                 {"key": "sso_url", "title": "SSO URL", "required": True},
             ])},
            # ─── AI ───
            {"code": "openai", "name": "OpenAI", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.openai.com"},
                 {"key": "model", "title": "默认模型", "default": "gpt-4o"},
             ])},
            {"code": "deepseek", "name": "DeepSeek", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.deepseek.com"},
                 {"key": "model", "title": "默认模型", "default": "deepseek-chat"},
             ])},
            {"code": "anthropic", "name": "Anthropic Claude", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.anthropic.com"},
                 {"key": "model", "title": "默认模型", "default": "claude-sonnet-4-20250514"},
             ])},
            {"code": "tongyi_qwen", "name": "通义千问 (Qwen)", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://dashscope.aliyuncs.com"},
                 {"key": "model", "title": "默认模型", "default": "qwen-plus"},
             ])},
            {"code": "local_llm", "name": "本地 LLM (OpenAI 兼容)", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "http://localhost:8000/v1", "required": True},
                 {"key": "model", "title": "默认模型", "default": "local-model"},
             ])},
            {"code": "gemini", "name": "Google Gemini", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://generativelanguage.googleapis.com"},
                 {"key": "model", "title": "默认模型", "default": "gemini-2.0-flash"},
             ])},
            # ─── Automation ───
            {"code": "ansible", "name": "Ansible", "category": "automation",
             "config_schema": _schema([
                 {"key": "host", "title": "控制节点地址"},
                 {"key": "port", "title": "SSH 端口", "type": "int", "default": 22},
             ])},
            {"code": "awx", "name": "AWX / Ansible Tower", "category": "automation",
             "version": "1.0", "provider_class": "integration.adapters.automation.awx.AWXConnector",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://localhost:8080/api/v2", "required": True},
                 {"key": "verify_ssl", "title": "Verify SSL", "type": "bool", "default": False},
                 {"key": "timeout", "title": "Timeout (s)", "type": "int", "default": 30},
                 {"key": "template_id", "title": "默认 Template ID", "type": "int", "default": 1},
             ])},
            {"code": "saltstack", "name": "SaltStack", "category": "automation",
             "config_schema": _schema([
                 {"key": "master_url", "title": "Master 地址", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 4506},
             ])},
            {"code": "puppet", "name": "Puppet", "category": "automation",
             "config_schema": _schema([
                 {"key": "server_url", "title": "Puppet Server", "required": True},
             ])},
            # ─── Database ───
            {"code": "neo4j", "name": "Neo4j 图数据库", "category": "other",
             "version": "1.0", "provider_class": "integration.adapters.database.neo4j.Neo4jConnector",
             "config_schema": _schema([
                 {"key": "host", "title": "主机地址", "default": "127.0.0.1"},
                 {"key": "port", "title": "端口", "type": "int", "default": 7687},
                 {"key": "protocol", "title": "协议", "default": "bolt"},
                 {"key": "user", "title": "默认用户", "default": "neo4j"},
             ])},
            # ─── CI/CD ───
            {"code": "jenkins", "name": "Jenkins", "category": "cicd",
             "config_schema": _schema([
                 {"key": "url", "title": "Jenkins URL", "required": True},
             ])},
            {"code": "gitlab_ci", "name": "GitLab CI", "category": "cicd",
             "config_schema": _schema([
                 {"key": "url", "title": "GitLab URL", "default": "https://gitlab.com"},
             ])},
            {"code": "github_actions", "name": "GitHub Actions", "category": "cicd",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.github.com"},
             ])},
            {"code": "argocd", "name": "ArgoCD", "category": "cicd",
             "config_schema": _schema([
                 {"key": "server_url", "title": "ArgoCD Server", "required": True},
             ])},
            # ─── SCM ───
            {"code": "gitlab", "name": "GitLab", "category": "scm",
             "config_schema": _schema([
                 {"key": "url", "title": "GitLab URL", "default": "https://gitlab.com"},
             ])},
            {"code": "github", "name": "GitHub", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.github.com"},
             ])},
            {"code": "bitbucket", "name": "Bitbucket", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.bitbucket.org"},
             ])},
            {"code": "gitee", "name": "Gitee (码云)", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://gitee.com/api"},
             ])},
            # ─── Log / Observability ───
            {"code": "elasticsearch", "name": "Elasticsearch", "category": "log",
             "config_schema": _schema([
                 {"key": "hosts", "title": "节点地址", "default": "http://localhost:9200", "required": True},
             ])},
            {"code": "graylog", "name": "Graylog", "category": "log",
             "config_schema": _schema([
                 {"key": "url", "title": "Graylog URL", "required": True},
             ])},
            {"code": "loki", "name": "Grafana Loki", "category": "log",
             "config_schema": _schema([
                 {"key": "url", "title": "Loki URL", "default": "http://localhost:3100"},
             ])},
            {"code": "splunk", "name": "Splunk", "category": "log",
             "config_schema": _schema([
                 {"key": "host", "title": "Splunk Host", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 8089},
             ])},
            # ─── Monitor ───
            {"code": "prometheus", "name": "Prometheus", "category": "monitor",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "http://localhost:9090", "required": True},
             ])},
            {"code": "grafana", "name": "Grafana", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Grafana URL", "default": "http://localhost:3000"},
             ])},
            {"code": "zabbix", "name": "Zabbix", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Zabbix URL", "required": True},
             ])},
            {"code": "nagios", "name": "Nagios", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Nagios URL", "default": "http://localhost/nagios"},
             ])},
            {"code": "datadog", "name": "Datadog", "category": "monitor",
             "config_schema": _schema([
                 {"key": "site", "title": "Site", "default": "datadoghq.com"},
             ])},
            # ─── PaaS / Container ───
            {"code": "kubernetes", "name": "Kubernetes", "category": "paas",
             "config_schema": _schema([
                 {"key": "api_server", "title": "API Server", "required": True},
                 {"key": "namespace", "title": "默认 Namespace", "default": "default"},
             ])},
            {"code": "docker", "name": "Docker", "category": "paas",
             "config_schema": _schema([
                 {"key": "host", "title": "Docker Host", "default": "unix:///var/run/docker.sock"},
             ])},
            {"code": "rancher", "name": "Rancher", "category": "paas",
             "config_schema": _schema([
                 {"key": "server_url", "title": "Rancher URL", "required": True},
             ])},
            {"code": "openshift", "name": "OpenShift", "category": "paas",
             "config_schema": _schema([
                 {"key": "api_server", "title": "API Server", "required": True},
             ])},
            # ─── ITSM / Ops ───
            {"code": "jira", "name": "Jira", "category": "other",
             "config_schema": _schema([
                 {"key": "url", "title": "Jira URL", "required": True},
             ])},
            {"code": "confluence", "name": "Confluence", "category": "other",
             "config_schema": _schema([
                 {"key": "url", "title": "Confluence URL", "required": True},
             ])},
            {"code": "pagerduty", "name": "PagerDuty", "category": "other",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.pagerduty.com"},
             ])},
            {"code": "opsgenie", "name": "Opsgenie", "category": "other",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.opsgenie.com"},
             ])},
            {"code": "service_now", "name": "ServiceNow", "category": "other",
             "config_schema": _schema([
                 {"key": "instance_url", "title": "Instance URL", "required": True},
             ])},
        ]
        c_count = 0
        for c in connectors:
            _, created = ConnectorDefinition.objects.update_or_create(
                code=c["code"], defaults=c
            )
            if created:
                c_count += 1
        self.stdout.write(f">>> Connector Definitions: {c_count} new, {len(connectors) - c_count} existing (config_schema updated)")
        self.stdout.write(f"    新增 {c_count} 个连接器定义，{len(connectors) - c_count} 个已有定义配置已同步")

    # ── 7. IAM Menu ──
