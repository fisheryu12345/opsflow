# -*- coding: utf-8 -*-
"""Views for agent app"""

import uuid
import hashlib
import logging
import os
import requests as _requests

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from agent_app.models import (
    AgentInstance, AgentTaskExecution, AgentTaskResult,
    AgentFileTask, AgentCollect, AgentUpgrade,
)
from agent_app.serializers import (
    AgentInstanceSerializer, AgentTaskExecutionSerializer, AgentTaskResultSerializer,
    AgentFileTaskSerializer, AgentCollectSerializer, AgentUpgradeSerializer,
)

logger = logging.getLogger(__name__)


class AgentInstanceViewSet(viewsets.ModelViewSet):
    queryset = AgentInstance.objects.all()
    serializer_class = AgentInstanceSerializer
    filter_fields = ['status', 'os_type', 'enable_collect', 'enable_file']
    search_fields = ['hostname', 'ip', 'agent_id']

    @action(detail=True, methods=['post'])
    def refresh_token(self, request, pk=None):
        """刷新 Agent Token"""
        instance = self.get_object()
        import uuid
        new_token = str(uuid.uuid4()).replace('-', '') + str(uuid.uuid4()).replace('-', '')
        import hashlib
        instance.credential_token = hashlib.sha256(new_token.encode()).hexdigest()
        instance.save(update_fields=['credential_token'])
        return DetailResponse(data={'token': new_token}, msg="Token 已刷新")

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """仪表盘统计"""
        total = AgentInstance.objects.count()
        online = AgentInstance.objects.filter(status='online').count()
        offline = AgentInstance.objects.filter(status='offline').count()
        upgrading = AgentInstance.objects.exclude(upgrade_status='none').count()
        return DetailResponse(data={
            'total': total,
            'online': online,
            'offline': offline,
            'upgrading': upgrading,
        })

    @action(detail=False, methods=['post'])
    def push_install(self, request):
        """SSH 推送安装 Agent — 通过 SSH 在目标主机上安装 Agent

        请求体:
            hosts: ["10.0.1.2", ...]  目标主机 IP 列表
            username: "root"           SSH 用户名
            password: "..."            SSH 密码（可选）
            ssh_key: "..."            SSH 私钥内容（可选）
            port: 22                  SSH 端口
            agent_version: "1.0.0"    Agent 版本
        """
        hosts = request.data.get('hosts', [])
        username = request.data.get('username', 'root')
        password = request.data.get('password', '')
        ssh_key = request.data.get('ssh_key', '')
        port = request.data.get('port', 22)
        agent_version = request.data.get('agent_version', '1.0.0')
        server_host = request.data.get('server_host') or request.get_host().split(':')[0]

        if not hosts:
            return ErrorResponse(msg="No target hosts specified")

        results = {}
        for host in hosts:
            try:
                result = self._ssh_install_agent(
                    host, username, password, ssh_key, port, agent_version, server_host,
                )
                results[host] = result
            except Exception as e:
                logger.exception("Push install failed for %s", host)
                results[host] = {'success': False, 'error': str(e)}

        return DetailResponse(data={'results': results})

    def _ssh_install_agent(self, host, username, password, ssh_key, port, agent_version, server_host):
        """SSH into a host and install the agent."""
        # Generate token and create AgentInstance record
        raw_token = uuid.uuid4().hex + uuid.uuid4().hex
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        agent_id = str(uuid.uuid4())
        AgentInstance.objects.update_or_create(
            agent_id=agent_id,
            defaults={
                'ip': host,
                'hostname': host,
                'status': 'unknown',
                'credential_token': token_hash,
                'agent_version': agent_version,
            },
        )

        ws_host = server_host.split(':')[0] if ':' in server_host else server_host
        api_url = f"http://{server_host}"
        ws_url = f"ws://{ws_host}:8081/ws"

        # Build the install commands to run on the target host
        install_script = f"""#!/bin/bash
set -euo pipefail

mkdir -p /etc/opsflow-agent /var/lib/opsflow-agent /var/log/opsflow-agent

cat > /etc/opsflow-agent/opsflow-agent.toml << 'EOFCFG'
[agent]
agent_id = "{agent_id}"
token = "{raw_token}"
data_dir = "/var/lib/opsflow-agent"

[server]
endpoint = "{ws_url}"
api_endpoint = "{api_url}"
fingerprint_verify = false

[heartbeat]
interval = 30
jitter = 5

[logging]
level = "info"
file = "/var/log/opsflow-agent/agent.log"
max_size = 100
max_backups = 7
max_age = 30
compress = true
EOFCFG

cat > /etc/systemd/system/opsflow-agent.service << 'EOFUNIT'
[Unit]
Description=OpsFlow Agent
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/opsflow-agent --config /etc/opsflow-agent/opsflow-agent.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFUNIT

systemctl daemon-reload
systemctl enable opsflow-agent
systemctl start opsflow-agent
echo "Agent installed and started successfully"
"""
        # Execute via SSH (using paramiko for cross-platform support)
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            pkey = None
            if ssh_key:
                from io import StringIO
                pkey = paramiko.RSAKey.from_private_key(StringIO(ssh_key))

            client.connect(
                hostname=host, port=port, username=username,
                password=password if password else None,
                pkey=pkey,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )

            # Step 1: Upload agent binary via SFTP
            agent_bin = os.path.join(os.path.dirname(__file__),
                                     '..', '..', 'agent', 'build', 'opsflow-agent-linux-amd64')
            if not os.path.exists(agent_bin):
                # Fallback
                agent_bin = os.path.join(os.path.dirname(__file__),
                                         '..', '..', 'agent', 'build', 'agent-linux-amd64')
            if not os.path.exists(agent_bin):
                agent_bin = os.path.join(os.path.dirname(__file__),
                                         '..', '..', 'agent', 'build', 'agent.exe')
            agent_bin = os.path.normpath(agent_bin)

            sftp = client.open_sftp()
            sftp.put(agent_bin, '/usr/local/bin/opsflow-agent')
            sftp.chmod('/usr/local/bin/opsflow-agent', 0o755)
            sftp.close()
            logger.info("Uploaded agent binary to %s", host)

            # Step 2: Execute install script (config + service, no download needed)
            stdin, stdout, stderr = client.exec_command(install_script, timeout=120)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')

            success = exit_code == 0
            if success:
                AgentInstance.objects.filter(agent_id=agent_id).update(
                    status='online',
                    last_heartbeat=timezone.now(),
                )
            else:
                logger.warning("Install script failed on %s: exit_code=%s stderr=%s stdout=%s",
                               host, exit_code, err[:200], out[:200])
            return {
                'success': success,
                'agent_id': agent_id,
                'stdout': out if not success else '',
                'stderr': err or out if not success else '',
                'exit_code': exit_code,
            }
        except Exception as e:
            logger.exception("SSH install failed for %s", host)
            return {'success': False, 'agent_id': agent_id, 'error': str(e)}
        finally:
            client.close()

