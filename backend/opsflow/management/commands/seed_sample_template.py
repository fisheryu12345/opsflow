"""Seed a sample template for new user onboarding
为新手用户创建示例模板种子数据

Usage:
    python manage.py seed_sample_template

Creates a published "Quick Start - Disk Check" template with a Shell plugin
pre-configured to run "df -h", so new users can immediately experience the
full template → execute workflow.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from opsflow.models import OpsProject, FlowTemplate
from opsflow.core.node_sync import sync_template_nodes

User = get_user_model()

SAMPLE_PIPELINE = {
    "nodes": [
        {
            "id": "node_1",
            "label": "Start",
            "node_type": "start_event",
        },
        {
            "id": "node_2",
            "label": "Disk Check",
            "atom_type": "shell",
            "node_type": "",
            "max_retries": 1,
            "retry_delay": 30,
            "timeout_seconds": 60,
            "params": {
                "command": "df -h",
                "timeout": 60,
            },
        },
        {
            "id": "node_3",
            "label": "End",
            "node_type": "end_event",
        },
    ],
    "edges": [
        {"from": "node_1", "to": "node_2", "label": "success"},
        {"from": "node_2", "to": "node_3", "label": "success"},
    ],
}

# Pipeline 2: Nginx health check with exclusive gateway + auto-restore
NGINX_HEALTH_PIPELINE = {
    "nodes": [
        {"id": "node_1", "label": "Start", "node_type": "start_event"},
        {"id": "node_2", "label": "Health Check Nginx", "atom_type": "health_check", "node_type": "",
         "params": {"host": "web-01", "ping_count": 2, "check_port": True, "port": 80},
         "max_retries": 1, "timeout_seconds": 30},
        {"id": "node_3", "label": "Healthy?", "node_type": "exclusive_gateway"},
        {"id": "node_4", "label": "Report OK", "atom_type": "send_alert", "node_type": "",
         "params": {"channel": "wecom", "title": "Nginx health check passed",
                    "content": "Nginx service on web-01 is healthy.", "recipients": "ops-team"},
         "max_retries": 1, "timeout_seconds": 15},
        {"id": "node_5", "label": "Restart Nginx", "atom_type": "service_control", "node_type": "",
         "params": {"service": "nginx", "action": "restart"},
         "max_retries": 2, "retry_delay": 10, "timeout_seconds": 30},
        {"id": "node_6", "label": "Send Alert", "atom_type": "send_alert", "node_type": "",
         "params": {"channel": "wecom", "title": "Nginx restarted due to failure",
                    "content": "Nginx was down on web-01, auto-restart executed.",
                    "recipients": "ops-team"},
         "max_retries": 1, "timeout_seconds": 15},
        {"id": "node_7", "label": "Converge", "node_type": "converge_gateway"},
        {"id": "node_8", "label": "End", "node_type": "end_event"},
    ],
    "edges": [
        {"from": "node_1", "to": "node_2", "label": "success"},
        {"from": "node_2", "to": "node_3", "label": "success"},
        {"from": "node_3", "to": "node_4", "label": "success"},
        {"from": "node_3", "to": "node_5", "label": "failure"},
        {"from": "node_4", "to": "node_7", "label": "success"},
        {"from": "node_5", "to": "node_6", "label": "success"},
        {"from": "node_5", "to": "node_7", "label": "failure"},
        {"from": "node_6", "to": "node_7", "label": "success"},
        {"from": "node_7", "to": "node_8", "label": "success"},
    ],
}


def _seed_template(project, name, category, desc, pipeline):
    from opsflow.models import FlowTemplate
    from opsflow.core.node_sync import sync_template_nodes
    tpl, created = FlowTemplate.objects.get_or_create(
        name=name,
        defaults={
            "project": project,
            "category": category,
            "description": desc,
            "is_draft": False,
            "is_public": True,
            "pipeline_tree": pipeline,
            "target_hosts": [],
            "global_vars": {},
            "version": 1,
        },
    )
    if created:
        tpl.publish_snapshot()
        sync_template_nodes(tpl)
        return tpl, True
    return tpl, False


class Command(BaseCommand):
    help = "Seed sample published templates for new user onboarding"

    def handle(self, *args, **options):
        project, created = OpsProject.objects.get_or_create(
            name="Demo Project",
            defaults={"description": "Auto-created demo project for onboarding"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created project: {project.name}"))
        else:
            self.stdout.write(f"Using existing project: {project.name}")

        templates = [
            ("Quick Start - Disk Check", "system",
             "Checks disk space via `df -h`. Published and ready to execute.",
             SAMPLE_PIPELINE),
            ("Nginx Health Check and Auto-Restore", "web",
             "Checks Nginx health on web-01 via ping+port 80. If healthy, reports OK. "
             "If down, auto-restarts nginx and sends alert. Demonstrates exclusive gateway.",
             NGINX_HEALTH_PIPELINE),
        ]

        for name, category, desc, pipeline in templates:
            tpl, created = _seed_template(project, name, category, desc, pipeline)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {tpl.name} (id={tpl.id})"))
            else:
                self.stdout.write(f"Already exists: {tpl.name} (id={tpl.id})")
