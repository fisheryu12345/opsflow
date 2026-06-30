# -*- coding: utf-8 -*-
"""APScheduler job registration for identity sync

Registers a cron job for each enabled LDAP/AD ConnectorInstance
that has a sync_cron configured.

Triggered at Django startup via AppConfig.ready().
"""

import logging

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def register_sync_jobs(scheduler):
    """Register identity sync cron jobs for all enabled LDAP/AD instances

    Called from IamConfig.ready() after the APScheduler has started.
    Each instance with a valid 'sync_cron' config gets a recurring job.
    """
    try:
        from integration.models.connector import ConnectorInstance
    except ImportError:
        logger.warning("Integration app not available, skipping sync job registration")
        return

    instances = ConnectorInstance.objects.filter(
        definition__code='ldap',
        is_active=True,
    )

    registered = 0
    for inst in instances:
        cron_expr = (inst.config or {}).get('sync_cron', '').strip()
        if not cron_expr:
            continue

        try:
            # Validate cron expression by parsing it
            CronTrigger.from_crontab(cron_expr)

            job_id = f'identity_sync_{inst.id}'

            # Remove existing job with same ID (in case of reload)
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            scheduler.add_job(
                _run_sync_task,
                trigger=CronTrigger.from_crontab(cron_expr),
                args=[inst.id],
                id=job_id,
                name=f'Sync {inst.name} ({cron_expr})',
                replace_existing=True,
                misfire_grace_time=300,
            )
            registered += 1
            logger.info(
                "Registered sync job: %s (%s) cron=%s",
                inst.name, job_id, cron_expr,
            )
        except Exception as e:
            logger.warning(
                "Failed to register sync job for %s: %s", inst.name, e
            )

    logger.info("Registered %d identity sync cron jobs", registered)


def _run_sync_task(instance_id):
    """Execute sync for a given instance (called by APScheduler)"""
    import django
    django.db.close_old_connections()

    try:
        from integration.models.connector import ConnectorInstance
        from iam.sync.provider import LDAPSyncProvider
        from integration.models.integration_log import IntegrationLog

        inst = ConnectorInstance.objects.get(id=instance_id)
        logger.info("Scheduled sync starting for %s", inst.name)

        log_entry = IntegrationLog.objects.create(
            instance=inst,
            definition_code='ldap',
            action='identity_sync',
            status='success',
        )

        provider = LDAPSyncProvider(inst)
        result = provider.sync_full()

        log_entry.response_data = {
            'dept_added': result.stats.dept_added,
            'dept_updated': result.stats.dept_updated,
            'dept_disabled': result.stats.dept_disabled,
            'user_added': result.stats.user_added,
            'user_updated': result.stats.user_updated,
            'user_disabled': result.stats.user_disabled,
            'errors': result.errors,
        }
        if not result.success:
            log_entry.status = 'failed'
            log_entry.error_message = result.error
        log_entry.save(update_fields=['response_data', 'status', 'error_message'])

        logger.info("Scheduled sync complete for %s: %s", inst.name, result.stats)

    except ConnectorInstance.DoesNotExist:
        logger.warning("Sync job skipped: instance %s not found", instance_id)
    except Exception as e:
        logger.exception("Scheduled sync failed for instance %s: %s", instance_id, e)
