"""FcDesigner settings — per-business form designer UI preferences"""
from django.db import models
from common.utils.models import CoreModel, table_prefix


class FcDesignerSettings(CoreModel):
    """Per-business FcDesigner UI settings — shared across all projects/users in a business."""
    business = models.ForeignKey(
        'iam.Business', on_delete=models.CASCADE,
        db_constraint=False, verbose_name="所属业务线"
    )
    value = models.JSONField(default=dict, verbose_name="设置值")

    class Meta:
        db_table = table_prefix + "itsm_fc_designer_settings"
        verbose_name = "表单设计器设置"
        verbose_name_plural = verbose_name
        unique_together = [("business",)]
