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
    """确保 datetime 是 naive 的（去除时区），兼容 USE_TZ=False + MySQL"""
    if dt is not None and hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _sync_next_run(plan):
    """从 APScheduler 同步 next_run_time 到 plan"""
    if opsflow_scheduler._started:
        job = opsflow_scheduler.scheduler.get_job(_job_id(plan.id))
        if job and job.next_run_time:
            plan.next_run_at = _naive(job.next_run_time)
            plan.save(update_fields=['next_run_at'])
            return

    # 调度器未启动时，手动计算 next_run_at
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
    """APScheduler 回调：创建 FlowExecution 并异步启动"""
    from opsflow.models import SchedulePlan, FlowExecution
    from opsflow.core.flow_engine import FlowEngine

    try:
        plan = SchedulePlan.objects.select_related(
            'template', 'created_by'
        ).get(id=plan_id)
    except SchedulePlan.DoesNotExist:
        logger.error(f"SchedulePlan {plan_id} 不存在，跳过执行")
        return

    if plan.template.is_draft:
        logger.warning(
            f"调度 '{plan.name}': 模板 '{plan.template.name}' 为草稿，跳过执行"
        )
        if plan.schedule_type == 'one_time':
            plan.status = SchedulePlan.Status.COMPLETED
            plan.is_active = False
            plan.save(update_fields=['status', 'is_active'])
        return

    try:
        execution = FlowExecution.objects.create(
            template=plan.template,
            status=FlowExecution.Status.PENDING,
            context={'pipeline_tree': plan.template.pipeline_tree},
            created_by=plan.created_by,
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

        logger.info(f"调度 '{plan.name}': 已创建执行 {execution.id}")
    except Exception as e:
        logger.exception(f"调度 '{plan.name}' 执行失败: {e}")
        if plan.max_retries > 0:
            from opsflow.tasks import retry_schedule_execution
            retry_schedule_execution.apply_async(
                args=[plan_id],
                countdown=plan.retry_delay,
                max_retries=plan.max_retries,
            )


class OpsflowScheduler:
    """APScheduler 封装，管理 SchedulePlan 的定时触发"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.scheduler.add_jobstore(DjangoJobStore(), 'default')
        self._started = False

    def start(self):
        if self._started:
            return
        self._register_existing_plans()
        self.scheduler.start()
        self._started = True
        logger.info("OpsflowScheduler started")

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
                logger.error(f"注册调度失败 plan={plan.id} name={plan.name}: {e}")

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
        logger.info(f"调度已注册: {plan.name} (id={plan.id})")

    def update_plan(self, plan):
        self.remove_plan(plan)
        self.add_plan(plan)

    def remove_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"调度已移除: {plan.name} (id={plan.id})")

    def pause_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)
            logger.info(f"调度已暂停: {plan.name} (id={plan.id})")

    def resume_plan(self, plan):
        job_id = self._job_id(plan.id)
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            _sync_next_run(plan)
            logger.info(f"调度已恢复: {plan.name} (id={plan.id})")

    def _build_trigger(self, plan):
        if plan.schedule_type == 'one_time':
            return DateTrigger(run_date=plan.scheduled_at, timezone=plan.timezone)
        return CronTrigger.from_crontab(plan.cron_expr, timezone=plan.timezone)

opsflow_scheduler = OpsflowScheduler()
