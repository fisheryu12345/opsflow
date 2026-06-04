"""External-facing API endpoints — called by third-party systems

对外暴露的 API 端点，第三方系统通过此接口与平台交互。
路由前缀: /api/v2/open/
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

logger = logging.getLogger(__name__)

FSM = 'open_api_external'


@csrf_exempt
@require_http_methods(['GET'])
def health(request):
    """健康检查端点"""
    return JsonResponse({'code': 2000, 'msg': 'ok', 'data': {'status': 'healthy'}})


@csrf_exempt
@require_http_methods(['POST'])
def cmdb_sync(request):
    """CMDB 资产同步 — 第三方推送资产到 OpsFlow CMDB"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': '无效的 JSON'}, status=400)

    # TODO: 解析资产数据并写入 Neo4j
    count = data.get('assets', [])
    return JsonResponse({'code': 2000, 'msg': 'success', 'data': {'received': len(count)}})


@csrf_exempt
@require_http_methods(['POST'])
def create_incident(request):
    """第三方系统创建事件工单"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': '无效的 JSON'}, status=400)

    from itsm.models.incident import Incident
    import uuid
    inc = Incident.objects.create(
        incident_id=f"EXT-{uuid.uuid4().hex[:8].upper()}",
        title=data.get('title', ''),
        description=data.get('description', ''),
        priority=data.get('priority', 'P3'),
        source='api',
        cmdb_biz_id=data.get('biz_id', ''),
    )
    return JsonResponse({'code': 2000, 'msg': 'success', 'data': {'incident_id': inc.incident_id}})


@csrf_exempt
@require_http_methods(['GET'])
def query_incident(request, incident_id):
    """第三方查询工单状态"""
    from itsm.models.incident import Incident
    try:
        inc = Incident.objects.get(incident_id=incident_id)
        return JsonResponse({'code': 2000, 'data': {
            'incident_id': inc.incident_id,
            'title': inc.title,
            'status': inc.status,
            'priority': inc.priority,
            'assignee': inc.assignee.name if inc.assignee else None,
            'created_at': inc.create_datetime,
        }})
    except Incident.DoesNotExist:
        return JsonResponse({'code': 4000, 'msg': '工单不存在'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def trigger_execution(request):
    """第三方触发作业执行（支持 Plan 或快速执行）"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': '无效的 JSON'}, status=400)

    from job_platform.models import JobExecution, Plan, Script
    plan_id = data.get('plan_id')
    script_id = data.get('script_id')
    target_hosts = data.get('target_hosts', [])
    variables = data.get('params', {})

    if plan_id:
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return JsonResponse({'code': 4000, 'msg': '执行方案不存在'}, status=404)
        execution = JobExecution.objects.create(
            plan=plan, template=plan.template, status='pending',
            variables=variables, triggered_by='api',
            target_config={'static_hosts': target_hosts},
        )
    elif script_id:
        try:
            script = Script.objects.get(id=script_id)
        except Script.DoesNotExist:
            return JsonResponse({'code': 4000, 'msg': '脚本不存在'}, status=404)
        execution = JobExecution.objects.create(
            status='pending', variables=variables, triggered_by='api',
            target_config={'static_hosts': target_hosts},
        )
    else:
        return JsonResponse({'code': 4000, 'msg': '请提供 plan_id 或 script_id'}, status=400)

    from job_platform.services.executor import async_execute_plan
    async_execute_plan(execution.id)

    return JsonResponse({'code': 2000, 'msg': 'success', 'data': {'execution_id': execution.id}})
