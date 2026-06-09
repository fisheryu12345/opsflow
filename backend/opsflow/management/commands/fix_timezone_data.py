"""
Timezone data migration — correct existing naive Asia/Shanghai datetimes for USE_TZ=True

Background:
  Current USE_TZ=False stores naive Asia/Shanghai datetimes in MySQL.
  After switching to USE_TZ=True, Django interprets naive values as UTC,
  shifting all timestamps +8h. This command subtracts 8 hours from all
  DateTimeField values so they represent the correct UTC instant.

Operation:
  Raw SQL UPDATEs bypass Django's timezone handling, so this works regardless
  of the current USE_TZ setting. Run once BEFORE deploying USE_TZ=True.

Usage:
    python manage.py fix_timezone_data          # dry-run (default)
    python manage.py fix_timezone_data --apply   # actually update data
    python manage.py fix_timezone_data --apply --table opsflow_flowexecution  # single table
"""

from collections import OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


# Map: table_name → [column_name, ...]
# All columns are DateTimeField / DateField that may contain naive values.
TABLE_COLUMNS = OrderedDict({
    # ── opsflow ────────────────────────────────────────────────────────────
    "opsflow_flowexecution": ["started_at", "ended_at", "created_at"],
    "opsflow_nodeexecution": ["entered_at", "exited_at", "created_at"],
    "opsflow_executionlog": ["created_at"],
    "opsflow_scheduleplan": ["scheduled_at", "last_run_at", "next_run_at", "created_at", "updated_at"],
    "opsflow_webhookevent": ["created_at"],
    "opsflow_opsproject": ["created_at", "updated_at", "joined_at"],
    "opsflow_pluginmeta": ["created_at", "updated_at"],
    "opsflow_pluginexecution": ["created_at", "updated_at"],
    "opsflow_knowledgedoc": ["created_at"],
    "opsflow_envvariable": ["created_at", "updated_at"],
    "opsflow_authtoken": ["expires_at", "created_at"],
    "opsflow_auditlog": ["created_at"],

    # ── opsagent ───────────────────────────────────────────────────────────
    "opsagent_session": ["started_at", "ended_at", "timestamp"],
    "opsagent_environmentcontext": ["execution_started", "execution_completed"],
    "opsagent_apikey": ["expires_at", "created_at", "updated_at"],

    # ── iam ────────────────────────────────────────────────────────────────
    "iam_permissionrequest": ["reviewed_at"],

    # ── itsm ───────────────────────────────────────────────────────────────
    "itsm_ticket": ["create_datetime", "update_datetime"],
    "itsm_incident": ["sla_deadline", "resolved_at", "planned_start", "planned_end", "fulfilled_at"],
    "itsm_delegation": ["date_from", "date_to"],
    "itsm_sla": ["deadline", "reply_deadline"],

    # ── job_platform ───────────────────────────────────────────────────────
    "job_platform_taskexecution": ["started_at", "finished_at"],
    "job_platform_nodeexecution": ["start_time", "end_time"],
    "job_platform_approvalrecord": ["approved_at"],
    "job_platform_cronjob": ["start_date", "end_date", "last_run_at", "next_run_at"],
    "job_platform_scheduledtask": ["scheduled_time", "actual_time"],

    # ── monitor ────────────────────────────────────────────────────────────
    "monitor_strategy": ["create_time", "update_time"],
    "monitor_alert": ["time", "anomaly_time", "create_time", "fired_at", "resolved_at", "acknowledged_at", "next_escalate_at"],
    "monitor_notification": ["date_from", "date_to"],

    # ── open_api ───────────────────────────────────────────────────────────
    "open_api_app": ["expire_at"],
    "open_api_apptoken": ["last_used_at", "expire_at"],

    # ── integration ────────────────────────────────────────────────────────
    "integration_credential": ["expire_at", "last_used_at"],
    "integration_connector": ["last_health_check"],

    # ── dvadmin / system (CoreModel derivatives) ───────────────────────────
    "dvadmin_system_operationlog": ["create_datetime", "update_datetime"],
    "dvadmin_system_loginlog": ["create_datetime", "update_datetime"],
})


class Command(BaseCommand):
    help = "Fix existing naive datetime data for USE_TZ=True migration"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually update data (default: dry-run)")
        parser.add_argument("--table", type=str, help="Only process a single table")

    def handle(self, *args, **options):
        dry_run = not options["apply"]
        only_table = options.get("table")

        tables = TABLE_COLUMNS
        if only_table:
            if only_table not in tables:
                raise CommandError(f"Unknown table '{only_table}'. Known: {', '.join(tables.keys())}")
            tables = {only_table: tables[only_table]}

        with connection.cursor() as cursor:
            for table, columns in tables.items():
                for col in columns:
                    sql = (
                        f"UPDATE {table} "
                        f"SET {col} = {col} - INTERVAL 8 HOUR "
                        f"WHERE {col} IS NOT NULL"
                    )
                    if dry_run:
                        # Estimate affected row count
                        count_sql = f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL"
                        cursor.execute(count_sql)
                        count = cursor.fetchone()[0]
                        self.stdout.write(f"[DRY-RUN] {table}.{col}: {count} rows would be updated")
                    else:
                        cursor.execute(sql)
                        affected = cursor.rowcount
                        self.stdout.write(f"[APPLIED] {table}.{col}: {affected} rows updated")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDry-run complete. Run with --apply to execute."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\nTimezone data migration complete."))
