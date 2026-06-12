"""
ProcessManager — 进程管理器

在目标主机上以 service/systemd 方式运行，内置 APScheduler 定时采集。
职责：
  1. discover() — 通过 ss + ps 采集本机进程信息
  2. register() — HTTP POST 到 CMDB API 创建/更新 Process 实例
  3. _discover_calls() — 匹配 remote_connections 自动建立 CALLS 关系
  4. status() / start() / stop() — 本地进程管理

只采集 app_users 指定的系统用户进程，不处理系统进程。

用法:
    from process_manager import ProcessManager
    pm = ProcessManager(
        cmdb_api_url="http://opsflow.example.com/api/cmdb",
        api_token="xxx",
        host_instance_id="host-uuid",
        app_users=["www-data", "appuser", "mysql", "redis"],
    )
    pm.start_scheduler()  # 每 5 分钟自动采集上报
"""
import json
import logging
import re
import subprocess
import time
import os
import signal
from typing import Optional

logger = logging.getLogger(__name__)

# 依赖: pip install APScheduler requests
# (在 agent/setup.py 中追加)


class ProcessManager:
    """进程管理器 — 采集、上报、启停"""

    def __init__(self, cmdb_api_url: str, api_token: str,
                 host_instance_id: str, app_users: list[str],
                 interval: int = 300):
        """
        Args:
            cmdb_api_url: CMDB API 基础 URL（如 http://opsflow/api/cmdb）
            api_token: API 认证令牌
            host_instance_id: 本主机的 CMDB instance_id
            app_users: 只采集这些系统用户的进程
            interval: 采集间隔（秒），默认 300（5 分钟）
        """
        self.cmdb_api_url = cmdb_api_url.rstrip("/")
        self.api_token = api_token
        self.host_instance_id = host_instance_id
        self.app_users = app_users
        self.interval = interval
        self._session = None
        self._scheduler = None

    # ── HTTP 客户端 ────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送 HTTP 请求到 CMDB API"""
        import requests
        url = f"{self.cmdb_api_url}/{path.lstrip('/')}"
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("timeout", 15)
        resp = requests.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # ── 进程采集 ────────────────────────────────────────────────

    def discover(self) -> list[dict]:
        """采集本机进程信息

        1. ps aux 获取进程列表（按 app_users 过滤）
        2. ss -tlnp 获取监听端口（关联到 PID）
        3. ss -tnp 获取活跃连接（关联到 PID）
        4. 按 PID 合并

        Returns:
            [{name, pid, user, status, command, cpu_percent, memory_mb,
              listen_addresses, remote_connections}, ...]
        """
        processes = self._ps_aux()
        self._ss_listen(processes)
        self._ss_connections(processes)
        return list(processes.values())

    def _ps_aux(self) -> dict[int, dict]:
        """执行 ps aux 并过滤 app_users 的进程"""
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")[1:]  # 跳过标题行

        users_set = set(self.app_users)
        processes = {}

        for line in lines:
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            user = parts[0]
            if user not in users_set:
                continue

            pid = int(parts[1])
            cpu = float(parts[2])
            mem_vsz = float(parts[4])  # VSZ in KB
            command = parts[10][:200]

            # 取进程名（command 的第一个单词或 basename）
            name = command.split("/")[-1].split()[0][:64]

            processes[pid] = {
                "name": name,
                "pid": pid,
                "user": user,
                "status": "running",
                "command": command,
                "cpu_percent": round(cpu, 1),
                "memory_mb": round(mem_vsz / 1024, 1),
                "listen_addresses": [],
                "remote_connections": [],
            }

        return processes

    def _ss_listen(self, processes: dict[int, dict]):
        """ss -tlnp 获取监听端口，关联到 PID"""
        try:
            result = subprocess.run(
                ["ss", "-tlnp", "-p"], capture_output=True, text=True, timeout=10
            )
        except FileNotFoundError:
            logger.warning("ss command not found, skip listen port scan")
            return

        for line in result.stdout.strip().split("\n")[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            pid_match = re.search(r"pid=(\d+)", line)
            if not pid_match:
                continue
            pid = int(pid_match.group(1))
            if pid not in processes:
                continue

            local = parts[3]
            proto = parts[0].lower()
            ip, port = local.rsplit(":", 1)
            port = port.split(",")[0]
            try:
                processes[pid]["listen_addresses"].append({
                    "ip": "0.0.0.0" if ip == "*" else ip,
                    "port": int(port),
                    "protocol": proto,
                })
            except ValueError:
                continue

    def _ss_connections(self, processes: dict[int, dict]):
        """ss -tnp 获取活跃连接，关联到 PID"""
        try:
            result = subprocess.run(
                ["ss", "-tnp", "-p"], capture_output=True, text=True, timeout=10
            )
        except FileNotFoundError:
            return

        for line in result.stdout.strip().split("\n")[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            pid_match = re.search(r"pid=(\d+)", line)
            if not pid_match:
                continue
            pid = int(pid_match.group(1))
            if pid not in processes:
                continue

            local = parts[3]
            remote = parts[4]
            proto = parts[0].lower()

            loc_ip, loc_port = local.rsplit(":", 1)
            rem_ip, rem_port = remote.rsplit(":", 1)

            try:
                processes[pid]["remote_connections"].append({
                    "remote_ip": rem_ip,
                    "remote_port": int(rem_port),
                    "protocol": proto,
                    "local_port": int(loc_port.split(",")[0]),
                })
            except ValueError:
                continue

    # ── 上报 CMDB ──────────────────────────────────────────────

    def register(self, processes: list[dict]) -> dict:
        """上报进程到 CMDB

        1. upsert 每个进程（按 host_instance_id + pid 匹配）
        2. 建立 RUNS_ON 关系
        3. 交叉匹配 CALLS 关系
        4. 清理已消失的进程

        Returns:
            {"created": N, "updated": N, "calls_created": N, "errors": [...]}
        """
        stats = {"created": 0, "updated": 0, "calls_created": 0, "errors": []}

        # 获取当前已注册的进程列表
        try:
            resp = self._request("GET", "instances/Process/", params={
                "filters": json.dumps({"host_instance_id": self.host_instance_id}),
                "page_size": 200,
            })
        except Exception as e:
            logger.error("Failed to fetch existing processes: %s", e)
            stats["errors"].append(str(e))
            return stats

        existing_list = self._extract_items(resp)
        existing_by_pid = {e.get("pid"): e for e in existing_list if e.get("pid")}
        current_pids = set()

        for proc in processes:
            pid = proc["pid"]
            current_pids.add(pid)
            data = {
                "name": proc["name"],
                "pid": proc["pid"],
                "user": proc["user"],
                "status": proc["status"],
                "command": proc["command"],
                "cpu_percent": proc["cpu_percent"],
                "memory_mb": proc["memory_mb"],
                "listen_addresses": json.dumps(proc["listen_addresses"], ensure_ascii=False),
                "remote_connections": json.dumps(proc["remote_connections"], ensure_ascii=False),
                "host_instance_id": self.host_instance_id,
            }

            try:
                if pid in existing_by_pid:
                    # 更新
                    eid = existing_by_pid[pid].get("instance_id") or existing_by_pid[pid].get("id")
                    if eid:
                        self._request("PUT", f"instances/Process/{eid}/", json=data)
                        stats["updated"] += 1
                        instance_id = eid
                    else:
                        continue
                else:
                    # 创建
                    resp_data = self._request("POST", "instances/Process/", json=data)
                    instance_id = resp_data.get("instance_id") or resp_data.get("data", {}).get("instance_id", "")
                    if instance_id:
                        stats["created"] += 1
                    else:
                        continue

                # 建立 RUNS_ON 关系
                try:
                    self._request("POST", "instance-associations/create_relation/", json={
                        "src_id": instance_id,
                        "dst_id": self.host_instance_id,
                        "asst_type_id": "RUNS_ON",
                    })
                except Exception:
                    pass  # 关系可能已存在

            except Exception as e:
                logger.warning("Failed to upsert process PID=%s: %s", pid, e)
                stats["errors"].append(str(e))

        # 交叉匹配 CALLS
        try:
            stats["calls_created"] = self._discover_calls(processes)
        except Exception as e:
            logger.warning("CALLS discovery failed: %s", e)

        # 清理已消失的进程（标记 stopped）
        for epid, eproc in existing_by_pid.items():
            if epid not in current_pids:
                eid = eproc.get("instance_id") or eproc.get("id")
                if eid:
                    try:
                        self._request("PATCH", f"instances/Process/{eid}/", json={"status": "stopped"})
                        stats["updated"] += 1
                    except Exception:
                        pass

        return stats

    def _extract_items(self, resp: dict) -> list:
        """从 CMDB API 响应中提取 items 列表"""
        data = resp.get("data") or resp
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("items") or data.get("results") or data.get("data", [])
        return []

    def _discover_calls(self, local_processes: list[dict]) -> int:
        """交叉匹配 remote_connections → 建立 CALLS 关系

        遍历本地进程的 remote_connections，查询 CMDB 中其他主机的 Process
        如果 remote_ip:remote_port 匹配某个 Process 的 listen_addresses，建立 CALLS
        """
        # 收集所有远程连接目标
        targets = {}
        for proc in local_processes:
            for conn in proc.get("remote_connections", []):
                key = f"{conn['remote_ip']}:{conn['remote_port']}"
                targets[key] = conn

        if not targets:
            return 0

        # 查询 CMDB 中所有 Process（排除本机）
        try:
            resp = self._request("GET", "instances/Process/", params={
                "page_size": 500,
            })
        except Exception as e:
            logger.error("Failed to query CMDB processes for CALLS: %s", e)
            return 0

        all_procs = self._extract_items(resp)

        # 构建查找表：ip:port → instance_id
        listen_map = {}
        for p in all_procs:
            p_id = p.get("instance_id") or p.get("id", "")
            if not p_id or p.get("host_instance_id") == self.host_instance_id:
                continue
            addrs = p.get("listen_addresses", "[]")
            if isinstance(addrs, str):
                try:
                    addrs = json.loads(addrs)
                except (json.JSONDecodeError, TypeError):
                    addrs = []
            for addr in addrs:
                ip = addr.get("ip", "")
                port = addr.get("port", 0)
                for listen_ip in (ip, "0.0.0.0"):
                    listen_map[f"{listen_ip}:{port}"] = p_id

        # 匹配并建立 CALLS
        calls_count = 0
        for proc in local_processes:
            src_data = {p["name"]: p for p in local_processes if p.get("instance_id")}
            for conn in proc.get("remote_connections", []):
                key = f"{conn['remote_ip']}:{conn['remote_port']}"
                dst_id = listen_map.get(key)
                if dst_id:
                    try:
                        self._request("POST", "instance-associations/create_relation/", json={
                            "src_id": proc.get("instance_id", ""),
                            "dst_id": dst_id,
                            "asst_type_id": "CALLS",
                        })
                        calls_count += 1
                    except Exception:
                        pass

        return calls_count

    # ── 进程管理 ────────────────────────────────────────────────

    def status(self, pid_or_name: str) -> dict:
        """查询单个进程状态（本地 ps 检查）"""
        if pid_or_name.isdigit():
            ps = subprocess.run(
                ["ps", "-p", pid_or_name, "-o", "pid,user,%cpu,%mem,args", "--no-headers"],
                capture_output=True, text=True, timeout=5,
            )
        else:
            ps = subprocess.run(
                ["pgrep", "-x", pid_or_name], capture_output=True, text=True, timeout=5,
            )

        if ps.returncode == 0:
            return {"status": "running", "detail": ps.stdout.strip()[:200]}
        return {"status": "stopped", "detail": ""}

    def start(self, command: str, user: Optional[str] = None) -> dict:
        """启动进程（subprocess.Popen）"""
        try:
            if user:
                full_cmd = ["su", "-", user, "-c", command]
            else:
                full_cmd = ["sh", "-c", command]

            proc = subprocess.Popen(
                full_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return {"success": True, "pid": proc.pid, "message": f"Started PID {proc.pid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self, pid: int, force: bool = False) -> dict:
        """停止进程"""
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.kill(pid, sig)
            return {"success": True, "message": f"Signal {sig.name} sent to PID {pid}"}
        except ProcessLookupError:
            return {"success": False, "error": f"PID {pid} not found"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied to kill PID {pid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── 定时调度 ────────────────────────────────────────────────

    def start_scheduler(self):
        """启动定时采集"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
            self._scheduler.add_job(
                self._run, "interval", seconds=self.interval,
                id="process_discovery", name="Process Discovery",
                coalesce=True, max_instances=1,
            )
            self._scheduler.start()
            logger.info("ProcessManager scheduler started (interval=%ds)", self.interval)
        except ImportError:
            logger.warning("APScheduler not installed, running once then exiting")
            self._run()

    def stop_scheduler(self):
        """停止定时采集"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("ProcessManager scheduler stopped")

    def _run(self):
        """执行一次完整的采集+上报周期"""
        logger.info("ProcessManager: starting discovery cycle")
        try:
            processes = self.discover()
            logger.info("ProcessManager: discovered %d processes", len(processes))
            stats = self.register(processes)
            logger.info("ProcessManager: register result: %s", stats)
        except Exception as e:
            logger.exception("ProcessManager: cycle failed: %s", e)
