"""Management command — 修复 MySQL JSON_SET 双层编码导致的 node_status 值错误

执行 JSON_SET 时未使用 CAST(%s AS JSON)，导致值被存储为带引号的
"completed" 而非纯字符串 completed。前端 nodeStatuses 比较时
"completed" 匹配不到，头部统计全部为 0。

修复方法：
- `"completed"` → `completed`（对所有已存在的执行记录）
"""
import json
import logging

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

_SQL_SCAN = """
SELECT id, node_status FROM ops_flow_execution
WHERE node_status IS NOT NULL AND node_status != '{}'
"""


def needs_fix(val):
    """检查值是否带双层引号：字符串以 " 开头和结尾且长度 > 2"""
    return isinstance(val, str) and val.startswith('"') and val.endswith('"') and len(val) >= 2


def fix_value(val):
    """去掉外层引号：'"completed"' → 'completed'"""
    if needs_fix(val):
        return val[1:-1]
    return val


class Command(BaseCommand):
    help = "修复 node_status JSON 字段的双层编码问题"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(_SQL_SCAN)
            rows = cursor.fetchall()

        fixed_count = 0
        for exec_id, raw_status in rows:
            if isinstance(raw_status, str):
                try:
                    status = json.loads(raw_status)
                except (json.JSONDecodeError, TypeError):
                    continue
            elif isinstance(raw_status, dict):
                status = raw_status
            else:
                continue

            # 检查是否有需要修复的值
            new_status = {}
            need_fix = False
            for k, v in status.items():
                fixed = fix_value(v)
                new_status[k] = fixed
                if fixed != v:
                    need_fix = True

            if need_fix:
                # 直接 ORM 更新，让 JSONField 处理正确的序列化
                from opsflow.models import FlowExecution
                FlowExecution.objects.filter(id=exec_id).update(node_status=new_status)
                fixed_count += 1
                self.stdout.write(f"  Fixed execution #{exec_id}: { {k: v for k, v in status.items() if needs_fix(v)} }")

        self.stdout.write(self.style.SUCCESS(f"Done — fixed {fixed_count} execution(s)"))
