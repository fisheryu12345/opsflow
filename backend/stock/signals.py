"""
Django 信号 — 用户注册时自动创建 TradingAccount
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from decimal import Decimal
from stock.models import TradingAccount


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def auto_create_trading_account(sender, instance, created, **kwargs):
    """
    确保每个用户都有至少一个交易账户。
    新用户创建时自动创建；老用户缺失时自动补建。
    """
    if created:
        TradingAccount.objects.create(
            user=instance,
            name=f"{instance.username}",
            initial_balance=Decimal('1000000.00'),
            current_equity=Decimal('1000000.00'),
            is_active=True,
        )
    else:
        TradingAccount.objects.get_or_create(
            user=instance,
            defaults={
                'name': f"{instance.username}",
                'initial_balance': Decimal('1000000.00'),
                'current_equity': Decimal('1000000.00'),
                'is_active': True,
            }
        )
