"""Job execution engine — reuses opsagent SSH/local_exec under the hood

执行引擎：复用 opsagent 的执行通道，支持 SSH 远程执行和本地执行。
"""

import logging
import threading
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)

FSM = 'job_executor'


def execute_job(execution_id: int) -> dict:
    """同步执行作业 — 阻塞直到完成"""
    from ..models.models import JobExecution

    try:
        execution = JobExecution.objects.get(id=execution_id)
    except JobExecution.DoesNotExist:
        return {'error': '执行记录不存在'}

    job = execution.job
    if not job:
        execution.status = 'failed'
        execution.error_message = '关联作业已被删除'
        execution.finished_at = timezone.now()
        execution.save()
        return {'error': execution.error_message}

    execution.status = 'running'
    execution.started_at = timezone.now()
    execution.save(update_fields=['status', 'started_at'])

    # 构建命令
    if job.script:
        command = job.script.content
    else:
        command = job.command or ''

    # 替换参数
    for key, value in execution.params.items():
        command = command.replace(f'${{{key}}}', str(value))

    # 按主机执行
    results = {}
    overall_exit_code = 0
    for host in execution.target_hosts:
        try:
            result = _execute_on_host(host, command, execution.run_as, execution.timeout_seconds)
            results[host] = result
            if result.get('exit_code', 0) != 0:
                overall_exit_code = result.get('exit_code', 1)
        except Exception as e:
            results[host] = {'error': str(e), 'exit_code': -1}
            overall_exit_code = -1

    # 更新执行结果
    execution.result_detail = results
    execution.exit_code = overall_exit_code
    execution.status = 'success' if overall_exit_code == 0 else 'failed'
    execution.finished_at = timezone.now()

    success_count = sum(1 for r in results.values() if r.get('exit_code', -1) == 0)
    total_count = len(execution.target_hosts)
    execution.result_summary = f"{success_count}/{total_count} 台成功"
    execution.save()

    return {
        'execution_id': execution_id,
        'status': execution.status,
        'results': results,
        'summary': execution.result_summary,
    }


def async_execute_job(execution_id: int):
    """异步执行作业 — 后台线程执行"""
    thread = threading.Thread(target=execute_job, args=(execution_id,), daemon=True)
    thread.start()
    logger.info(f"后台执行作业: {execution_id}")


def _execute_on_host(host: str, command: str, run_as: str = 'root', timeout: int = 300) -> dict:
    """在单台主机上执行命令

    优先尝试 opsagent 的 SSH 工具，如果不可用则使用本地 subprocess。
    """
    try:
        from opsagent.tools.ssh import SshTool
        tool = SshTool()
        result = tool.execute(
            hostname=host,
            username=run_as,
            command=command,
            timeout=timeout,
        )
        return {
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', ''),
            'exit_code': result.get('returncode', -1),
        }
    except ImportError:
        logger.warning("opsagent SshTool 不可用，使用本地 subprocess")
        import subprocess
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return {
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'exit_code': proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'stdout': '', 'stderr': '执行超时', 'exit_code': -1}
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}
    except Exception as e:
        return {'stdout': '', 'stderr': str(e), 'exit_code': -1}
