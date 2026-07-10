# -*- coding: utf-8 -*-
"""Trigger matching, execution, and action dispatch.

Execution flow:
  Ticket/Flow event → TriggerMatcher.match() → TriggerExecutor.enqueue()
  → APScheduler (every 10s) → TriggerExecutor.process_pending()
  → ActionRunner.run() per action → TriggerExecution.status updated
"""

import json
import logging
import re
from datetime import timedelta

import requests
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# TemplateResolver — resolve ${variable} placeholders against ticket context
# =============================================================================

class TemplateResolver:
    """Resolve ${variable} templates in action config strings."""

    @staticmethod
    def resolve(template: str, ticket, current_state_name: str = '') -> str:
        if not template:
            return template
        # Resolve starter/processor names safely
        starter_name = ''
        if ticket.creator_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                u = User.objects.only('username').get(id=ticket.creator_id)
                starter_name = u.username
            except Exception:
                starter_name = str(ticket.creator_id)
        processor_name = ''
        assignee = (ticket.meta or {}).get('assignee', {})
        if assignee and assignee.get('name'):
            processor_name = assignee.get('name', '')
        elif assignee and assignee.get('username'):
            processor_name = assignee.get('username', '')

        replacements = {
            'ticket_id': str(ticket.id),
            'ticket_title': ticket.title or '',
            'priority': ticket.priority or '',
            'current_state': current_state_name or '',
            'starter_name': starter_name,
            'processor_name': processor_name,
        }
        for key, val in replacements.items():
            template = template.replace(f'${{{key}}}', str(val))
        # Resolve ${field.xxx} from form_data
        for match in re.finditer(r'\$\{field\.(\w+)\}', template):
            field_val = ticket.meta.get('form_data', {}).get(match.group(1), '')
            template = template.replace(match.group(0), str(field_val))
        return template


# =============================================================================
# ConditionEvaluator — evaluate field-level condition expressions
# =============================================================================

class ConditionEvaluator:
    """Evaluate condition expression against ticket form data.

    Condition format (matching frontend ConditionStruct):
        {"logic": "AND", "rules": [{"source": "ticket", "field": "...", "op": "==", "value": "..."}]}
    """

    @staticmethod
    def evaluate(condition: dict, ticket) -> bool:
        if not condition or not condition.get('rules'):
            return True
        logic = condition.get('logic', 'AND')
        results = []
        for rule in condition['rules']:
            field_value = ConditionEvaluator._resolve_value(
                ticket, rule.get('source'), rule['field']
            )
            results.append(ConditionEvaluator._apply_op(
                field_value, rule['op'], rule['value']
            ))
        return all(results) if logic == 'AND' else any(results)

    @staticmethod
    def _resolve_value(ticket, source, field):
        """Resolve field value from ticket meta or pipeline node outputs."""
        if source == 'ticket' or not source:
            return ticket.meta.get('form_data', {}).get(field)
        # Node-scoped fields: resolve from pipeline Data context
        if ticket.pipeline_id:
            try:
                from pipeline.eri.runtime import BambooDjangoRuntime
                runtime = BambooDjangoRuntime()
                pipeline_data = runtime.get_data(ticket.pipeline_id)
                return pipeline_data.get(f'{source}_{field}')
            except Exception:
                pass
        return None

    @staticmethod
    def _apply_op(left, op, right):
        """Apply comparison operator. Coerce types for numeric comparison."""
        # Normalize None to empty string for consistent comparison
        if left is None:
            left = ''
        try:
            if op in ('>', '<', '>=', '<=') and left != '':
                left = float(left)
                right = float(right)
            ops = {
                '==': lambda a, b: str(a) == str(b),
                '!=': lambda a, b: str(a) != str(b),
                '>': lambda a, b: a > b,
                '<': lambda a, b: a < b,
                '>=': lambda a, b: a >= b,
                '<=': lambda a, b: a <= b,
                'in': lambda a, b: str(a) in str(b).split(','),
                'notin': lambda a, b: str(a) not in str(b).split(','),
            }
            if op in ops:
                return ops[op](left, right)
            return True
        except (ValueError, TypeError, AttributeError):
            return False


# =============================================================================
# TriggerMatcher — find triggers matching an event
# =============================================================================

