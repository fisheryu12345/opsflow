# -*- coding: utf-8 -*-
"""Delete legacy model tables — replaced by unified Ticket + workflow engine"""
from django.db import migrations

LEGACY_TABLES = [
    'opsflow_itsm_problem_related_incidents',  # M2M — drop first
    'opsflow_itsm_incident',
    'opsflow_itsm_change',
    'opsflow_itsm_service_request',
    'opsflow_itsm_problem',
    'opsflow_itsm_skill_group',
    'opsflow_itsm_on_duty_schedule',
    'opsflow_itsm_assign_rule',
    'opsflow_itsm_escalation_level',
    'opsflow_itsm_ticket_transfer_log',
]


def drop_legacy_tables(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    with schema_editor.connection.cursor() as cursor:
        if vendor == 'mysql':
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in LEGACY_TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        if vendor == 'mysql':
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


class Migration(migrations.Migration):

    dependencies = [
        ('itsm', '0008_remove_servicecategory_auto_assign_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_legacy_tables),
            ],
            state_operations=[
                migrations.DeleteModel('TicketTransferLog'),
                migrations.DeleteModel('EscalationLevel'),
                migrations.DeleteModel('AssignRule'),
                migrations.DeleteModel('OnDutySchedule'),
                migrations.DeleteModel('SkillGroup'),
                migrations.DeleteModel('Problem'),
                migrations.DeleteModel('ServiceRequest'),
                migrations.DeleteModel('Change'),
                migrations.DeleteModel('Incident'),
            ],
        ),
    ]
