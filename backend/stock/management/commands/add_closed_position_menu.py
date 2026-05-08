"""
添加平仓记录菜单的管理命令
"""
from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = '添加平仓记录菜单项'

    def handle(self, *args, **options):
        # 查找父菜单"期货交易"
        try:
            parent_menu = Menu.objects.get(name='期货交易')
        except Menu.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('未找到父菜单"期货交易"，请先确保业务菜单已初始化')
            )
            return

        # 检查是否已存在平仓记录菜单
        if Menu.objects.filter(name='平仓记录').exists():
            self.stdout.write(
                self.style.WARNING('平仓记录菜单已存在，跳过创建')
            )
            return

        # 创建平仓记录菜单
        closed_position_menu = Menu.objects.create(
            name='平仓记录',
            icon='ele-Document',
            sort=3,  # 在持仓列表之后
            is_link=False,
            is_catalog=False,
            web_path='/closed-position',
            component='apps/closed-position/index',
            component_name='closed-position',
            status=True,
            cache=False,
            visible=True,
            parent=parent_menu
        )

        self.stdout.write(
            self.style.SUCCESS(f'成功创建平仓记录菜单，ID: {closed_position_menu.id}')
        )