class AgentTaskExecutionViewSet(viewsets.ModelViewSet):
    queryset = AgentTaskExecution.objects.all()
    serializer_class = AgentTaskExecutionSerializer
    filter_fields = ['status', 'task_source', 'script_type']
    search_fields = ['exec_id', 'target_host']

    @action(detail=False, methods=['post'], url_path='exec')
    def execute(self, request):
        """前端下发指令 — 通过 Agent Server 执行

        请求体:
            agent_id: str   目标 Agent ID
            script_type: str shell/python/bat/powershell
            script_content: str 命令内容
            timeout: int    超时秒数
            work_dir: str   工作目录（可选）
        """
        agent_id = request.data.get('agent_id')
        script_type = request.data.get('script_type', 'shell')
        script_content = request.data.get('script_content', '')
        timeout = request.data.get('timeout', 3600)

        if not script_content:
            return ErrorResponse(msg="script_content is required")

        # Create task execution record
        exec_id = str(uuid.uuid4())
        task = AgentTaskExecution.objects.create(
            exec_id=exec_id,
            task_source='manual',
            target_host=request.data.get('target_host', ''),
            script_type=script_type,
            timeout=int(timeout),
            status='dispatching',
        )
        if agent_id:
            try:
                task.agent = AgentInstance.objects.get(agent_id=agent_id)
                task.save()
            except AgentInstance.DoesNotExist:
                pass

        # Forward to Agent Server
        agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:18080')
        try:
            resp = _requests.post(
                f"{agent_server_url}/api/v1/tasks/exec",
                json={
                    "agent_id": agent_id,
                    "target_host": task.target_host,
                    "exec_id": exec_id,
                    "script_type": script_type,
                    "script_content": script_content,
                    "timeout": int(timeout),
                },
                timeout=int(timeout) + 10,
            )
            if resp.status_code == 200:
                data = resp.json()
                task.status = 'running'
                task.save(update_fields=['status'])
                return DetailResponse(data={'exec_id': exec_id, 'agent_result': data})
        except Exception as _e:
            logger.error("Agent Server forward failed: %s: %s", type(_e).__name__, _e)

        # Fallback: save as dispatched, result will come via batch_results
        task.status = 'dispatching'
        task.save(update_fields=['status'])
        return DetailResponse(data={'exec_id': exec_id, 'status': 'dispatching'})

    @action(detail=False, methods=['post'])
    def batch_results(self, request):
        """Agent Server 批量写回执行结果"""
        results = request.data.get('results', [])
        for item in results:
            exec_id = item.get('exec_id')
            status = item.get('status', 'running')
            exit_code = item.get('exit_code')
            error_msg = item.get('error_msg', '')

            AgentTaskExecution.objects.filter(exec_id=exec_id).update(
                status=status,
                exit_code=exit_code,
                error_msg=error_msg or '',
            )

            # Write result chunks
            seq = item.get('seq', 1)
            stdout = item.get('stdout', '')
            stderr = item.get('stderr', '')
            is_final = item.get('is_final', False)
            if stdout or stderr:
                AgentTaskResult.objects.create(
                    exec_id=exec_id,
                    seq=seq,
                    is_final=is_final,
                    stdout=stdout,
                    stderr=stderr,
                )
        return DetailResponse(data={'processed': len(results)})

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """获取任务结果（按 pk / id）"""
        """获取任务结果流数据"""
        execution = self.get_object()
        results = AgentTaskResult.objects.filter(exec_id=execution.exec_id) \
            .order_by('seq')
        serializer = AgentTaskResultSerializer(results, many=True)
        return DetailResponse(data=serializer.data)


