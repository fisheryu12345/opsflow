# -*- coding: utf-8 -*-
"""SSH connection manager — Connection pooling, auth, command execution

SSH 连接管理器：连接池复用、超时处理、密码/密钥认证、命令执行
"""

from __future__ import annotations

import logging
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import paramiko

logger = logging.getLogger(__name__)
FSM = 'ssh_client'

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    paramiko = None  # type: ignore[assignment]
    logger.warning('paramiko not installed — SSH executor disabled. '
                   'Install with: pip install paramiko')


class SSHConnectionPool:
    """Thread-safe SSH connection pool — 线程安全的 SSH 连接池

    Reuses connections for same (hostname, port, username) tuple.
    Connections are lazily created and kept alive until explicitly closed.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connections: dict[str, 'paramiko.SSHClient'] = {}

    def _make_key(self, hostname: str, port: int, username: str) -> str:
        return f'{username}@{hostname}:{port}'

    def get(self, hostname: str, port: int, username: str) -> Optional['paramiko.SSHClient']:
        """Get an existing connection from pool — 从连接池获取已有连接"""
        key = self._make_key(hostname, port, username)
        with self._lock:
            return self._connections.get(key)

    def put(self, hostname: str, port: int, username: str,
            client: 'paramiko.SSHClient') -> None:
        """Store a connection in pool — 将连接存入连接池"""
        key = self._make_key(hostname, port, username)
        with self._lock:
            self._connections[key] = client

    def remove(self, hostname: str, port: int, username: str) -> None:
        """Remove and close a connection — 移除并关闭连接"""
        key = self._make_key(hostname, port, username)
        with self._lock:
            client = self._connections.pop(key, None)
            if client:
                try:
                    client.close()
                except Exception:
                    pass

    def close_all(self) -> None:
        """Close all connections in pool — 关闭连接池中所有连接"""
        with self._lock:
            for key, client in self._connections.items():
                try:
                    client.close()
                except Exception:
                    pass
            self._connections.clear()


# Global connection pool — 全局连接池
_pool = SSHConnectionPool()


class SSHClient:
    """SSH client wrapper — 封装 paramiko 的 SSH 客户端

    Supports password-based and key-based authentication.
    Supports connection pooling, connect timeout, and exec timeout.

    Usage:
        client = SSHClient()
        # Password auth
        client.connect('10.0.0.1', port=22, username='root', password='xxx')
        # Key auth
        client.connect('10.0.0.1', port=22, username='root', key='<private_key_content>')
        # Execute command
        result = client.exec_command('ls -la', timeout=60)
        # {'stdout': '...', 'stderr': '...', 'exit_code': 0}
        client.close()
    """

    def __init__(self, use_pool: bool = True):
        self._client: Optional['paramiko.SSHClient'] = None
        self._hostname: str = ''
        self._port: int = 22
        self._username: str = ''
        self._use_pool = use_pool
        self._connected = False

    def connect(self, hostname: str, port: int = 22,
                username: str = 'root', password: str = '',
                key: str = '',
                connect_timeout: int = 10) -> bool:
        """Connect to SSH server — 连接 SSH 服务器

        Args:
            hostname: Hostname or IP address
            port: SSH port (default 22)
            username: Login username
            password: Login password (mutually exclusive with key)
            key: Private key content (mutually exclusive with password)
            connect_timeout: Connection timeout in seconds

        Returns:
            True if connected successfully, False otherwise
        """
        if not HAS_PARAMIKO:
            logger.error('paramiko not available, cannot connect')
            return False

        self._hostname = hostname
        self._port = port
        self._username = username

        # Check pool first — 先从连接池获取
        if self._use_pool:
            existing = _pool.get(hostname, port, username)
            if existing:
                try:
                    transport = existing.get_transport()
                    if transport and transport.is_active():
                        self._client = existing
                        self._connected = True
                        return True
                    else:
                        _pool.remove(hostname, port, username)
                except Exception:
                    _pool.remove(hostname, port, username)

        # Create new connection — 创建新连接
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if key:
                # Key-based auth — 密钥认证
                from io import StringIO
                key_file = StringIO(key)
                try:
                    pkey = paramiko.RSAKey.from_private_key(key_file)
                except paramiko.SSHException:
                    try:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    except paramiko.SSHException:
                        try:
                            key_file.seek(0)
                            pkey = paramiko.ECDSAKey.from_private_key(key_file)
                        except paramiko.SSHException:
                            logger.error(f'Failed to parse private key for {hostname}')
                            return False

                client.connect(
                    hostname, port=port, username=username,
                    pkey=pkey, timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                )
            else:
                # Password auth — 密码认证
                client.connect(
                    hostname, port=port, username=username,
                    password=password, timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                )

            self._client = client
            self._connected = True

            # Store in pool — 存入连接池
            if self._use_pool:
                _pool.put(hostname, port, username, client)

            logger.info(f'SSH connected: {username}@{hostname}:{port}')
            return True

        except paramiko.AuthenticationException:
            logger.error(f'SSH auth failed: {username}@{hostname}:{port}')
            return False
        except paramiko.SSHException as e:
            logger.error(f'SSH connection error: {hostname}:{port} — {e}')
            return False
        except Exception as e:
            logger.error(f'SSH connect failed: {hostname}:{port} — {e}')
            return False

    def exec_command(self, command: str, timeout: int = 3600) -> dict:
        """Execute a command on the remote host — 在远程主机上执行命令

        Args:
            command: Shell command to execute
            timeout: Command execution timeout in seconds (default 3600)

        Returns:
            {'stdout': str, 'stderr': str, 'exit_code': int}
            On failure, exit_code is -1 and stderr contains error message.
        """
        if not self._connected or not self._client:
            return {'stdout': '', 'stderr': 'Not connected', 'exit_code': -1}

        try:
            transport = self._client.get_transport()
            if not transport or not transport.is_active():
                self._connected = False
                return {'stdout': '', 'stderr': 'Connection lost', 'exit_code': -1}

            chan = transport.open_session()
            chan.settimeout(timeout)
            chan.exec_command(command)

            stdout_data = b''
            stderr_data = b''

            # Read stdout — 读取标准输出
            if chan.recv_ready():
                stdout_data = chan.recv(65536)

            # Read stderr — 读取标准错误
            if chan.recv_stderr_ready():
                stderr_data = chan.recv_stderr(65536)

            # Wait for completion with timeout — 等待执行完成
            import time
            deadline = time.time() + timeout
            while not chan.exit_status_ready():
                if time.time() > deadline:
                    chan.close()
                    return {
                        'stdout': stdout_data.decode('utf-8', errors='replace'),
                        'stderr': stderr_data.decode('utf-8', errors='replace') + '\nTIMEOUT',
                        'exit_code': -1,
                    }
                # Continue reading remaining data — 继续读取剩余数据
                if chan.recv_ready():
                    stdout_data += chan.recv(65536)
                if chan.recv_stderr_ready():
                    stderr_data += chan.recv_stderr(65536)
                time.sleep(0.1)

            # Final read — 最终读取
            while chan.recv_ready():
                stdout_data += chan.recv(65536)
            while chan.recv_stderr_ready():
                stderr_data += chan.recv_stderr(65536)

            exit_code = chan.recv_exit_status()
            chan.close()

            return {
                'stdout': stdout_data.decode('utf-8', errors='replace'),
                'stderr': stderr_data.decode('utf-8', errors='replace'),
                'exit_code': exit_code,
            }

        except paramiko.SSHException as e:
            self._connected = False
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}

    def close(self) -> None:
        """Close the SSH connection — 关闭 SSH 连接"""
        if self._client and self._hostname:
            _pool.remove(self._hostname, self._port, self._username)
        self._connected = False
        self._client = None

    def is_connected(self) -> bool:
        """Check if connection is active — 检查连接是否活跃"""
        if not self._client:
            return False
        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False


def close_all_connections():
    """Close all connections in the global pool — 关闭全局连接池所有连接"""
    _pool.close_all()
    logger.info('All SSH connections closed')


class SSHClientError(Exception):
    """SSH client base exception — SSH 客户端基础异常"""
    pass
