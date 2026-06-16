# -*- coding: utf-8 -*-
"""Job execution engine — JobExecutor class + Plan / Quick execution support

作业执行引擎：支持 SSH / Local / Ansible 三种执行方式
通过 paramiko (SSH) 或 subprocess (Local) 执行脚本或命令
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import threading
from datetime import datetime
from typing import Optional

from django.utils import timezone

from ..models.subs.execution import JobExecution, StepExecution
from ..models.subs.step import Step
from ..models.subs.script import Script
from ..models.subs.base import Account

logger = logging.getLogger(__name__)
FSM = 'job_executor'

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    from ansible_runner import run as ansible_run
    HAS_ANSIBLE_RUNNER = True
except ImportError:
    HAS_ANSIBLE_RUNNER = False


# ══════════════════════════════════════════════════════════════
#  JobExecutor — 作业执行器主类
# ══════════════════════════════════════════════════════════════

class JobExecutor:
    """作业执行器 — 支持 SSH / Local / Ansible 三种执行方式

    封装 Plan 多步骤执行和快速执行，并提供变量渲染、高危检测、结果存储。
    """

    def __init__(self, execution_id: int):
        self.execution_id = execution_id
        self.execution: Optional[JobExecution] = None
        self._load_execution()

    def _load_execution(self):
        """Load JobExecution with related objects — 加载执行实例"""
        try:
            self.execution = JobExecution.objects.get(id=self.execution_id)
        except JobExecution.DoesNotExist:
            raise ValueError(f'Execution record not found: {self.execution_id}')

    # ─── Public API ───

    def execute(self) -> dict:
        """Execute job — 执行作业入口

        Determines executor type from JobDefinition or Plan, renders script,
        checks dangerous commands, and executes on target hosts.
        """
        execution = self.execution

        # Mark as running — 标记为执行中
        execution.status = 'running'
        execution.start_time = timezone.now()
        execution.save(update_fields=['status', 'start_time'])

        try:
            if execution.plan:
                return self._execute_plan(execution)
            return self._execute_script_execution(execution)
        except Exception as e:
            execution.status = 'failed'
            execution.end_time = timezone.now()
            execution.error_message = str(e)
            execution.save()
            logger.error(f'Execution failed: {execution.id} — {e}')
            return {
                'execution_id': execution.id,
                'status': 'failed',
                'error': str(e),
            }

    def _execute_plan(self, execution: JobExecution) -> dict:
        """Execute a Plan with multi-step support — 执行方案（多步骤）"""
        plan = execution.plan
        steps = _get_enabled_steps(plan)

        if not steps:
            execution.status = 'success'
            execution.end_time = timezone.now()
            execution.result_summary = '0 steps executed'
            execution.save()
            return {'execution_id': execution.id, 'status': 'success', 'steps': []}

        overall_success = True
        step_results = []

        for idx, step in enumerate(steps):
            execution.current_step_index = idx
            execution.save(update_fields=['current_step_index'])

            # Create step execution record — 创建步骤执行记录
            step_exec = StepExecution.objects.create(
                execution=execution,
                step=step,
                step_type=step.type,
                step_name=step.name or f'Step {idx + 1}',
                status='running',
                started_at=timezone.now(),
            )

            try:
                result = self._execute_step(step_exec, step, execution.variables or {})
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

        # Summarize — 汇总结果
        execution.status = 'success' if overall_success else 'failed'
        execution.end_time = timezone.now()
        success_count = sum(1 for r in step_results if r.get('success'))
        execution.result_summary = f'{success_count}/{len(steps)} steps succeeded'
        execution.save()

        return {
            'execution_id': execution.id,
            'status': execution.status,
            'steps': step_results,
            'summary': execution.result_summary,
        }

    def _execute_step(self, step_exec: StepExecution, step: Step,
                      variables: dict) -> dict:
        """Execute a single step — 执行单个步骤"""
        if step.type == 'script':
            return self._execute_script_step(step_exec, step, variables)
        elif step.type == 'approval':
            return _execute_approval_step(step_exec, step)
        elif step.type == 'file':
            return _execute_file_step(step_exec, step)
        return {'success': False, 'error': f'Unknown step type: {step.type}'}

    def _execute_script_step(self, step_exec: StepExecution, step: Step,
                             variables: dict) -> dict:
        """Execute a script step — 执行脚本步骤

        Renders variables into script content, checks dangerous commands,
        resolves target hosts, and executes via the appropriate channel.
        """
        script_step = getattr(step, 'script_step', None)
        if not script_step:
            return {'success': False, 'error': 'Script step config missing'}

        # Get script content — 获取脚本内容
        command = script_step.content
        if not command and script_step.script:
            command = script_step.script.content
        if not command:
            return {'success': False, 'error': 'No command or script to execute'}

        # Render variables — 变量渲染
        command = self._render_variables(command, variables)

        # Dangerous command detection — 高危命令检测
        from ..services.dangerous_detector import check_script_safety
        safety = check_script_safety(command, script_step.language or 'shell')
        if safety.get('blocked'):
            return {
                'success': False,
                'error': f'Dangerous command blocked: {safety.get("reason", "")}',
                'blocked': True,
                'safety_result': safety,
            }

        # Determine executor type — 确定执行方式
        executor_type = 'ssh'
        if step_exec.execution:
            executor_type = step_exec.execution.executor or 'ssh'

        timeout = script_step.timeout or 300

        # Resolve account — 解析执行账号
        account_name = 'root'
        account_port = 22
        account_password = ''
        account_key = ''
        if script_step.account:
            account_name = script_step.account.username
            account_port = script_step.account.port or 22
            account_password = script_step.account.password or ''
            account_key = script_step.account.ssh_key or ''

        # Resolve target hosts — 解析目标主机
        targets = _resolve_targets(step)
        if not targets:
            return {'success': False, 'error': 'No target hosts'}

        # Execute on hosts — 在目标主机上执行
        if executor_type == 'local':
            host_results = self._execute_local(command, timeout)
        elif executor_type == 'agent':
            host_results = self._execute_agent(targets, command, timeout)
        else:
            host_results = self._execute_on_hosts(
                targets, command, account_name, account_password,
                account_key, account_port, timeout,
            )

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

    def _execute_script_execution(self, execution: JobExecution) -> dict:
        """Quick execution — 快速执行（单次脚本/命令）"""
        target_config = execution.target_config or {}
        targets = target_config.get('static_hosts', execution.resolved_targets or [])
        params = execution.variables or {}
        executor_type = execution.executor or 'ssh'

        # Try to get command from plan template — 尝试从关联的 Plan/Template 获取命令
        command = ''
        if execution.plan and execution.plan.template:
            template = execution.plan.template
            if template.first_step:
                first_script_step = getattr(template.first_step, 'script_step', None)
                if first_script_step:
                    command = first_script_step.content
                    if not command and first_script_step.script:
                        command = first_script_step.script.content

        if not command:
            return {'error': 'No command to execute'}

        # Render variables — 变量渲染
        command = self._render_variables(command, params)

        # Dangerous command detection — 高危命令检测
        from ..services.dangerous_detector import check_script_safety
        safety = check_script_safety(command, 'shell')
        if safety.get('blocked'):
            execution.status = 'failed'
            execution.end_time = timezone.now()
            execution.error_message = f'Blocked: {safety.get("reason", "")}'
            execution.save()
            return {
                'execution_id': execution.id,
                'status': 'failed',
                'error': execution.error_message,
            }

        # Execute — 执行
        if executor_type == 'local':
            results = self._execute_local(command, 300)
        elif executor_type == 'agent':
            results = self._execute_agent(targets, command, 300)
        else:
            results = self._execute_on_hosts(targets, command, 'root', '', '', 22, 300)

        execution.result_summary = results.get('summary', '')
        execution.result_detail = results
        execution.exit_code = results.get('exit_code', 0)
        execution.status = 'success' if results.get('exit_code', -1) == 0 else 'failed'
        execution.end_time = timezone.now()
        execution.save()

        return {
            'execution_id': execution.id,
            'status': execution.status,
            'results': results,
        }

    # ─── Execution backends — 执行后端 ───

    def _execute_on_hosts(self, targets: list, command: str,
                          username: str = 'root', password: str = '',
                          key: str = '', port: int = 22,
                          timeout: int = 300) -> dict:
        """Execute command on multiple hosts via SSH — 在多台主机上执行命令

        Uses the SSHClient for connection pooling and proper SSH handling.
        Falls back to subprocess if paramiko is not available.
        """
        results = {}
        overall_exit_code = 0

        for host in targets:
            try:
                result = self._execute_ssh(
                    host, command, username, password, key, port, timeout,
                )
                results[host] = result
                if result.get('exit_code', 0) != 0:
                    overall_exit_code = result.get('exit_code', 1)
            except Exception as e:
                results[host] = {'error': str(e), 'exit_code': -1}
                overall_exit_code = -1

        success_count = sum(
            1 for r in results.values() if r.get('exit_code', -1) == 0
        )
        total_count = len(targets)

        return {
            'hosts': results,
            'exit_code': overall_exit_code,
            'summary': f'{success_count}/{total_count} hosts succeeded',
        }

    def _execute_ssh(self, host: str, command: str,
                     username: str = 'root', password: str = '',
                     key: str = '', port: int = 22,
                     timeout: int = 300) -> dict:
        """Execute command on a single host via SSH — 单台主机 SSH 执行

        Uses paramiko SSHClient if available, otherwise falls back to subprocess ssh.
        """
        if HAS_PARAMIKO:
            from .ssh_client import SSHClient
            client = SSHClient(use_pool=True)
            connected = client.connect(
                host, port=port, username=username,
                password=password, key=key,
                connect_timeout=10,
            )
            if not connected:
                return {
                    'stdout': '', 'stderr': f'SSH connection failed: {host}',
                    'exit_code': -1,
                }

            result = client.exec_command(command, timeout=timeout)

            # Return connection to pool — 归还连接到连接池（don't close, pool handles it）
            # Only close on error — 出错时关闭连接
            if result.get('exit_code', -1) != 0:
                client.close()

            return result
        else:
            # Fallback: subprocess ssh — 降级到命令行 ssh
            return self._execute_ssh_subprocess(host, command, username, port, timeout)

    def _execute_ssh_subprocess(self, host: str, command: str,
                                username: str = 'root', port: int = 22,
                                timeout: int = 300) -> dict:
        """Fallback SSH via subprocess — 通过 subprocess 执行 SSH 的降级方案"""
        ssh_cmd = [
            'ssh', '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=accept-new',
            '-p', str(port),
            f'{username}@{host}',
            command,
        ]
        try:
            proc = subprocess.run(
                ssh_cmd, capture_output=True, text=True,
                timeout=timeout,
            )
            return {
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'exit_code': proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'stdout': '', 'stderr': 'TIMEOUT', 'exit_code': -1}
        except FileNotFoundError:
            return {'stdout': '', 'stderr': 'ssh client not found', 'exit_code': -1}
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}

    def _execute_agent(self, hosts: list, command: str, timeout: int = 300) -> dict:
        """Execute command on hosts via Agent — 通过 Agent 执行命令"""
        import requests
        from django.conf import settings

        agent_server_url = getattr(settings, 'AGENT_SERVER_URL', 'http://localhost:8080')
        results = {}
        overall_exit_code = 0

        for host in hosts:
            try:
                resp = requests.post(
                    f"{agent_server_url}/api/v1/tasks/exec",
                    json={
                        "target_host": host,
                        "script_content": command,
                        "script_type": "shell",
                        "timeout": timeout,
                    },
                    timeout=timeout + 10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results[host] = {
                        'stdout': data.get('stdout', ''),
                        'stderr': data.get('stderr', ''),
                        'exit_code': data.get('exit_code', 0),
                    }
                else:
                    results[host] = {
                        'stdout': '',
                        'stderr': f"Agent Server returned HTTP {resp.status_code}: {resp.text}",
                        'exit_code': -1,
                    }
            except Exception as e:
                results[host] = {'stdout': '', 'stderr': str(e), 'exit_code': -1}
                overall_exit_code = -1

        summary_lines = []
        for host, result in results.items():
            summary_lines.append(f"[{host}] exit_code={result['exit_code']}")
            if result['stdout']:
                summary_lines.append(result['stdout'][:500])
            if result['stderr']:
                summary_lines.append(f"ERR: {result['stderr'][:200]}")

        return {
            'results': results,
            'exit_code': overall_exit_code,
            'summary': '\n'.join(summary_lines),
        }

    def _execute_local(self, command: str, timeout: int = 300) -> dict:
        """Execute command locally — 本地执行命令"""
        try:
            # Use shell=True for pipe support — 使用 shell=True 支持管道
            proc = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=timeout,
            )
            exit_code = proc.returncode
            # Build result in the same format as SSH
            return {
                'hosts': {
                    'localhost': {
                        'stdout': proc.stdout,
                        'stderr': proc.stderr,
                        'exit_code': exit_code,
                    }
                },
                'exit_code': exit_code,
                'summary': 'Completed' if exit_code == 0 else f'Failed (code={exit_code})',
            }
        except subprocess.TimeoutExpired:
            return {
                'hosts': {'localhost': {'error': 'TIMEOUT', 'exit_code': -1}},
                'exit_code': -1,
                'summary': 'Timeout',
            }
        except Exception as e:
            return {
                'hosts': {'localhost': {'error': str(e), 'exit_code': -1}},
                'exit_code': -1,
                'summary': str(e),
            }

    def _execute_ansible(self, command: str, hosts: list[str],
                         username: str = 'root', timeout: int = 300) -> dict:
        """Execute via Ansible — 通过 Ansible 执行

        Generates a temporary playbook and invokes ansible-runner.
        Falls back to ansible command line if ansible-runner is not available.
        """
        if HAS_ANSIBLE_RUNNER:
            return self._execute_ansible_runner(command, hosts, username, timeout)
        return self._execute_ansible_cli(command, hosts, username, timeout)

    def _execute_ansible_runner(self, command: str, hosts: list[str],
                                username: str, timeout: int) -> dict:
        """Execute via ansible-runner — 通过 ansible-runner Python API 执行"""
        import tempfile
        import shutil

        private_data_dir = tempfile.mkdtemp(prefix='ansible_')

        try:
            # Create inventory — 创建主机清单
            inventory = '\n'.join(hosts) + '\n'
            inv_dir = os.path.join(private_data_dir, 'inventory')
            os.makedirs(inv_dir, exist_ok=True)
            with open(os.path.join(inv_dir, 'hosts'), 'w') as f:
                f.write(inventory)

            # Create playbook — 创建剧本
            playbook = {
                'name': 'Job Platform Execution',
                'hosts': 'all',
                'gather_facts': 'no',
                'tasks': [{
                    'name': 'Execute command',
                    'shell': command,
                    'register': 'result',
                }, {
                    'name': 'Debug output',
                    'debug': {'msg': '{{ result.stdout }}'},
                }],
            }
            playbook_dir = os.path.join(private_data_dir, 'project')
            os.makedirs(playbook_dir, exist_ok=True)
            playbook_path = os.path.join(playbook_dir, 'main.yml')
            import yaml
            with open(playbook_path, 'w') as f:
                yaml.dump([playbook], f)

            # Run — 执行
            result = ansible_run(
                private_data_dir=private_data_dir,
                playbook='main.yml',
                json_mode=True,
                timeout=timeout,
            )

            # Parse results — 解析结果
            host_results = {}
            overall_exit_code = 0
            for host in hosts:
                facts = result.get_facts(host)
                host_results[host] = {
                    'stdout': facts.get('result', {}).get('stdout', ''),
                    'stderr': facts.get('result', {}).get('stderr', ''),
                    'exit_code': 0 if result.status == 'successful' else 1,
                }
                if result.status != 'successful':
                    overall_exit_code = 1

            return {
                'hosts': host_results,
                'exit_code': overall_exit_code,
                'summary': f'Ansible: {result.status}',
            }

        except Exception as e:
            return {
                'hosts': {},
                'exit_code': -1,
                'summary': f'Ansible error: {e}',
            }
        finally:
            shutil.rmtree(private_data_dir, ignore_errors=True)

    def _execute_ansible_cli(self, command: str, hosts: list[str],
                             username: str, timeout: int) -> dict:
        """Execute via ansible CLI — 通过 ansible 命令行执行"""
        # Create temporary inventory file — 创建临时主机清单文件
        import shutil
        tmp_dir = tempfile.mkdtemp(prefix='ansible_cli_')
        try:
            inv_path = os.path.join(tmp_dir, 'inventory')
            with open(inv_path, 'w') as f:
                for h in hosts:
                    f.write(f'{h} ansible_user={username}\n')

            cmd = [
                'ansible', '-i', inv_path, 'all',
                '-m', 'shell', '-a', command,
                '--timeout', str(timeout),
            ]

            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )

            return {
                'hosts': {h: {'stdout': proc.stdout, 'stderr': proc.stderr,
                              'exit_code': proc.returncode} for h in hosts},
                'exit_code': proc.returncode,
                'summary': 'Completed' if proc.returncode == 0 else 'Failed',
            }
        except subprocess.TimeoutExpired:
            return {'hosts': {}, 'exit_code': -1, 'summary': 'Timeout'}
        except FileNotFoundError:
            return {'hosts': {}, 'exit_code': -1, 'summary': 'ansible CLI not found'}
        except Exception as e:
            return {'hosts': {}, 'exit_code': -1, 'summary': str(e)}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ─── Utilities — 实用工具 ───

    @staticmethod
    def _render_variables(content: str, variables: dict) -> str:
        """Render variables into script content — 渲染变量到脚本内容

        Supports {{ var_name }} and ${var_name} syntax.
        """
        if not variables:
            return content

        result = content
        for key, value in variables.items():
            if value is None:
                value = ''
            str_value = str(value)
            # {{ var_name }} syntax — Django/Jinja2 style
            result = result.replace('{{ ' + key + ' }}', str_value)
            result = result.replace('{{' + key + '}}', str_value)
            # ${var_name} syntax — Shell style
            result = result.replace('${' + key + '}', str_value)
            # $var_name (word boundary) — Variable expansion
            result = re.sub(r'\$' + re.escape(key) + r'\b', str_value, result)

        return result

    @staticmethod
    def _resolve_target(step: Step) -> list:
        """Resolve target hosts from step config — 从步骤配置解析目标主机"""
        return _resolve_targets(step)


# ══════════════════════════════════════════════════════════════
#  Async helpers — 异步执行辅助函数
# ══════════════════════════════════════════════════════════════

def async_execute(execution_id: int):
    """Execute job asynchronously in background thread — 后台异步执行作业"""
    thread = threading.Thread(
        target=lambda: JobExecutor(execution_id).execute(),
        daemon=True,
    )
    thread.start()
    logger.info(f'Background execution started: {execution_id}')


def async_execute_plan(execution_id: int):
    """Execute plan asynchronously (backward-compatible) — 异步执行方案（兼容旧接口）"""
    async_execute(execution_id)


def async_execute_job(execution_id: int):
    """Quick execute asynchronously (backward-compatible) — 异步快速执行（兼容旧接口）"""
    async_execute(execution_id)


# 向后兼容别名
execute_job = lambda execution_id: async_execute_plan(execution_id)
execute_plan = lambda execution_id: JobExecutor(execution_id).execute()


# ══════════════════════════════════════════════════════════════
#  Internal helpers — 内部辅助函数
# ══════════════════════════════════════════════════════════════

def _get_enabled_steps(plan) -> list[Step]:
    """获取方案中启用的步骤链表"""
    enable_ids = set(plan.enable_step_ids or [])
    if not enable_ids:
        return []

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


def _execute_approval_step(step_exec: StepExecution, step: Step) -> dict:
    """执行审批步骤 — 创建 ITSM 工单"""
    approval_step = getattr(step, 'approval_step', None)
    if not approval_step:
        return {'success': False, 'error': 'Approval step config missing'}

    step_exec.status = 'waiting_user'
    step_exec.save(update_fields=['status'])

    # TODO: Integrate with ITSM for approval ticket creation — 对接 ITSM 创建审批工单
    logger.info(f'Approval step waiting: {step.name}, approvers: {approval_step.approvers}')
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
        return {'success': False, 'error': 'File step config missing'}

    targets = _resolve_targets(step)
    if not targets:
        return {'success': False, 'error': 'No target hosts'}

    logger.info(f'File distribution: {file_step.destination_path} -> {len(targets)} hosts')
    return {
        'success': True,
        'destination': file_step.destination_path,
        'targets': targets,
        'mode': file_step.transfer_mode,
    }


def _resolve_targets(step: Step) -> list:
    """解析步骤的目标主机列表（TODO: CMDB 动态解析）"""
    script_step = getattr(step, 'script_step', None)
    if script_step:
        account_id = script_step.account_id
    # TODO: Resolve from step's TargetConfig — 从步骤的 TargetConfig 解析
    return []