class AgentFileTaskViewSet(viewsets.ModelViewSet):
    queryset = AgentFileTask.objects.all()
    serializer_class = AgentFileTaskSerializer
    filter_fields = ['status', 'direction']

    @action(detail=False, methods=['post'], url_path='push')
    def push(self, request):
        """创建文件推送任务（支持 multipart 文件上传）"""
        target_host = request.data.get('target_host', '')
        target_path = request.data.get('target_path', '')
        file = request.FILES.get('file')

        if not target_host or not target_path:
            return ErrorResponse(msg="target_host and target_path are required")

        if file:
            # 有文件上传 — 存到 Agent Server 的文件暂存区
            from django.conf import settings
            upload_dir = os.path.join(settings.MEDIA_ROOT or '/tmp', 'agent_uploads')
            os.makedirs(upload_dir, exist_ok=True)
            import hashlib
            file_hash = hashlib.sha256()
            file_path = os.path.join(upload_dir, file.name)
            with open(file_path, 'wb+') as dest:
                for chunk in file.chunks():
                    dest.write(chunk)
                    file_hash.update(chunk)
            file_size = os.path.getsize(file_path)
            file_hash_hex = file_hash.hexdigest()
            source_path = file_path
        else:
            source_path = request.data.get('source_path', '')
            file_size = 0
            file_hash_hex = ''

        task = AgentFileTask.objects.create(
            direction='push',
            source_type='local',
            target_type='agent',
            file_name=os.path.basename(source_path),
            file_size=file_size,
            file_hash=file_hash_hex,
            status='pending',
        )

        # Forward to Agent Server's file coordinator
        agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:18080')
        try:
            import requests as _req
            _req.post(
                f"{agent_server_url}/api/v1/files/push",
                json={
                    "file_task_id": task.file_task_id,
                    "target_host": target_host,
                    "target_path": target_path,
                    "source_path": source_path,
                    "file_name": task.file_name,
                    "file_size": file_size,
                    "file_hash": file_hash_hex,
                    "download_url": f"http://{request.get_host()}/api/agent/file-download/{task.file_task_id}/",
                    "server_addr": request.get_host(),
                },
                timeout=10,
            )
        except Exception as e:
            logger.warning("Agent Server not reachable: %s", e)

        return DetailResponse(data={
            'file_task_id': task.file_task_id,
            'id': task.id,
            'status': 'pending',
        }, msg="文件推送任务已创建")


