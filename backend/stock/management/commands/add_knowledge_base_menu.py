"""
添加知识库菜单的管理命令
"""
from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = '添加知识库菜单项'

    def handle(self, *args, **options):
        # 查找父菜单"系统管理"
        try:
            parent_menu = Menu.objects.get(name='系统管理')
        except Menu.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('未找到父菜单"系统管理"，请先确保基础菜单已初始化')
            )
            return

        # 检查是否已存在
        if Menu.objects.filter(name='知识库').exists():
            self.stdout.write(
                self.style.WARNING('知识库菜单已存在，跳过创建')
            )
            return

        # 创建知识库菜单
        menu = Menu.objects.create(
            name='知识库',
            icon='ele-Notebook',
            sort=99,
            is_link=False,
            is_catalog=False,
            web_path='/knowledge-base',
            component='apps/knowledgebase/index',
            component_name='knowledge-base',
            status=True,
            cache=False,
            visible=True,
            parent=parent_menu
        )

        self.stdout.write(
            self.style.SUCCESS(f'成功创建知识库菜单，ID: {menu.id}')
        )
