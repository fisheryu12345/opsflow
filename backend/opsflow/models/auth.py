from django.db import models
from django.conf import settings


class ApiToken(models.Model):
    """外部 API Token — 用于第三方系统认证"""
    name = models.CharField(max_length=64, verbose_name='Token Name')
    token = models.CharField(max_length=64, unique=True, verbose_name='Token')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    allowed_actions = models.JSONField(default=list, blank=True, verbose_name='Allowed Actions')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name='Creator'
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expires At')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_api_token'
        verbose_name = 'API Token'

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"
