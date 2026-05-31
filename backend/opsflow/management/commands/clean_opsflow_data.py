"""清理过期 OpsFlow 数据 — DB 记录 + 日志文件

清理策略:
  1. FlowExecution (status=completed/failed/cancelled, ended_at > days)
     → 级联删除关联 NodeExecutionTrace + OpsLog
  2. SchedulePlan (status=completed/expired, updated_at > days)
  3. TemplateVersion (created_at > days, 保留最新 3 个版本)
  4. 节点日志文件 (委托给 clean_node_trace_logs)

用法:
  python manage.py clean_opsflow_data                     # 默认保留 90 天
  python manage.py clean_opsflow_data --days 30            # 保留 30 天
  python manage.py clean_opsflow_data --dry-run            # 预览
  python manage.py clean_opsflow_data --model executions   # 仅清理执行记录
"""

import os
import shutil
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q


class Command(BaseCommand):
    help = "清理过期 OpsFlow 数据"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90, help="保留天数（默认90）")
        parser.add_argument("--dry-run", action="store_true", help="仅预览不删除")
        parser.add_argument("--model", choices=["executions", "schedules", "versions",
                                                "trace_logs", "all"],
                            default="all", help="要清理的模型类型")
        parser.add_argument("--batch-size", type=int, default=100,
                            help="每批删除数量（默认100）")

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        model = options["model"]
        batch_size = options["batch_size"]
        threshold = timezone.now() - timedelta(days=days)

        self.stdout.write(f"[{'DRY-RUN' if dry_run else 'EXEC'}] 清理 {days} 天前的数据")
        self.stdout.write(f"[{'DRY-RUN' if dry_run else 'EXEC'}] 截止时间: {threshold.isoformat()}")

        total_deleted = 0

        if model in ("executions", "all"):
            total_deleted += self._clean_executions(threshold, batch_size, dry_run)

        if model in ("schedules", "all"):
            total_deleted += self._clean_schedules(threshold, batch_size, dry_run)

        if model in ("versions", "all"):
            total_deleted += self._clean_versions(threshold, batch_size, dry_run)

        if model in ("trace_logs", "all"):
            total_deleted += self._clean_trace_logs(days, dry_run)

        self.stdout.write(self.style.SUCCESS(f"清理完成，共处理 {total_deleted} 条记录"))

    def _clean_executions(self, threshold, batch_size, dry_run):
        """清理已完结的执行记录"""
        from opsflow.models import FlowExecution, NodeExecutionTrace, OpsLog

        qs = FlowExecution.objects.filter(
            Q(status="completed") | Q(status="failed") | Q(status="cancelled"),
            ended_at__lt=threshold,
        )
        total = qs.count()
        self.stdout.write(f"待清理执行: {total} 条")

        if dry_run:
            return total

        deleted = 0
        while True:
            batch = list(qs.values_list("id", flat=True)[:batch_size])
            if not batch:
                break

            # 级联删除关联数据
            NodeExecutionTrace.objects.filter(execution_id__in=batch).delete()
            OpsLog.objects.filter(execution_id__in=batch).delete()

            # 删除执行本身
            FlowExecution.objects.filter(id__in=batch).delete()
            deleted += len(batch)
            self.stdout.write(f"  已清理 {deleted}/{total}")

        return deleted

    def _clean_schedules(self, threshold, batch_size, dry_run):
        """清理已完成的调度计划"""
        from opsflow.models import SchedulePlan

        qs = SchedulePlan.objects.filter(
            Q(status=SchedulePlan.Status.COMPLETED) |
            Q(status=SchedulePlan.Status.EXPIRED),
            updated_at__lt=threshold,
        )
        total = qs.count()
        self.stdout.write(f"待清理调度: {total} 条")

        if dry_run:
            return total

        deleted = 0
        while True:
            batch = list(qs.values_list("id", flat=True)[:batch_size])
            if not batch:
                break
            SchedulePlan.objects.filter(id__in=batch).delete()
            deleted += len(batch)

        return deleted

    def _clean_versions(self, threshold, batch_size, dry_run):
        """清理过期的模板版本，保留每个模板最新 3 个版本"""
        from opsflow.models import TemplateVersion

        total = 0
        template_ids = TemplateVersion.objects.values_list(
            "template_id", flat=True
        ).distinct()

        for tid in template_ids:
            # 对每个模板，保留最新 3 个版本
            keep = list(
                TemplateVersion.objects.filter(template_id=tid)
                .order_by("-version")
                .values_list("id", flat=True)[:3]
            )
            old = TemplateVersion.objects.filter(
                template_id=tid,
                created_at__lt=threshold,
            ).exclude(id__in=keep)

            count = old.count()
            if count:
                total += count
                if not dry_run:
                    old.delete()
                    self.stdout.write(f"  模板 {tid}: 清理 {count} 个旧版本")

        self.stdout.write(f"待清理版本: {total} 条")
        return total

    def _clean_trace_logs(self, days, dry_run):
        """清理节点日志文件 — 委托给 clean_node_trace_logs"""
        from opsflow.management.commands.clean_node_trace_logs import Command as CleanLogsCmd

        cmd = CleanLogsCmd()
        cmd.handle(days=days, dry_run=dry_run)
        return 0
