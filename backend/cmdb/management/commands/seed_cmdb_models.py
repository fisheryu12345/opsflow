# -*- coding: utf-8 -*-
"""Seed built-in CMDB model definitions into MySQL

Usage:
    python manage.py seed_cmdb_models

Creates built-in classifications, association types, model definitions,
and default fields required for OpsFlow CMDB operation.
"""

from django.core.management.base import BaseCommand

# ─── 预置分类 ───
BUILTIN_CLASSIFICATIONS = [
    ('bk_biz_topo', '业务拓扑', ''),
    ('bk_host_manage', '主机管理', ''),
    ('bk_organization', '组织架构', ''),
    ('bk_network', '网络设备', ''),
    ('bk_uncategorized', '未分类', ''),
]

# ─── 预置关联类型 ───
BUILTIN_ASSOCIATION_TYPES = [
    ('BELONGS_TO', '属于', '属于', '包含', 'dest_to_src'),
    ('CONTAINS', '包含', '包含', '属于', 'src_to_dest'),
    ('RUNS', '运行', '运行进程', '运行在', 'src_to_dest'),
    ('DEPENDS_ON', '依赖', '依赖', '被依赖', 'bidirectional'),
    ('CONNECTS_TO', '连接', '连接到', '连接到', 'bidirectional'),
]

# ─── 预置模型定义 ───
BUILTIN_MODELS = {
    'Biz': {
        'name': '业务',
        'cls_id': 'bk_biz_topo',
        'description': '业务 (Business)，最顶层组织单元',
        'fields': [
            ('name', '业务名称', 'string', True, None, 'basic'),
            ('lifecycle', '生命周期', 'enum', False, ['生产', '测试', '开发', '预发'], 'basic'),
            ('operator', '负责人', 'string', False, None, 'basic'),
            ('description', '描述', 'string', False, None, 'basic'),
        ],
    },
    'Set': {
        'name': '集群',
        'cls_id': 'bk_biz_topo',
        'description': '集群 (Cluster/Set)，业务下的集群单元',
        'fields': [
            ('name', '集群名称', 'string', True, None, 'basic'),
            ('env_type', '环境类型', 'enum', False, ['生产', '测试', '开发'], 'basic'),
            ('description', '描述', 'string', False, None, 'basic'),
        ],
    },
    'Module': {
        'name': '模块',
        'cls_id': 'bk_biz_topo',
        'description': '模块 (Module)，集群下的功能模块',
        'fields': [
            ('name', '模块名称', 'string', True, None, 'basic'),
            ('service_type', '服务类型', 'enum', False, ['web', 'db', 'cache', 'mq', 'lb', 'other'], 'basic'),
            ('description', '描述', 'string', False, None, 'basic'),
        ],
    },
    'Host': {
        'name': '主机',
        'cls_id': 'bk_host_manage',
        'description': '主机 (Host)，物理机/虚拟机/容器实例',
        'fields': [
            ('ip', 'IP 地址', 'ip', True, None, 'network'),
            ('hostname', '主机名', 'string', False, None, 'basic'),
            ('os_type', '操作系统', 'enum', False, ['linux', 'windows', 'aix'], 'basic'),
            ('os_version', '操作系统版本', 'string', False, None, 'basic'),
            ('cpu_cores', 'CPU 核数', 'integer', False, None, 'hardware'),
            ('memory_mb', '内存(MB)', 'integer', False, None, 'hardware'),
            ('disk_gb', '磁盘(GB)', 'integer', False, None, 'hardware'),
            ('status', '状态', 'enum', False, ['normal', 'alarm', 'offline', 'maintenance', 'unknown'], 'basic'),
            ('agent_status', 'Agent 状态', 'enum', False, ['online', 'offline', 'unknown'], 'basic'),
            ('cloud_instance_id', '云实例 ID', 'string', False, None, 'cloud'),
            ('private_ip', '内网 IP', 'ip', False, None, 'network'),
            ('public_ip', '公网 IP', 'ip', False, None, 'network'),
            ('region', '地域', 'string', False, None, 'cloud'),
        ],
    },
    'Process': {
        'name': '进程',
        'cls_id': 'bk_host_manage',
        'description': '进程 (Process)，主机上的服务进程',
        'fields': [
            ('name', '进程名称', 'string', True, None, 'basic'),
            ('port', '端口', 'integer', False, None, 'basic'),
            ('protocol', '协议', 'enum', False, ['tcp', 'udp', 'http', 'grpc'], 'basic'),
            ('status', '状态', 'enum', False, ['running', 'stopped', 'error'], 'basic'),
            ('version', '版本', 'string', False, None, 'basic'),
        ],
    },
}

