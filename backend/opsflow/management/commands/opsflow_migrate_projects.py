"""Management command — 迁移现有数据到默认项目

创建默认项目（如果不存在），将所有 project=None 的数据关联到默认项目。
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create default project and migrate orphan data"

    def handle(self, *args, **options):
        from opsflow.models import OpsProject, FlowTemplate, FlowExecution
        from opsflow.models import SchedulePlan, OpsKnowledge, ExecutionScheme

        # 1. 创建或获取默认项目
        default_project, created = OpsProject.objects.get_or_create(
            name="Default Project",
            defaults={
                "description": "Default project for existing data",
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created default project: {default_project}"))
        else:
            self.stdout.write(f"Using existing default project: {default_project}")

        # 2. 迁移所有 project=None 的数据
        migrated = {}

        for model, name in [
            (FlowTemplate, "templates"),
            (FlowExecution, "executions"),
            (SchedulePlan, "schedule_plans"),
            (OpsKnowledge, "knowledge"),
            (ExecutionScheme, "execution_schemes"),
        ]:
            count = model.objects.filter(project__isnull=True).update(project=default_project)
            if count:
                migrated[name] = count
                self.stdout.write(f"  Migrated {count} {name}")

        if migrated:
            self.stdout.write(self.style.SUCCESS(f"Migration complete: {migrated}"))
        else:
            self.stdout.write(self.style.WARNING("No orphan data found"))

        # 3. 确保 project owner 是成员
        from opsflow.models import ProjectMember
        member_count = 0
        for project in OpsProject.objects.filter(owner__isnull=False):
            _, created = ProjectMember.objects.get_or_create(
                project=project, user=project.owner,
                defaults={'role': ProjectMember.Role.ADMIN},
            )
            if created:
                member_count += 1
        if member_count:
            self.stdout.write(self.style.SUCCESS(f"Created {member_count} ADMIN memberships"))

        self.stdout.write(self.style.SUCCESS(f"Default project ID: {default_project.id}"))
