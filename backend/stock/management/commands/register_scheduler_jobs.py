"""
管理命令：注册 APScheduler 定时任务到数据库

在开发环境中，调度器不会自动启动（仅生产服务器 172.25.21.216 上启动）。
此命令将任务定义写入 django_apscheduler 表，使其在 Django admin 中可见。

用法：
    python manage.py register_scheduler_jobs
    python manage.py register_scheduler_jobs --type report  # 仅注册报告任务
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '注册 APScheduler 定时任务到数据库，供 Django admin 查看'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'report'],
            default='all',
            help='要注册的任务类型: all=全部, report=仅绩效报告任务',
        )

    def handle(self, *args, **options):
        job_type = options['type']

        if job_type == 'all':
            # 导入 scheduler 会触发模块级代码，自动注册所有可用的任务
            from stock.scheduler.scheduler import scheduler
            job_ids = [job.id for job in scheduler.get_jobs()]
            self.stdout.write(self.style.SUCCESS(
                f'调度器已加载 {len(job_ids)} 个定时任务: {", ".join(job_ids)}'
            ))
        else:
            # --type report: 仅注册绩效报告任务
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore

            scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
            scheduler.add_jobstore(DjangoJobStore(), 'default')
            registered = []

            try:
                from stock.scheduler.tasks_report import (
                    job_monthly_report,
                    job_quarterly_report,
                    job_annual_report,
                )
            except ImportError as e:
                self.stdout.write(self.style.WARNING(
                    f'跳过报告任务注册（依赖缺失: {e}）'
                ))
            else:
                scheduler.add_job(job_monthly_report, 'cron', day=1, hour=9, minute=30,
                                  id='job_monthly_report', name='月度绩效报告',
                                  misfire_grace_time=3600, replace_existing=True,
                                  max_instances=1, coalesce=True)
                registered.append('job_monthly_report')
                scheduler.add_job(job_quarterly_report, 'cron', month='1,4,7,10', day=1,
                                  hour=9, minute=30, id='job_quarterly_report',
                                  name='季度绩效报告', misfire_grace_time=3600,
                                  replace_existing=True, max_instances=1, coalesce=True)
                registered.append('job_quarterly_report')
                scheduler.add_job(job_annual_report, 'cron', month=1, day=1,
                                  hour=10, minute=0, id='job_annual_report',
                                  name='年度绩效报告', misfire_grace_time=7200,
                                  replace_existing=True, max_instances=1, coalesce=True)
                registered.append('job_annual_report')

            self.stdout.write(self.style.SUCCESS(
                f'成功注册 {len(registered)} 个定时任务: {", ".join(registered)}'
            ))

        self.stdout.write(self.style.WARNING(
            '提示: 这些任务仅在 Django admin 可见。'
            '实际执行需要调度器在 172.25.21.216 上运行。'
        ))