# ─── 预置模型关联 ───
BUILTIN_ASSOCIATIONS = [
    ('Biz', 'Set', 'CONTAINS', '1:n', 'delete_target'),
    ('Set', 'Module', 'CONTAINS', '1:n', 'delete_target'),
    ('Module', 'Host', 'CONTAINS', '1:n', 'delete_target'),
    ('Host', 'Process', 'RUNS', '1:n', 'delete_target'),
    ('Process', 'Process', 'DEPENDS_ON', 'n:n', 'none'),
]

# ─── 预置主线拓扑 ───
BUILTIN_MAINLINE = [
    ('Biz', None, 1),
    ('Set', 'Biz', 2),
    ('Module', 'Set', 3),
    ('Host', 'Module', 4),
]


class Command(BaseCommand):
    help = "Seed built-in CMDB model definitions into MySQL"

    def handle(self, *args, **options):
        from cmdb.models.classification import Classification
        from cmdb.models.model_definition import ModelDefinition, ModelField
        from cmdb.models.attribute_group import AttributeGroup
        from cmdb.models.association import AssociationType, ModelAssociation
        from cmdb.models.mainline_topo import MainlineTopo

        # 1. 创建分类
        self.stdout.write("--- 创建分类 ---")
        cls_map = {}
        for cls_id, name, icon in BUILTIN_CLASSIFICATIONS:
            cls, created = Classification.objects.get_or_create(
                cls_id=cls_id,
                defaults={'name': name, 'icon': icon},
            )
            cls_map[cls_id] = cls
            self.stdout.write(f"  {'[OK]' if created else '[--]'} {name} ({cls_id})")

        # 2. 创建关联类型
        self.stdout.write("\n--- 创建关联类型 ---")
        asst_map = {}
        for asst_id, name, src_note, dst_note, direction in BUILTIN_ASSOCIATION_TYPES:
            asst_created, created = AssociationType.objects.get_or_create(
                asst_id=asst_id,
                defaults={
                    'name': name,
                    'src_to_dest_note': src_note,
                    'dest_to_src_note': dst_note,
                    'direction': direction,
                },
            )
            asst_map[asst_id] = asst_created
            self.stdout.write(f"  {'[OK]' if created else '[--]'} {name} ({asst_id})")

        # 3. 创建模型定义、属性分组、字段
        self.stdout.write("\n--- 创建模型定义 ---")
        model_map = {}
        group_map = {}

        for code, data in BUILTIN_MODELS.items():
            model_def, created = ModelDefinition.objects.get_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'classification': cls_map.get(data['cls_id']),
                    'description': data['description'],
                    'is_builtin': True,
                    'source': 'builtin',
                },
            )
            model_map[code] = model_def
            self.stdout.write(f"  {'[OK]' if created else '[--]'} {data['name']} ({code})")

            # 自动创建属性分组、字段
            groups_seen = set()
            for sort_idx, (name, label, field_type, required, options, group_id) in enumerate(data['fields']):
                # 创建分组
                if group_id and group_id not in groups_seen:
                    grp, _ = AttributeGroup.objects.get_or_create(
                        model_definition=model_def,
                        group_id=group_id,
                        defaults={
                            'name': {'basic': '基本信息', 'hardware': '硬件规格',
                                     'network': '网络配置', 'cloud': '云属性'}.get(
                                group_id, group_id),
                            'sort_order': len(groups_seen),
                        },
                    )
                    group_map[(code, group_id)] = grp
                    groups_seen.add(group_id)

                field_created, _ = ModelField.objects.get_or_create(
                    model_definition=model_def,
                    name=name,
                    defaults={
                        'label': label,
                        'field_type': field_type,
                        'required': required,
                        'options': options,
                        'sort_order': sort_idx,
                        'group': group_map.get((code, group_id)),
                    },
                )
                if field_created:
                    self.stdout.write(f"       field: {label} ({name})")

        # 4. 创建模型关联
        self.stdout.write("\n--- 创建模型关联 ---")
        for src_code, tgt_code, asst_id, mapping, on_delete in BUILTIN_ASSOCIATIONS:
            assoc, created = ModelAssociation.objects.get_or_create(
                source_model=model_map[src_code],
                target_model=model_map[tgt_code],
                association_type=asst_map[asst_id],
                defaults={
                    'mapping': mapping,
                    'on_delete': on_delete,
                    'is_pre': True,
                },
            )
            self.stdout.write(f"  {'[OK]' if created else '[--]'} {src_code} -[{asst_id}]-> {tgt_code}")

        # 5. 创建主线拓扑
        self.stdout.write("\n--- 创建主线拓扑 ---")
        for code, parent_code, sort_order in BUILTIN_MAINLINE:
            topo, created = MainlineTopo.objects.get_or_create(
                model_definition=model_map[code],
                defaults={
                    'parent_model': model_map.get(parent_code),
                    'sort_order': sort_order,
                },
            )
            parent_name = parent_code or "ROOT"
            self.stdout.write(f"  {'[OK]' if created else '[--]'} {parent_name} → {code}")

        self.stdout.write(self.style.SUCCESS(
            "\n[OK] 种子数据创建完成!"
        ))
