# -*- coding: utf-8 -*-
"""Seed built-in CMDB model definitions into MySQL

Usage:
    python manage.py seed_cmdb_models

Creates the 5 built-in CMDB models (Biz, Set, Module, Host, Process)
with their default field definitions.
"""

from django.core.management.base import BaseCommand

BUILTIN_MODELS = {
    'biz': {
        'name': '业务',
        'description': '业务 (Business)，最顶层组织单元',
        'fields': [
            ('name', '业务名称', 'string', True),
            ('lifecycle', '生命周期', 'enum', False),
            ('operator', '负责人', 'string', False),
            ('description', '描述', 'string', False),
        ],
    },
    'set': {
        'name': '集群',
        'description': '集群 (Cluster/Set)，业务下的集群单元',
        'fields': [
            ('name', '集群名称', 'string', True),
            ('env_type', '环境类型', 'enum', False),
            ('description', '描述', 'string', False),
        ],
    },
    'module': {
        'name': '模块',
        'description': '模块 (Module)，集群下的功能模块',
        'fields': [
            ('name', '模块名称', 'string', True),
            ('service_type', '服务类型', 'enum', False),
            ('description', '描述', 'string', False),
        ],
    },
    'host': {
        'name': '主机',
        'description': '主机 (Host)，物理机/虚拟机/容器实例',
        'fields': [
            ('ip', 'IP 地址', 'ip', True),
            ('hostname', '主机名', 'string', False),
            ('os_type', '操作系统', 'enum', False),
            ('cpu_cores', 'CPU 核数', 'integer', False),
            ('memory_mb', '内存(MB)', 'integer', False),
            ('disk_gb', '磁盘(GB)', 'integer', False),
            ('status', '状态', 'enum', False),
            ('agent_status', 'Agent 状态', 'enum', False),
            ('region', '地域', 'string', False),
        ],
    },
    'process': {
        'name': '进程',
        'description': '进程 (Process)，主机上的服务进程',
        'fields': [
            ('name', '进程名称', 'string', True),
            ('port', '端口', 'integer', False),
            ('protocol', '协议', 'enum', False),
            ('status', '状态', 'enum', False),
            ('version', '版本', 'string', False),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed built-in CMDB model definitions into MySQL"

    def handle(self, *args, **options):
        from cmdb.models.model_schema import ModelDefinition, ModelField

        created_count = 0
        for code, data in BUILTIN_MODELS.items():
            model_def, created = ModelDefinition.objects.get_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                    'category': code if code in ('business', 'custom') else code,
                    'is_builtin': True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  [OK] Created model: {data['name']} ({code})")
            else:
                self.stdout.write(f"  [--] Model already exists: {code}")

            # Seed fields
            for sort_idx, (name, label, field_type, required) in enumerate(data['fields']):
                _, field_created = ModelField.objects.get_or_create(
                    model_definition=model_def,
                    name=name,
                    defaults={
                        'label': label,
                        'field_type': field_type,
                        'required': required,
                        'sort_order': sort_idx,
                    },
                )
                if field_created:
                    self.stdout.write(f"       field: {label} ({name})")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Created {created_count} built-in models."))