class DirectFileDownloadView:
    """Serve uploaded files for Agent Server to pull."""
    @staticmethod
    def as_view():
        from django.views.static import serve
        from django.conf import settings
        upload_dir = os.path.join(settings.MEDIA_ROOT or '/tmp', 'agent_uploads')
        return serve  # We'll use a proper view

    @staticmethod
    def get(request, file_task_id):
        """Handle /api/agent/files/direct/<id>/"""
        from django.http import FileResponse, Http404
        import mimetypes
        upload_dir = os.path.join(settings.MEDIA_ROOT or '/tmp', 'agent_uploads')
        # Find the file by task
        try:
            f = AgentFileTask.objects.get(file_task_id=file_task_id)
        except AgentFileTask.DoesNotExist:
            raise Http404("File task not found")

        file_path = os.path.join(upload_dir, f.file_name)
        if not os.path.exists(file_path):
            raise Http404("File not found")
        response = FileResponse(open(file_path, 'rb'), filename=f.file_name)
        response['Content-Length'] = os.path.getsize(file_path)
        return response


class AgentCollectViewSet(viewsets.ModelViewSet):
    queryset = AgentCollect.objects.all()
    serializer_class = AgentCollectSerializer
    filter_fields = ['agent', 'collect_type', 'status']

    @action(detail=False, methods=['post'])
    @authentication_classes([])
    @permission_classes([])
    def reports(self, request):
        """Agent Server 上报采集数据"""
        from django.utils import timezone
        reports = request.data if isinstance(request.data, list) else [request.data]
        processed = 0
        for item in reports:
            agent_id = item.get('agent_id')
            collect_type = item.get('collect_type')
            data = item.get('data', {})
            timestamp = item.get('timestamp')

            if not agent_id or not collect_type:
                continue

            # Upsert collect record
            AgentCollect.objects.update_or_create(
                agent_id=agent_id,
                collect_type=collect_type,
                defaults={
                    'last_data': data if isinstance(data, dict) else {},
                    'last_collect': timezone.now(),
                    'status': 'enabled',
                },
            )

            # Update AgentInstance host info if it's host_info type
            if collect_type == 'host_info' and isinstance(data, dict):
                AgentInstance.objects.filter(agent_id=agent_id).update(
                    hostname=data.get('hostname', ''),
                    ip=data.get('ip', ''),
                    os_type=data.get('os', ''),
                    os_version=data.get('os_version', ''),
                    arch=data.get('arch', ''),
                )
            processed += 1

        return DetailResponse(data={'processed': processed})


class AgentUpgradeViewSet(viewsets.ModelViewSet):
    queryset = AgentUpgrade.objects.all()
    serializer_class = AgentUpgradeSerializer
    filter_fields = ['status', 'agent']
