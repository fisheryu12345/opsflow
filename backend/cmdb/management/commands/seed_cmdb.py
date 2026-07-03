"""Seed CMDB model definitions"""

from django.core.management.base import BaseCommand
import json
from cmdb.models.model_definition import ModelDefinition, ModelField
from cmdb.models.classification import Classification

class Command(BaseCommand):
    help = "Seed CMDB model definitions"

    def handle(self, *args, **options):
        self._seed_cmdb_models()
        self.stdout.write(self.style.SUCCESS("Seed complete!"))

    def _seed_cmdb_models(self):
        from cmdb.models import Classification, AssociationType, ModelDefinition, ModelField, ModelAssociation, MainlineTopo

        # Classifications
        cls_data = [
            ("bk_biz_topo", "业务拓扑", ""), ("bk_host_manage", "主机管理", ""),
            ("bk_organization", "组织架构", ""), ("bk_network", "网络设备", ""),
            ("bk_uncategorized", "未分类", ""),
        ]
        for cls_id, name, desc in cls_data:
            Classification.objects.get_or_create(cls_id=cls_id, defaults={"name": name, "description": desc})
        self.stdout.write(f"  + Classifications: {len(cls_data)}")

        # Association types
        at_data = [
            ("BELONGS_TO", "属于", "属于", "包含", "dest_to_src"),
            ("CONTAINS", "包含", "包含", "属于", "src_to_dest"),
            ("RUNS", "运行", "运行进程", "运行在", "src_to_dest"),
            ("DEPENDS_ON", "依赖", "依赖", "被依赖", "bidirectional"),
            ("CONNECTS_TO", "连接", "连接到", "连接到", "bidirectional"),
        ]
        for code, name_d, name_s, name_t, direction in at_data:
            AssociationType.objects.get_or_create(
                asst_id=code,
                defaults={"name": name_t, "src_to_dest_note": name_s, "dest_to_src_note": name_d, "direction": direction},
            )
        self.stdout.write(f"  + AssociationTypes: {len(at_data)}")

        # Model definitions
        models_def = {
            "Biz": {"name": "业务", "cls_id": "bk_biz_topo",
                    "fields": [("name", "业务名"), ("lifecycle", "生命周期"), ("operator", "负责人"), ("description", "描述")]},
            "Set": {"name": "集群", "cls_id": "bk_biz_topo",
                    "fields": [("name", "集群名"), ("env_type", "环境类型"), ("description", "描述")]},
            "Module": {"name": "模块", "cls_id": "bk_biz_topo",
                       "fields": [("name", "模块名"), ("service_type", "服务类型"), ("description", "描述")]},
            "Host": {"name": "主机", "cls_id": "bk_host_manage",
                     "fields": [("ip", "IP地址"), ("hostname", "主机名"), ("os_type", "操作系统"),
                                ("cpu_cores", "CPU核数"), ("memory_mb", "内存(MB)"), ("disk_gb", "磁盘(GB)"),
                                ("status", "状态"), ("region", "地域"),
                                ("cloud_instance_id", "云实例ID"), ("cloud_type", "云厂商"), ("instance_type", "实例规格")]},
            "Process": {"name": "进程", "cls_id": "bk_host_manage",
                        "fields": [("name", "进程名"), ("port", "端口"), ("protocol", "协议"), ("status", "状态"), ("version", "版本")]},
        }

        md_count = f_count = 0
        for code, mdef in models_def.items():
            cls_obj = Classification.objects.filter(cls_id=mdef["cls_id"]).first()
            md, created = ModelDefinition.objects.get_or_create(code=code, defaults={"name": mdef["name"], "classification": cls_obj})
            if created:
                md_count += 1
            for fname, flabel in mdef["fields"]:
                _, fc = ModelField.objects.get_or_create(model_definition=md, name=fname, defaults={"label": flabel})
                if fc:
                    f_count += 1
        self.stdout.write(f"  + Models: {md_count}, Fields: {f_count}")

        # Associations (delete + recreate for idempotency)
        ModelAssociation.objects.all().delete()
        asso_data = [
            ("Biz", "Set", "CONTAINS", "1:n", "delete_target"),
            ("Set", "Module", "CONTAINS", "1:n", "delete_target"),
            ("Module", "Host", "CONTAINS", "1:n", "delete_target"),
            ("Host", "Process", "RUNS", "1:n", "delete_target"),
            ("Process", "Process", "DEPENDS_ON", "n:n", "none"),
        ]
        for src, dst, rel_type, cardinality, on_delete in asso_data:
            src_md = ModelDefinition.objects.filter(code=src).first()
            dst_md = ModelDefinition.objects.filter(code=dst).first()
            assoc_type = AssociationType.objects.filter(asst_id=rel_type).first()
            if src_md and dst_md and assoc_type:
                ModelAssociation.objects.create(
                    source_model=src_md, target_model=dst_md,
                    association_type=assoc_type, mapping=cardinality, on_delete=on_delete,
                )

        # Mainline
        ml_data = [("Biz", None, 1), ("Set", "Biz", 2), ("Module", "Set", 3), ("Host", "Module", 4)]
        for code, parent_code, sort_order in ml_data:
            md = ModelDefinition.objects.filter(code=code).first()
            pmd = ModelDefinition.objects.filter(code=parent_code).first() if parent_code else None
            if md:
                MainlineTopo.objects.get_or_create(model_definition=md, defaults={"parent_model": pmd, "sort_order": sort_order})
        self.stdout.write(f"  + CMDB Mainline topology: {len(ml_data)} levels")

    # ── 5. Monitor Plugins ──