class TriggerMatcher:
    """Match active triggers against a ticket event context."""

    @staticmethod
    def match(ticket, event_type, state_id=None) -> list:
        from itsm.models import Trigger, State

        qs = Trigger.objects.filter(is_active=True, event_type=event_type)

        # Workflow filter: always scoped to ticket's workflow
        workflow = ticket.workflow_version.workflow if ticket.workflow_version else None
        if workflow:
            qs = qs.filter(workflow=workflow)
        else:
            return []

        # Priority filter: specified priority OR blank
        qs = qs.filter(
            Q(priority='') | Q(priority=ticket.priority)
        )

        # State filter (ENTER/LEAVE only): must match the triggering state
        if state_id:
            qs = qs.filter(states__id=state_id)

        # Evaluate field-level conditions (skip for FLOW_START — form_data is empty)
        matched = []
        for trigger in qs:
            if event_type != 'FLOW_START' and trigger.condition:
                if not ConditionEvaluator.evaluate(trigger.condition, ticket):
                    continue
            matched.append(trigger)
        return matched


# =============================================================================
# ActionRunner — dispatch to type-specific action handlers
# =============================================================================

class ActionRunner:
    """Dispatch action execution to type-specific runners."""

    @staticmethod
    def run(action, ticket, current_state_name='') -> dict:
        try:
            if action.action_type == 'NOTIFY':
                return NotifyRunner.run(action.config, ticket, current_state_name)
            elif action.action_type == 'WEBHOOK':
                return WebhookRunner.run(action.config, ticket, current_state_name)
            elif action.action_type == 'OPSFLOW':
                return OpsflowRunner.run(action.config, ticket)
            elif action.action_type == 'MODIFY_FIELD':
                return ModifyFieldRunner.run(action.config, ticket, current_state_name)
            return {'status': 'FAILED', 'error': f'Unknown action type: {action.action_type}'}
        except Exception as e:
            logger.warning(f'ActionRunner error for action #{action.id}: {e}')
            return {
                'action_id': action.id,
                'action_type': action.action_type,
                'status': 'FAILED',
                'error': str(e),
            }


class NotifyRunner:
    """Send notification via NotificationService."""

    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        from itsm.services.notifications import NotificationService

        title = TemplateResolver.resolve(config.get('title_tpl', ''), ticket, current_state_name)
        body = TemplateResolver.resolve(config.get('body_tpl', ''), ticket, current_state_name)
        receivers = config.get('receivers', [])
        channels = config.get('channels', ['site'])
        custom_users = config.get('custom_users', [])

        # Resolve receiver roles to actual user IDs
        user_ids = set()
        if 'processor' in receivers and ticket.processor_id:
            user_ids.add(ticket.processor_id)
        if 'starter' in receivers and ticket.creator_id:
            user_ids.add(ticket.creator_id)
        if 'leader' in receivers:
            try:
                from itsm.services.sla_time import resolve_leader
                # resolve_leader takes a username string, returns a username string
                processor_username = (ticket.meta or {}).get('assignee', {}).get('username', '')
                leader_username = resolve_leader(processor_username) if processor_username else None
                if leader_username:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    leader_user = User.objects.filter(username=leader_username).only('id').first()
                    if leader_user:
                        user_ids.add(leader_user.id)
            except Exception:
                pass
        for uid in custom_users:
            user_ids.add(int(uid) if isinstance(uid, str) else uid)

        if user_ids:
            NotificationService.notify_users(
                list(user_ids), title=title, body=body, channels=channels
            )

        return {
            'action_type': 'NOTIFY',
            'status': 'SUCCESS',
            'channels': channels,
            'user_count': len(user_ids),
        }


class WebhookRunner:
    """HTTP callback to external system."""

    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        url = config.get('url', '')
        method = config.get('method', 'POST').upper()
        body_tpl = config.get('body_tpl', '{}')
        timeout = config.get('timeout', 30)
        headers = config.get('headers', {})

        body_str = TemplateResolver.resolve(body_tpl, ticket, current_state_name)
        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            body = body_str

        kwargs: dict = {'headers': headers, 'timeout': timeout}
        if isinstance(body, dict):
            kwargs['json'] = body
        else:
            kwargs['data'] = body
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'text/plain'

        if method == 'POST':
            resp = requests.post(url, **kwargs)
        elif method == 'PUT':
            resp = requests.put(url, **kwargs)
        elif method == 'GET':
            resp = requests.get(url, headers=headers, timeout=timeout)
        else:
            resp = requests.request(method, url, **kwargs)

        resp.raise_for_status()
        return {
            'action_type': 'WEBHOOK',
            'status': 'SUCCESS',
            'http_status': resp.status_code,
        }


