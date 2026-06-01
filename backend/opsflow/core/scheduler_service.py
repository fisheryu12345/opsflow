import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

JOB_ID_PREFIX = 'opsflow_schedule_plan_'


def _job_id(plan_id: int) -> str:
    return f'{JOB_ID_PREFIX}{plan_id}'


def _naive(dt):
    """Ensure datetime is naive (strip timezone), compatible with USE_TZ=False + MySQL"""
    if dt is not None and hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _sync_next_run(plan):
    """Sync next_run_time from APScheduler to plan"""
    if opsflow_scheduler._started:
        job = opsflow_scheduler.scheduler.get_job(_job_id(plan.id))
        if job and job.next_run_time:
            plan.next_run_at = _naive(job.next_run_time)
            plan.save(update_fields=['next_run_at'])
            return

    # Manually calculate next_run_at when scheduler is not started
    if plan.schedule_type == 'one_time' and plan.scheduled_at:
        plan.next_run_at = _naive(plan.scheduled_at)
    elif plan.schedule_type == 'cron' and plan.cron_expr:
        from apscheduler.triggers.cron import CronTrigger
        from django.utils import timezone
        try:
            trigger = CronTrigger.from_crontab(plan.cron_expr, timezone=plan.timezone)
            plan.next_run_at = _naive(trigger.get_next_fire_time(
                prev_fire_time=None, now=timezone.localtime()
            ))
        except Exception:
            plan.next_run_at = None
    plan.save(update_fields=['next_run_at'])


def _execute_plan(plan_id: int):
    """APScheduler callback: create FlowExecution and start asynchronously"""
    from opsflow.models import SchedulePlan, FlowExecution
    from opsflow.core.flow_engine import FlowEngine

    try:
        plan = SchedulePlan.objects.select_related(
            'template', 'created_by'
        ).get(id=plan_id)
    except SchedulePlan.DoesNotExist:
        logger.error(f"SchedulePlan {plan_id} does not exist, skipping execution")
        return

    if plan.template.is_draft:
        logger.warning(
            f"Schedule '{plan.name}': template '{plan.template.name}' is draft, skipping execution"
        )
        if plan.schedule_type == 'one_time':
            plan.status = SchedulePlan.Status.COMPLETED
            plan.is_active = False
            plan.save(update_fields=['status', 'is_active'])
        return

    try:
        # Use snapshot from schedule creation (isolate template changes from schedule execution)
        ss = plan.template_snapshot
        if ss and 'pipeline_tree' in ss:
            # Structured format (new): {'pipeline_tree', 'target_hosts', 'global_vars'}
            execution = FlowExecution.objects.create(
                template=plan.template,
                status=FlowExecution.Status.PENDING,
                template_snapshot={
                    'pipeline_tree': ss['pipeline_tree'],
                    'target_hosts': ss.get('target_hosts', []),
                    'global_vars': ss.get('global_vars', {}),
                },
                created_by=plan.created_by,
                schedule_plan=plan,
            )
        else:
            # Old format: plan.template_snapshot itself is a pipeline_tree
            execution = FlowExecution.objects.create(
                template=plan.template,
                status=FlowExecution.Status.PENDING,
                template_snapshot={
                    'pipeline_tree': ss or plan.template.pipeline_tree,
                    'target_hosts': plan.template.target_hosts or [],
                    'global_vars': plan.template.global_vars or {},
                },
                created_by=plan.created_by,
                schedule_plan=plan,
            )
        engine = FlowEngine(execution)
        engine.start(sync=False)

        plan.last_run_at = timezone.now()
        plan.total_run_count += 1

        if plan.schedule_type == 'one_time':
            plan.status = SchedulePlan.Status.COMPLETED
            plan.is_active = False

        _sync_next_run(plan)
        plan.save()

        logger.info(f"Schedule '{plan.name}': created execution {execution.id}")
    except Exception as e:
        logger.exception(f"Schedule '{plan.name}' execution failed: {e}")
        if plan.max_retries > 0:
            from opsflow.tasks import retry_schedule_execution
            retry_schedule_execution.apply_async(
                args=[plan_id, plan.max_retries],
                countdown=plan.retry_delay,
            )


class OpsflowScheduler:
    """APScheduler wrapper for managing SchedulePlan timed triggers"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.scheduler.add_jobstore(DjangoJobStore(), 'default')
        self._started = False

    def start(self):
        if self._started:
            return
        self._register_existing_plans()
        self._register_timeout_check()
        self.scheduler.start()
        self._started = True
        logger.info("OpsflowScheduler started")

    def _register_timeout_check(self):
        """注册节点超时检查定时任务（每 10 秒扫描 Redis 到期节点）"""
        from apscheduler.triggers.interval import IntervalTrigger
        from opsflow.core.node_timeout_strategy import dispatch_timeout_nodes, TIMEOUT_CHECK_INTERVAL

        self.scheduler.add_job(
            dispatch_timeout_nodes,
            trigger=IntervalTrigger(seconds=TIMEOUT_CHECK_INTERVAL),
            id='opsflow_timeout_check',
            name='节点超时检查',
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=30,
        )
        logger.info("Timeout check registered (interval=%ds)", TIMEOUT_CHECK_INTERVAL)

    def shutdown(self, wait=False):
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("OpsflowScheduler shut down")

    def _register_existing_plans(self):
        from opsflow.models import SchedulePlan
        active_plans = SchedulePlan.objects.filter(
            is_active=True, status=SchedulePlan.Status.ACTIVE
        )
        for plan in active_plans:
            try:
                self.add_plan(plan)
            except Exception as e:
                logger.error(f"Failed to register schedule plan={plan.id} name={plan.name}: {e}")

    def _job_id(self, plan_id):
        return _job_id(plan_id)

    def add_plan(self, plan):
        job_id = self._job_id(plan.id)
        trigger = self._build_trigger(plan)
        self.scheduler.add_job(
            _execute_plan,
            trigger=trigger,
            id=job_id,
            name=plan.name,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=900,
            kwargs={'plan_id': plan.id},
        )
        _sync_next_run(plan)
        logger.info(f"Schedule registered: {plan.name} (id={plan.id})")

    def update_plan(self, plan):
        self.remove_plan(plan)
        self.add_plan(plan)

    def remove_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Schedule removed: {plan.name} (id={plan.id})")

    def pause_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)
            logger.info(f"Schedule paused: {plan.name} (id={plan.id})")

    def resume_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            _sync_next_run(plan)
            logger.info(f"Schedule resumed: {plan.name} (id={plan.id})")

    def _build_trigger(self, plan):
        if plan.schedule_type == 'one_time':
            return DateTrigger(run_date=plan.scheduled_at, timezone=plan.timezone)
        return CronTrigger.from_crontab(plan.cron_expr, timezone=plan.timezone)

opsflow_scheduler = OpsflowScheduler()
