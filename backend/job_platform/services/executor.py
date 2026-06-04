# -*- coding: utf-8 -*-
"""Job execution engine — 支持 Plan 多步骤 + Script 快速执行

执行通道: SSH / Ansible / Agent
执行模式:
  - Plan 执行: 按步骤链表依次执行
  - 快速执行: 单次脚本/命令执行
"""

import json
import logging
import subprocess
import threading
from datetime import datetime

from django.utils import timezone

from ..models.subs.execution import JobExecution, StepExecution
from ..models.subs.step import Step

logger = logging.getLogger(__name__)
FSM = 'job_executor'


def execute_plan(execution_id: int) -> dict:
    """执行完整方案 — 按步骤链表依次执行"""
    try:
        execution = JobExecution.objects.get(id=execution_id)
    except JobExecution.DoesNotExist:
        return {'error': '执行记录不存在'}

    execution.status = 'running'
    execution.start_time = timezone.now()
    execution.save(update_fields=['status', 'start_time'])

    plan = execution.plan
    if not plan:
        return execute_script_execution(execution)

    # 获取启用的步骤（链表遍历）
    steps = _get_enabled_steps(plan)

    if not steps:
        execution.status = 'success'
        execution.end_time = timezone.now()
        execution.result_summary = '0 steps executed'
        execution.save()
        return {'execution_id': execution_id, 'status': 'success', 'steps': []}

    overall_success = True
    step_results = []

    for idx, step in enumerate(steps):
        execution.current_step_index = idx
        execution.save(update_fields=['current_step_index'])

        # 创建步骤执行记录
        step_exec = StepExecution.objects.create(
            execution=execution,
            step=step,
            step_type=step.type,
            step_name=step.name or f'Step {idx+1}',
            status='running',
            started_at=timezone.now(),
        )

        try:
            result = _execute_step(step_exec, step)
            step_results.append(result)

            if result.get('success'):
                step_exec.status = 'success'
            else:
                step_exec.status = 'ignored_error' if step.script_step and step.script_step.ignore_error else 'failed'
                if not step.script_step or not step.script_step.ignore_error:
                    overall_success = False

            step_exec.finished_at = timezone.now()
            step_exec.save()

        except Exception as e:
            step_exec.status = 'failed'
            step_exec.error_message = str(e)
            step_exec.finished_at = timezone.now()
            step_exec.save()
            overall_success = False

        if not overall_success and not (step.script_step and step.script_step.ignore_error):
            break

    # 汇总结果
    execution.status = 'success' if overall_success else 'failed'
    execution.end_time = timezone.now()
    success_count = sum(1 for r in step_results if r.get('success'))
    execution.result_summary = f'{success_count}/{len(steps)} steps succeeded'
    execution.save()

    return {
        'execution_id': execution_id,
        'status': execution.status,
        'steps': step_results,
        'summary': execution.result_summary,
    }


def execute_script_execution(execution: JobExecution) -> dict:
    """快速执行 — 单次脚本/命令"""
    # 解析目标主机
    target_config = execution.target_config or {}
    targets = target_config.get('static_hosts', execution.resolved_targets or [])
    params = execution.variables or {}

    command = ''
    if execution.plan and execution.plan.template:
        # 尝试从模板获取脚本
        pass

    if not command:
        return {'error': '没有可执行的命令'}

    results = _execute_on_hosts(targets, command, 'root')

    execution.result_summary = results.get('summary', '')
    execution.exit_code = results.get('exit_code', 0)
    execution.status = 'success' if results.get('exit_code') == 0 else 'failed'
    execution.end_time = timezone.now()
    execution.save()

    return {
        'execution_id': execution.id,
        'status': execution.status,
        'results': results,
    }


def async_execute_plan(execution_id: int):
    """异步执行方案"""
    thread = threading.Thread(target=execute_plan, args=(execution_id,), daemon=True)
    thread.start()
    logger.info(f"后台执行方案: {execution_id}")


def async_execute_job(execution_id: int):
    """异步快速执行（保持向后兼容）"""
    thread = threading.Thread(target=execute_plan, args=(execution_id,), daemon=True)
    thread.start()
    logger.info(f"后台快速执行: {execution_id}")


# 向后兼容别名
execute_job = execute_plan


# ─── 内部工具 ───

def _get_enabled_steps(plan) -> list[Step]:
    """获取方案中启用的步骤链表"""
    enable_ids = set(plan.enable_step_ids or [])
    if not enable_ids:
        return []

    # 从链表头部开始遍历
    template = plan.template
    if not template:
        return []

    current = template.first_step
    enabled_steps = []
    seen = set()

    while current and current.id not in seen:
        seen.add(current.id)
        if current.id in enable_ids and current.enable:
            enabled_steps.append(current)
        current = current.next_step

    return enabled_steps


