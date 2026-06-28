"""Seed mock OpsAgent data"""

from django.core.management.base import BaseCommand
from opsagent.models import Session,EnvironmentContext,AgentMemory,AuditRecord
from django.utils import timezone

class Command(BaseCommand):
    help = "Seed mock OpsAgent data"

    def handle(self, *args, **options):
        self._create_opsagent_data()
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
