"""
Management command to add the Trading Account management menu entry.
Run: python manage.py add_trading_account_menu
"""
from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = '添加交易账户管理菜单'

    def handle(self, *args, **options):
        parent = Menu.objects.get(id=16)

        # Check if already exists
        existing = Menu.objects.filter(parent=parent, name='交易账户').first() or \
                   Menu.objects.filter(parent=parent, web_path='/trading-account').first()
        if existing:
            self.stdout.write(f'菜单已存在: {existing.name}')
            return

        menu = Menu.objects.create(
            parent=parent,
            name='交易账户',
            icon='el-icon-setting',
            sort=7,
            is_catalog=False,
            web_path='/trading-account',
            component='apps/trading-account/index',
            component_name='TradingAccount',
            status=True,
            cache=False,
            visible=True,
            is_link=False,
            is_iframe=False,
            is_affix=False,
        )
        self.stdout.write(self.style.SUCCESS(f'菜单创建成功: {menu.name} (ID={menu.id})'))
