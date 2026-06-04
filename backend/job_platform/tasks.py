# -*- coding: utf-8 -*-
"""Celery tasks for job_platform — AI detection + execution engine

后台任务：AI 高危检测、作业执行引擎、步骤轮询
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)
FSM = 'job_platform_tasks'


# ════════════════════════════════════════════
#  AI 高危检测任务
# ════════════════════════════════════════════

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def ai_script_check(self, script_content: str, script_type: str = 'shell') -> dict:
    """AI 语义检测脚本安全性（异步）"""
    try:
        from opsflow.core.llm_service import analyze_by_llm
    except ImportError:
        logger.warning("opsflow LLM 服务不可用，跳过 AI 检测")
        return {'risk_level': 'unknown', 'reason': 'LLM 服务不可用'}

    from .services.dangerous_detector import build_ai_check_prompt
    prompt = build_ai_check_prompt(script_content, script_type)

    try:
        response = analyze_by_llm(prompt)
        result = _parse_ai_response(response)
        logger.info(f"AI 高危检测完成: risk_level={result.get('risk_level')}")
        return result
    except Exception as e:
        logger.error(f"AI 检测失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {'risk_level': 'unknown', 'reason': str(e)}


def _parse_ai_response(response: str) -> dict:
    """解析 AI 返回结果"""
    import json
    try:
        # 尝试提取 JSON
        if '{' in response:
            json_str = response[response.index('{'):response.rindex('}') + 1]
            return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        pass
    return {'risk_level': 'unknown', 'reason': response[:200]}


# ════════════════════════════════════════════
#  作业执行引擎任务
# ════════════════════════════════════════════

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def job_start_task(self, execution_id: int) -> dict:
    """作业执行入口 — 初始化并启动第一个步骤"""
    from .models import JobExecution, StepExecution, Step
    from .services.executor import _get_enabled_steps, _execute_step

    try:
        execution = JobExecution.objects.get(id=execution_id)
    except JobExecution.DoesNotExist:
        return {'error': f'Execution {execution_id} not found'}

    execution.status = 'running'
    execution.start_time = timezone.now()
    execution.save(update_fields=['status', 'start_time'])

    if execution.plan:
        steps = _get_enabled_steps(execution.plan)
    else:
        steps = []

    if not steps:
        execution.status = 'success'
        execution.end_time = timezone.now()
        execution.result_summary = 'No steps to execute'
        execution.save()
        return {'execution_id': execution_id, 'status': 'success', 'steps': 0}

    # 启动第一个步骤
    return step_exec_task(execution_id, steps[0].id)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def step_exec_task(self, execution_id: int, step_id: int) -> dict:
    """执行单个步骤"""
    from .models import JobExecution, StepExecution, Step

    try:
        execution = JobExecution.objects.get(id=execution_id)
        step = Step.objects.get(id=step_id)
    except (JobExecution.DoesNotExist, Step.DoesNotExist) as e:
        return {'error': str(e)}

    # 创建步骤执行记录
    step_exec = StepExecution.objects.create(
        execution=execution,
        step=step,
        step_type=step.type,
        step_name=step.name or f'Step {step_id}',
        status='running',
        started_at=timezone.now(),
    )

    try:
        result = _execute_single_step(step_exec, step)
        step_exec.status = 'success' if result.get('success') else 'failed'
    except Exception as e:
        step_exec.status = 'failed'
        step_exec.error_message = str(e)
        result = {'success': False, 'error': str(e)}

    step_exec.finished_at = timezone.now()
    step_exec.save()

    # 判断是否继续下一步
    if result.get('success'):
        next_step = step.next_step
        if next_step and next_step.enable:
            return step_exec_task(execution_id, next_step.id)
        # 全部完成
        execution.status = 'success'
        execution.end_time = timezone.now()
        execution.save()
        return {'execution_id': execution_id, 'status': 'success'}
    else:
        # 检查是否 ignore_error
        if step.type == 'script' and _has_ignore_error(step):
            next_step = step.next_step
            if next_step and next_step.enable:
                return step_exec_task(execution_id, next_step.id)
        execution.status = 'failed'
        execution.end_time = timezone.now()
        execution.save()
        return {'execution_id': execution_id, 'status': 'failed'}


def _execute_single_step(step_exec, step) -> dict:
    """执行单个步骤（同步执行）"""
    from .services.executor import _execute_script_step, _execute_approval_step, _execute_file_step

    if step.type == 'script':
        return _execute_script_step(step_exec, step)
    elif step.type == 'approval':
        return _execute_approval_step(step_exec, step)
    elif step.type == 'file':
        return _execute_file_step(step_exec, step)
    return {'success': False, 'error': f'Unknown step type: {step.type}'}


def _has_ignore_error(step) -> bool:
    """检查脚本步骤是否设置了忽略错误"""
    try:
        return step.script_step.ignore_error
    except AttributeError:
        return False
