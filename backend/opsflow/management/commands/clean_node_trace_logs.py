"""清理 N 天前的节点轨迹日志文件

用法:
  python manage.py clean_node_trace_logs                          # 默认保留 30 天
  python manage.py clean_node_trace_logs --days 7                 # 保留 7 天
  python manage.py clean_node_trace_logs --days 90 --dry-run      # 预览将要清理的目录
"""

import os
import shutil
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from opsflow.core.trace_logger import TRACE_LOG_ROOT


class Command(BaseCommand):
    help = "清理 N 天前的节点轨迹日志文件"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=30,
            help="保留天数（默认 30 天，之前的数据将被清理）",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="仅预览将要清理的目录，不实际删除",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        threshold = timezone.now() - timedelta(days=days)

        log_root = os.path.join(settings.LOG_DIR, TRACE_LOG_ROOT, "tasks")
        if not os.path.exists(log_root):
            self.stdout.write(f"日志目录不存在: {log_root}")
            return

        total_size = 0
        count = 0

        for exec_dir in os.listdir(log_root):
            dir_path = os.path.join(log_root, exec_dir)
            if not os.path.isdir(dir_path):
                continue

            mtime = datetime.fromtimestamp(os.path.getmtime(dir_path))
            if mtime >= threshold:
                continue

            # 计算目录大小
            dir_size = 0
            for dirpath, _, filenames in os.walk(dir_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        dir_size += os.path.getsize(fp)
                    except OSError:
                        pass

            total_size += dir_size
            count += 1

            if dry_run:
                self.stdout.write(
                    f"  [{exec_dir}] {_format_size(dir_size)} "
                    f"(last modified: {mtime.date()})"
                )
            else:
                try:
                    shutil.rmtree(dir_path)
                except OSError as e:
                    self.stderr.write(f"  清理失败 {exec_dir}: {e}")
                    continue

        if dry_run:
            self.stdout.write(
                f"\n预览完成: 将清理 {count} 个执行日志目录 "
                f"(共 {_format_size(total_size)})"
            )
        else:
            self.stdout.write(
                f"清理完成: 已清理 {count} 个执行日志目录 "
                f"(释放 {_format_size(total_size)})"
            )


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为可读字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
