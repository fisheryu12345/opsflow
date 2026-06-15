# -*- coding: utf-8 -*-
"""Agent command executor — runs scripts/commands locally

本地命令执行器：接收服务端指令，执行并回传结果
"""

import logging
import subprocess
import tempfile
import os
import time
import threading

logger = logging.getLogger(__name__)
FSM = 'agent_executor'


def execute_command(exec_id: str, script: str, timeout: int = 300,
                    shell: bool = True, env: dict = None) -> dict:
    """执行命令并返回结果

    Returns:
        {exec_id, exit_code, stdout, stderr, duration}
    """
    start = time.time()
    try:
        proc = subprocess.run(
            script,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, **(env or {})},
        )
        duration = time.time() - start
        return {
            'exec_id': exec_id,
            'exit_code': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'duration': round(duration, 2),
        }
    except subprocess.TimeoutExpired:
        return {
            'exec_id': exec_id,
            'exit_code': -1,
            'stdout': '',
            'stderr': f'执行超时（{timeout}s）',
            'duration': timeout,
        }
    except Exception as e:
        return {
            'exec_id': exec_id,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e),
            'duration': round(time.time() - start, 2),
        }


def execute_script_file(exec_id: str, content: str, interpreter: str = '/bin/bash',
                        timeout: int = 300) -> dict:
    """将脚本写入临时文件后执行（支持多种解释器）"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh',
                                     delete=False, prefix='opsflow_') as f:
        f.write(content)
        script_path = f.name

    try:
        os.chmod(script_path, 0o755)
        result = execute_command(exec_id, f'{interpreter} {script_path}', timeout)
        return result
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


class BackgroundExecutor:
    """后台执行器 — 异步执行 + 实时回传"""

    def __init__(self, result_callback):
        self._running = {}
        self._callback = result_callback

    def start(self, exec_id: str, script: str, timeout: int = 300):
        """在后台线程中启动执行"""
        thread = threading.Thread(
            target=self._run,
            args=(exec_id, script, timeout),
            daemon=True,
            name=f'exec-{exec_id[:8]}',
        )
        self._running[exec_id] = thread
        thread.start()

    def _run(self, exec_id: str, script: str, timeout: int):
        """执行并回调"""
        try:
            # 实时回传 stdout
            proc = subprocess.Popen(
                script, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            stdout_lines = []
            for line in proc.stdout:
                stdout_lines.append(line)
                self._callback('stdout', exec_id, line.rstrip())

            proc.wait(timeout=timeout)
            stderr = proc.stderr.read()
            self._callback('result', exec_id, {
                'exit_code': proc.returncode,
                'stdout': ''.join(stdout_lines),
                'stderr': stderr,
            })
        except Exception as e:
            self._callback('error', exec_id, str(e))
        finally:
            self._running.pop(exec_id, None)
