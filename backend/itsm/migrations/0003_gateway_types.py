# -*- coding: utf-8 -*-
# Generated manually — ITSM 网关类型命名对齐
"""ROUTER_P → CONDITIONAL_PARALLEL, 新增 EXCLUSIVE/PARALLEL, 移除 WEBHOOK"""

from django.db import migrations, models


def rename_router_p(apps, schema_editor):
    State = apps.get_model('itsm', 'State')
    State.objects.filter(type='ROUTER_P').update(type='CONDITIONAL_PARALLEL')


class Migration(migrations.Migration):

    dependencies = [
        ('itsm', '0002_ticket_pipeline_id_db_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='state',
            name='type',
            field=models.CharField(
                choices=[
                    ('START', '开始'),
                    ('END', '结束'),
                    ('NORMAL', '普通节点'),
                    ('APPROVAL', '审批'),
                    ('SIGN', '会签'),
                    ('TASK', '自动任务'),
                    ('CONDITIONAL_PARALLEL', '条件并行网关'),
                    ('EXCLUSIVE', '排他网关'),
                    ('PARALLEL', '并行网关'),
                    ('COVERAGE', '汇聚网关'),
                ],
                max_length=32, verbose_name='节点类型',
            ),
        ),
        migrations.AlterField(
            model_name='transition',
            name='condition_type',
            field=models.CharField(
                choices=[('default', '默认'), ('by_field', '字段判断')],
                default='default', max_length=16, verbose_name='条件类型',
            ),
        ),
        migrations.RunPython(rename_router_p),
    ]
