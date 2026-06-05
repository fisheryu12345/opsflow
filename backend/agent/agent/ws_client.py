# -*- coding: utf-8 -*-
"""Agent WebSocket client — connects to opsflow server, receives commands

与 opsflow 服务端的 WebSocket 连接管理，接收命令并执行
"""

import json
import logging
import socket
import time
from threading import Thread, Event

logger = logging.getLogger(__name__)
FSM = 'agent_ws_client'


class WSClient:
    """WebSocket 客户端 — 与服务端保持长连接"""

    def __init__(self, server_url: str, agent_id: str, token: str,
                 on_exec=None, reconnect_delay: tuple = (1, 60)):
        self.server_url = server_url
        self.agent_id = agent_id
        self.token = token
        self.on_exec = on_exec or (lambda msg: None)
        self._running = Event()
        self._running.set()
        self._reconnect_delay = reconnect_delay  # (min, max) seconds
        self._ws = None
        self._thread: Thread | None = None

    def connect(self):
        """建立连接（阻塞，带自动重连）"""
        import websocket as ws

        delay = self._reconnect_delay[0]
        while self._running.is_set():
            try:
                url = f'{self.server_url}/ws/agent/?token={self.token}'
                self._ws = ws.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"连接失败: {e}")

            if not self._running.is_set():
                break

            logger.info(f"将在 {delay}s 后重连...")
            time.sleep(delay)
            delay = min(delay * 2, self._reconnect_delay[1])

    def start(self):
        """在后台线程中启动连接"""
        self._thread = Thread(target=self.connect, daemon=True, name='agent-ws')
        self._thread.start()
        logger.info(f"Agent WebSocket 客户端已启动: {self.agent_id}")

    def stop(self):
        """停止连接"""
        self._running.clear()
        if self._ws:
            self._ws.close()
        logger.info("Agent 已停止")

    def send_heartbeat(self):
        """发送心跳"""
        if self._ws and self._ws.sock and self._ws.sock.connected:
            self._ws.send(json.dumps({
                'type': 'heartbeat',
                'agent_id': self.agent_id,
                'hostname': socket.gethostname(),
                'timestamp': time.time(),
            }))

    def send_result(self, exec_id: str, exit_code: int,
                    stdout: str = '', stderr: str = ''):
        """回传执行结果"""
        if self._ws and self._ws.sock and self._ws.sock.connected:
            self._ws.send(json.dumps({
                'type': 'result',
                'exec_id': exec_id,
                'exit_code': exit_code,
                'stdout': stdout[-10000:],  # 限制长度
                'stderr': stderr[-5000:],
            }))

    def _on_open(self, ws):
        logger.info(f"已连接到服务端: {self.server_url}")

    def _on_message(self, ws, message):
        try:
            msg = json.loads(message)
            if msg.get('type') == 'exec':
                self.on_exec(msg)
            elif msg.get('type') == 'ping':
                ws.send(json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            logger.warning(f"收到无效消息: {message[:100]}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket 错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"连接已关闭 ({close_status_code}): {close_msg}")
