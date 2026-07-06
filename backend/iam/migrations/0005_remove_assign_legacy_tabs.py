# -*- coding: utf-8 -*-
"""Remove skill-groups, on-duty, escalation tabs — legacy assign engine removed"""
from django.db import migrations


def remove_tabs(apps, schema_editor):
    PageTab = apps.get_model('iam', 'PageTab')
    PageButton = apps.get_model('iam', 'PageButton')

    for tab in PageTab.objects.filter(app='itsm', key__in=('skill-groups', 'on-duty', 'escalation')):
        PageButton.objects.filter(tab=tab).delete()
        tab.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('iam', '0004_remove_assign_rules_tab'),
    ]

    operations = [
        migrations.RunPython(remove_tabs),
    ]