class OpsflowRunner:
    """Trigger an OpsFlow execution."""

    @staticmethod
    def run(config, ticket) -> dict:
        from itsm.services.opsflow_trigger import OpsflowTriggerService

        flow_id = config.get('flow_id')
        if not flow_id:
            return {'action_type': 'OPSFLOW', 'status': 'FAILED', 'error': 'flow_id is required'}

        OpsflowTriggerService.execute(ticket, flow_id, config.get('variable_mapping', {}))
        return {'action_type': 'OPSFLOW', 'status': 'SUCCESS', 'flow_id': flow_id}


class ModifyFieldRunner:
    """Update a field in ticket form_data."""

    @staticmethod
    def run(config, ticket, current_state_name='') -> dict:
        field_name = config.get('field_name')
        if not field_name:
            return {'action_type': 'MODIFY_FIELD', 'status': 'FAILED', 'error': 'field_name is required'}

        field_value = config.get('field_value', '')
        if config.get('value_type') == 'template':
            field_value = TemplateResolver.resolve(str(field_value), ticket, current_state_name)

        meta = dict(ticket.meta or {})
        form_data = dict(meta.get('form_data', {}))
        form_data[field_name] = field_value
        meta['form_data'] = form_data
        ticket.meta = meta
        ticket.save(update_fields=['meta'])

        return {'action_type': 'MODIFY_FIELD', 'status': 'SUCCESS', 'field': field_name}


# =============================================================================
# TriggerExecutor — enqueue and process trigger executions
# =============================================================================

class TriggerExecutor:
    """Enqueue matching triggers and process them asynchronously."""

    @staticmethod
    def enqueue(ticket, event_type, state_id=None):
        """Match triggers against event context and create PENDING executions."""
        try:
            triggers = TriggerMatcher.match(ticket, event_type, state_id)
            from itsm.models import TriggerExecution
            for trigger in triggers:
                TriggerExecution.objects.create(
                    trigger=trigger,
                    ticket=ticket,
                    event_type=event_type,
                    status='PENDING',
                )
            if triggers:
                logger.debug(
                    'TriggerExecutor enqueued %d executions for ticket #%d event=%s',
                    len(triggers), ticket.id, event_type,
                )
        except Exception as e:
            logger.warning(f'TriggerExecutor.enqueue error: {e}')

    @staticmethod
    def process_pending():
        """Called by APScheduler every 10s. Process batch of PENDING executions."""
        try:
            from itsm.models import TriggerExecution
            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                executions = list(TriggerExecution.objects.select_for_update(
                    skip_locked=True
                ).filter(
                    status='PENDING'
                ).select_related('trigger', 'ticket').prefetch_related(
                    'trigger__actions'
                )[:50])
                # Mark as PROCESSING to prevent concurrent workers from picking them up
                if executions:
                    TriggerExecution.objects.filter(
                        id__in=[e.id for e in executions]
                    ).update(status='PROCESSING')

            for exec in executions:
                try:
                    results = []
                    current_state_name = exec.ticket.current_status or ''
                    for action in exec.trigger.actions.order_by('order'):
                        try:
                            result = ActionRunner.run(action, exec.ticket, current_state_name)
                            result.setdefault('action_id', action.id)
                            result.setdefault('action_type', action.action_type)
                            results.append(result)
                        except Exception as e:
                            results.append({
                                'action_id': action.id,
                                'action_type': action.action_type,
                                'status': 'FAILED',
                                'error': str(e),
                            })
                    exec.action_results = results
                    has_failure = any(r.get('status') == 'FAILED' for r in results)
                    exec.status = 'FAILED' if has_failure else 'SUCCESS'
                except Exception as e:
                    exec.status = 'FAILED'
                    exec.action_results = [{'error': str(e)}]
                exec.save()
        except Exception as e:
            logger.warning(f'TriggerExecutor.process_pending error: {e}')

    @staticmethod
    def cleanup_old_executions():
        """Delete TriggerExecution records older than 365 days."""
        try:
            from itsm.models import TriggerExecution
            cutoff = timezone.now() - timedelta(days=365)
            deleted, _ = TriggerExecution.objects.filter(created_at__lt=cutoff).delete()
            if deleted:
                logger.info('Cleaned up %d old TriggerExecution records (365d+).', deleted)
        except Exception as e:
            logger.warning(f'TriggerExecutor.cleanup_old_executions error: {e}')
