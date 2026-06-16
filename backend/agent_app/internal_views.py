# -*- coding: utf-8 -*-
"""Internal API views for Agent Server → Django communication.
   No authentication required — these are server-to-server endpoints.
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import AgentInstance, AgentTaskExecution, AgentTaskResult

logger = logging.getLogger(__name__)


@csrf_exempt
def batch_results(request):
    """Agent Server 批量写回执行结果"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    results = data.get('results', [])
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

    return JsonResponse({'code': 2000, 'data': {'processed': len(results)}, 'msg': 'success'})


@csrf_exempt
def collect_reports(request):
    """Agent Server 上报采集数据"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    reports = data if isinstance(data, list) else [data]
    processed = 0
    for item in reports:
        agent_id = item.get('agent_id')
        collect_type = item.get('collect_type')
        item_data = item.get('data', {})
        timestamp = item.get('timestamp')

        if not agent_id or not collect_type:
            continue

        # Update AgentInstance host info if it's host_info type
        if collect_type == 'host_info' and isinstance(item_data, dict):
            AgentInstance.objects.filter(agent_id=agent_id).update(
                hostname=item_data.get('hostname', ''),
                ip=item_data.get('ip', ''),
                os_type=item_data.get('os', ''),
                os_version=item_data.get('os_version', ''),
                arch=item_data.get('arch', ''),
            )
        processed += 1

    return JsonResponse({'code': 2000, 'data': {'processed': processed}, 'msg': 'success'})
