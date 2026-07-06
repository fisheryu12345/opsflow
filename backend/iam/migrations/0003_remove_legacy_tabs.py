# -*- coding: utf-8 -*-
"""Remove legacy incidents/changes tabs — unified Ticket model replaces them"""
from django.db import migrations


def remove_legacy_tabs(apps, schema_editor):
    PageTab = apps.get_model('iam', 'PageTab')
    PageButton = apps.get_model('iam', 'PageButton')

    for tab in PageTab.objects.filter(app='itsm', key__in=('incidents', 'changes')):
        PageButton.objects.filter(tab=tab).delete()
        tab.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('iam', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(remove_legacy_tabs),
    ]
