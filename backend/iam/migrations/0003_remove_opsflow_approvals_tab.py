"""Data migration — remove the deprecated OpsFlow 'approvals' tab.

The OpsFlow Approval Center was retired; approval is delegated to ITSM.
The seed command uses get_or_create and does not prune stale rows, so we
delete the existing PageTab and IAMPermission here (role bindings cascade
via IAMRolePermission's FK on_delete=CASCADE).
"""
from django.db import migrations


def remove_approvals_tab(apps, schema_editor):
    PageTab = apps.get_model('iam', 'PageTab')
    IAMPermission = apps.get_model('iam', 'IAMPermission')
    PageTab.objects.filter(app='opsflow', key='approvals').delete()
    IAMPermission.objects.filter(codename='opsflow:approvals:view').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('iam', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(remove_approvals_tab, migrations.RunPython.noop),
    ]