def _execute_step(step_exec: StepExecution, step: Step) -> dict:
    """执行单个步骤"""
    if step.type == 'script':
        return _execute_script_step(step_exec, step)
    elif step.type == 'approval':
        return _execute_approval_step(step_exec, step)
    elif step.type == 'file':
        return _execute_file_step(step_exec, step)
    return {'success': False, 'error': f'未知步骤类型: {step.type}'}


def _execute_script_step(step_exec: StepExecution, step: Step) -> dict:
    """执行脚本步骤"""
    script_step = getattr(step, 'script_step', None)
    if not script_step:
        return {'success': False, 'error': '脚本步骤配置缺失'}

    command = script_step.content
    if not command and script_step.script:
        command = script_step.script.content
    if not command:
        return {'success': False, 'error': '没有可执行的命令或脚本'}

    account_name = 'root'
    timeout = script_step.timeout or 300

    # 获取目标主机
    targets = _resolve_targets(step)
    if not targets:
        return {'success': False, 'error': '没有目标主机'}

    host_results = _execute_on_hosts(targets, command, account_name, timeout)

    step_exec.host_results = host_results
    step_exec.exit_code = host_results.get('exit_code', 0)
    step_exec.save(update_fields=['host_results', 'exit_code'])

    success = host_results.get('exit_code', -1) == 0
    return {
        'success': success,
        'targets': targets,
        'host_results': host_results,
        'summary': host_results.get('summary', ''),
    }


def _execute_approval_step(step_exec: StepExecution, step: Step) -> dict:
    """执行审批步骤 — 创建 ITSM 工单"""
    approval_step = getattr(step, 'approval_step', None)
    if not approval_step:
        return {'success': False, 'error': '审批步骤配置缺失'}

    step_exec.status = 'waiting_user'
    step_exec.save(update_fields=['status'])

    # TODO: 对接 ITSM 创建审批工单
    logger.info(f"审批步骤等待: {step.name}, 审批人: {approval_step.approvers}")
    return {
        'success': True,
        'approval_type': approval_step.approval_type,
        'approvers': approval_step.approvers,
        'waiting': True,
    }


def _execute_file_step(step_exec: StepExecution, step: Step) -> dict:
    """执行文件分发步骤"""
    file_step = getattr(step, 'file_step', None)
    if not file_step:
        return {'success': False, 'error': '文件步骤配置缺失'}

    targets = _resolve_targets(step)
    if not targets:
        return {'success': False, 'error': '没有目标主机'}

    logger.info(f"文件分发: {file_step.destination_path} -> {len(targets)} hosts")
    return {
        'success': True,
        'destination': file_step.destination_path,
        'targets': targets,
        'mode': file_step.transfer_mode,
    }


def _execute_on_hosts(targets: list, command: str, run_as: str = 'root',
                       timeout: int = 300) -> dict:
    """在目标主机上执行命令"""
    results = {}
    overall_exit_code = 0

    for host in targets:
        try:
            result = _execute_on_host(host, command, run_as, timeout)
            results[host] = result
            if result.get('exit_code', 0) != 0:
                overall_exit_code = result.get('exit_code', 1)
        except Exception as e:
            results[host] = {'error': str(e), 'exit_code': -1}
            overall_exit_code = -1

    success_count = sum(1 for r in results.values() if r.get('exit_code', -1) == 0)
    total_count = len(targets)

    return {
        'hosts': results,
        'exit_code': overall_exit_code,
        'summary': f'{success_count}/{total_count} hosts succeeded',
    }


def _execute_on_host(host: str, command: str, run_as: str = 'root',
                      timeout: int = 300) -> dict:
    """单台主机执行"""
    try:
        from opsagent.tools.ssh import SshTool
        tool = SshTool()
        result = tool.execute(
            hostname=host, username=run_as,
            command=command, timeout=timeout,
        )
        return {
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', ''),
            'exit_code': result.get('returncode', -1),
        }
    except ImportError:
        # Fallback to subprocess
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=timeout,
            )
            return {
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'exit_code': proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'stdout': '', 'stderr': 'TIMEOUT', 'exit_code': -1}
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}
    except Exception as e:
        return {'stdout': '', 'stderr': str(e), 'exit_code': -1}


def _resolve_targets(step: Step) -> list:
    """解析步骤的目标主机列表（TODO: CMDB 动态解析）"""
    script_step = getattr(step, 'script_step', None)
    if script_step:
        account_id = script_step.account_id
    return []  # TODO: 从 step 配置的 TargetConfig 解析
