# -*- coding: utf-8 -*-
"""Remove legacy assign-rules tab — assignment now driven by node processors"""
from django.db import migrations


def remove_assign_rules_tab(apps, schema_editor):
    PageTab = apps.get_model('iam', 'PageTab')
    PageButton = apps.get_model('iam', 'PageButton')

    for tab in PageTab.objects.filter(app='itsm', key__in=('assign-rules',)):
        PageButton.objects.filter(tab=tab).delete()
        tab.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('iam', '0003_remove_legacy_tabs'),
    ]

    operations = [
        migrations.RunPython(remove_assign_rules_tab),
    ]
