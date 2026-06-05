# -*- coding: utf-8 -*-
"""Agent main entry — daemon process entry point

Agent 守护进程入口：启动 WebSocket 连接、心跳、命令执行
"""

import argparse
import logging
import signal
import sys
import time
import threading

from .ws_client import WSClient
from .executor import execute_command, execute_script_file, BackgroundExecutor

logger = logging.getLogger(__name__)
FSM = 'agent_main'


class AgentDaemon:
    """Agent 守护进程"""

    def __init__(self, server_url: str, agent_id: str, token: str):
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id or f'agent-{socket.gethostname()}'
        self.token = token
        self._running = True
        self._heartbeat_interval = 30  # seconds

        # 执行器
        self.executor = BackgroundExecutor(result_callback=self._on_exec_result)

        # WebSocket 客户端
        self.ws = WSClient(
            server_url=self.server_url,
            agent_id=self.agent_id,
            token=self.token,
            on_exec=self._on_exec_command,
        )

    def _on_exec_command(self, msg: dict):
        """收到执行命令"""
        exec_id = msg.get('exec_id', '')
        script = msg.get('script', '')
        timeout = msg.get('timeout', 300)
        interpreter = msg.get('interpreter', '/bin/bash')

        logger.info(f"执行命令: {exec_id}, timeout={timeout}s")

        if msg.get('mode') == 'file':
            # 文件写入模式
            file_path = msg.get('path', '')
            content = msg.get('content', '')
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.ws.send_result(exec_id, 0, stdout=f'Written: {file_path}')
            except Exception as e:
                self.ws.send_result(exec_id, -1, stderr=str(e))
        else:
            # 脚本执行模式 — 后台执行，实时回传
            self.executor.start(exec_id, script, timeout)

    def _on_exec_result(self, msg_type: str, exec_id: str, data):
        """执行结果回调"""
        if msg_type == 'stdout':
            # 实时 stdout 行
            if self.ws:
                import json
                try:
                    self.ws._ws.send(json.dumps({
                        'type': 'log', 'exec_id': exec_id, 'line': data
                    }))
                except Exception:
                    pass
        elif msg_type == 'result':
            self.ws.send_result(
                exec_id, data['exit_code'],
                stdout=data.get('stdout', ''),
                stderr=data.get('stderr', ''),
            )
        elif msg_type == 'error':
            self.ws.send_result(exec_id, -1, stderr=data)

    def _heartbeat_loop(self):
        """心跳保活循环"""
        while self._running:
            try:
                self.ws.send_heartbeat()
            except Exception as e:
                logger.warning(f"心跳发送失败: {e}")
            time.sleep(self._heartbeat_interval)

    def start(self):
        """启动 Agent"""
        import socket
        logger.info(f"OpsFlow Agent v0.1.0 启动...")
        logger.info(f"  服务端: {self.server_url}")
        logger.info(f"  Agent ID: {self.agent_id}")
        logger.info(f"  主机名: {socket.gethostname()}")

        # 启动心跳线程
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        # 启动 WebSocket 连接（阻塞）
        self.ws.start()

    def stop(self):
        """停止 Agent"""
        self._running = False
        self.ws.stop()
        logger.info("Agent 已停止")


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(description='OpsFlow Agent')
    parser.add_argument('--server', required=True, help='OpsFlow 服务端地址 (ws://host:port)')
    parser.add_argument('--agent-id', help='Agent ID (默认: agent-<hostname>)')
    parser.add_argument('--token', required=True, help='认证 Token')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    import socket
    agent = AgentDaemon(
        server_url=args.server,
        agent_id=args.agent_id or f'agent-{socket.gethostname()}',
        token=args.token,
    )

    def signal_handler(sig, frame):
        logger.info("收到关闭信号...")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    agent.start()


if __name__ == '__main__':
    main()
