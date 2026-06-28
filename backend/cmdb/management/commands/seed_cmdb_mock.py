"""Seed mock CMDB instances/models"""

from django.core.management.base import BaseCommand
from cmdb.services.node_service import NodeService

class Command(BaseCommand):
    help = "Seed mock CMDB instances/models"

    def handle(self, *args, **options):
        self._create_cmdb_models()
        self._create_cmdb_instances()
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

    def _create_cmdb_models(self):
        self.stdout.write("\n>>> Creating CMDB Model Definitions ...")
        from cmdb.models import Classification, ModelDefinition, ModelField
        for m in SAMPLE_CMDB_MODELS:
            cls_obj = Classification.objects.filter(cls_id=m["cls_id"]).first()
            obj, created = self._get_or_create(
                ModelDefinition, code=m["code"], name=m["name"],
                defaults_update={"classification": cls_obj, "source": "custom"},
            )
            self.stdout.write(f"  {'+' if created else ' '} ModelDef: {m['name']} ({m['code']})")
            for f in m["fields"]:
                f_obj, f_created = self._get_or_create(
                    ModelField, model_definition=obj, name=f["name"],
                    defaults_update={"label": f["label"], "field_type": f["field_type"]},
                )
                if f_created:
                    self.stdout.write(f"    + Field: {f['label']}")

    def _create_cmdb_instances(self):
        """创建 CMDB 实例数据到 Neo4j 及拓扑关联"""
        self.stdout.write("\n>>> Creating CMDB Neo4j Instances ...")
        from cmdb.services.node_service import NodeService
        from cmdb.services.association_service import AssociationService

        asst = AssociationService()
        created_map = {}  # (model_code, name_or_ip) -> instance_id

        # 1. 创建所有节点
        for model_code, records in SAMPLE_CMDB_INSTANCES.items():
            svc = NodeService(model_code)
            for rec in records:
                key_name = rec.get('name') or rec.get('ip') or rec.get('hostname', '')
                try:
                    instance = svc.create(rec)
                    created_map[(model_code, key_name)] = instance['instance_id']
                    self.stdout.write(f"  + {model_code}: {key_name}")
                except Exception as e:
                    self.stdout.write(f"    ~ {model_code}: {key_name} (skip: {e})")

        # 2. 建立拓扑关联
        self.stdout.write(">>> Creating CMDB Topology Relations ...")
        for biz_name, set_name, mod_name, host_ip, proc_name in CMDB_TOPOLOGY:
            biz_id = created_map.get(('Biz', biz_name))
            set_id = created_map.get(('Set', set_name))
            mod_id = created_map.get(('Module', mod_name))
            host_id = created_map.get(('Host', host_ip))
            proc_id = created_map.get(('Process', proc_name))

            if biz_id and set_id:
                try:
                    asst.create_relation(biz_id, set_id, 'CONTAINS')
                except Exception:
                    pass
            if set_id and mod_id:
                try:
                    asst.create_relation(set_id, mod_id, 'CONTAINS')
                except Exception:
                    pass
            if mod_id and host_id:
                try:
                    asst.create_relation(mod_id, host_id, 'CONTAINS')
                except Exception:
                    pass
            if host_id and proc_id:
                try:
                    asst.create_relation(host_id, proc_id, 'RUNS')
                except Exception:
                    pass

        self.stdout.write(f"  Created {len(CMDB_TOPOLOGY)} topology relations")
