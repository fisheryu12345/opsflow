# Generated migration — add preset FK to Field model for options preset reuse

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('itsm', '0003_preset_project_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='preset',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='field_defs', to='itsm.preset', verbose_name='关联预设',
            ),
        ),
    ]
