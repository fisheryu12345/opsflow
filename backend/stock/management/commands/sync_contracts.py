from django.core.management.base import BaseCommand, CommandError
from stock.scheduler.tasks_daily_close import sync_contract_list_from_tqsdk


class Command(BaseCommand):
    help = '使用 TqSDK 同步期货合约列表到数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新所有合约信息（即使没有变化）',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 开始执行合约同步任务...'))
        
        try:
            result = sync_contract_list_from_tqsdk()
            
            if result.get('error'):
                raise CommandError(f"同步失败: {result['error']}")
            
            self.stdout.write(self.style.SUCCESS('\n✅ 同步完成！'))
            self.stdout.write(f"   新增: {result.get('synced', 0)}")
            self.stdout.write(f"   更新: {result.get('updated', 0)}")
            self.stdout.write(f"   跳过: {result.get('skipped', 0)}")
            
        except Exception as e:
            raise CommandError(f"❌ 同步失败: {str(e)}")