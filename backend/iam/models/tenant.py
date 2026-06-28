"""Tenant models — BusinessGroup, Business, DeployEnvironment

Business: core isolation unit, the permission base for all sub-products.
DeployEnvironment: global cross-cutting deployment target (dev/staging/prod),
  independent of Business hierarchy.
"""
from django.db import models


class BusinessGroup(models.Model):
    """Optional visual grouping for businesses — no permission semantics"""
    name = models.CharField(
        max_length=128, unique=True, verbose_name="Name",
        help_text="业务群组名称 / Business group display name"
    )
    code = models.SlugField(
        max_length=32, unique=True, verbose_name="Code",
        help_text="业务群组代码 / Unique slug identifier"
    )
    sort = models.IntegerField(
        default=0, verbose_name="Sort Order",
        help_text="排序 / Display order"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Is Active",
        help_text="是否启用 / Whether this group is active"
    )

    class Meta:
        db_table = 'iam_business_group'
        verbose_name = "Business Group"
        verbose_name_plural = "Business Groups"
        ordering = ['sort']

    def __str__(self):
        return self.name


class Business(models.Model):
    """Business line — the core isolation unit for all operational resources"""
    name = models.CharField(
        max_length=128, unique=True, verbose_name="Name",
        help_text="业务线名称 / Business line display name"
    )
    code = models.SlugField(
        max_length=32, unique=True, verbose_name="Code",
        help_text="业务线代码 / Unique slug identifier"
    )
    group = models.ForeignKey(
        BusinessGroup, null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name="Group",
        help_text="所属业务群组（可选） / Optional parent business group"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Is Active",
        help_text="是否启用 / Whether this business is active"
    )
    db_alias = models.CharField(
        max_length=32, null=True, blank=True, verbose_name="DB Alias",
        help_text="Physical isolation extension point: Django DATABASES key. "
                  "Null means use 'default'. 物理隔离扩展点，默认 null 使用 default 库"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Created At"
    )

    class Meta:
        db_table = 'iam_business'
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        ordering = ['created_at']

    def __str__(self):
        return self.name


class DeployEnvironment(models.Model):
    """Deployment environment — globally defined, managed by Platform Admin

    Not owned by any Business. User access is explicitly granted via
    DeployEnvironmentPermission and does NOT inherit from role hierarchy.
    """
    name = models.CharField(
        max_length=64, verbose_name="Name",
        help_text="环境名称 / Display name, e.g. Production, Staging, Development"
    )
    code = models.CharField(
        max_length=16, unique=True, verbose_name="Code",
        help_text="环境代码 / Unique code, e.g. prod, staging, dev"
    )
    risk_level = models.IntegerField(
        default=0, verbose_name="Risk Level",
        help_text="风险等级 / 0=dev, 50=staging, 100=prod"
    )
    sort = models.IntegerField(
        default=0, verbose_name="Sort Order",
        help_text="排序 / Display order"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Is Active",
        help_text="是否启用 / Whether this environment is active"
    )

    class Meta:
        db_table = 'iam_deploy_environment'
        verbose_name = "Deploy Environment"
        verbose_name_plural = "Deploy Environments"
        ordering = ['sort']

    def __str__(self):
        return f"{self.name} ({self.code})"
