"""External-facing API endpoints — called by third-party systems

对外暴露的 API 端点，第三方系统通过此接口与平台交互。
路由前缀: /api/v2/open/

所有端点使用 OpenApiAuthentication（Token 认证）+ OpenApiRateThrottle（频率限制）。
"""

import json
import logging

from rest_framework.decorators import api_view, authentication_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from open_api.auth import OpenApiAuthentication
from open_api.throttling import OpenApiRateThrottle

logger = logging.getLogger(__name__)

FSM = "open_api_external"

# 所有端点统一应用认证和限流
AUTH_CLASSES = [OpenApiAuthentication]
THROTTLE_CLASSES = [OpenApiRateThrottle]


@api_view(['GET'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def health(request):
    """健康检查端点"""
    # 获取认证信息（如果有）
    app_info = {}
    if hasattr(request, 'auth') and request.auth:
        app = getattr(request.auth, 'app', None)
        if app:
            app_info = {
                'app_name': app.name,
                'app_id': app.id,
            }
    return DetailResponse(data={
        'status': 'healthy',
        'version': 'v2',
        **app_info,
    })


@api_view(['POST'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def cmdb_sync(request):
    """CMDB 资产同步 — 第三方推送资产到 OpsFlow CMDB"""
    data = request.data
    assets = data.get('assets', []) if isinstance(data, dict) else []

    # 校验数据格式
    if not isinstance(assets, list):
        return ErrorResponse(msg='assets 字段必须是数组', code=4000)

    # TODO: 解析资产数据并写入 Neo4j
    # 支持单条和批量同步
    count = len(assets)
    if count == 0:
        return DetailResponse(data={'received': 0}, msg='无资产数据')

    logger.info('[%s] Received %d assets from API sync', FSM, count)

    return DetailResponse(data={'received': count}, msg=f'成功接收 {count} 条资产')


@api_view(['POST'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def create_incident(request):
    """第三方系统创建事件工单"""
    data = request.data if isinstance(request.data, dict) else {}

    title = data.get('title', '').strip()
    if not title:
        return ErrorResponse(msg='title 为必填字段', code=4000)

    from itsm.models.incident import Incident
    import uuid

    inc = Incident.objects.create(
        incident_id=f"EXT-{uuid.uuid4().hex[:8].upper()}",
        title=title,
        description=data.get('description', ''),
        priority=data.get('priority', 'P3'),
        source='api',
        cmdb_biz_id=data.get('biz_id', ''),
    )
    return DetailResponse(data={'incident_id': inc.incident_id}, msg='工单创建成功')


@api_view(['GET'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def query_incident(request, incident_id):
    """第三方查询工单状态"""
    from itsm.models.incident import Incident
    try:
        inc = Incident.objects.get(incident_id=incident_id)
        return DetailResponse(data={
            'incident_id': inc.incident_id,
            'title': inc.title,
            'status': inc.status,
            'priority': inc.priority,
            'assignee': inc.assignee.name if inc.assignee else None,
            'created_at': inc.create_datetime,
        })
    except Incident.DoesNotExist:
        return ErrorResponse(msg='工单不存在', code=4000)


@api_view(['POST'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def trigger_execution(request):
    """第三方触发作业执行（支持 Plan 或快速执行）"""
    data = request.data if isinstance(request.data, dict) else {}

    from job_platform.models import JobExecution, Plan, Script
    plan_id = data.get('plan_id')
    script_id = data.get('script_id')
    target_hosts = data.get('target_hosts', [])
    variables = data.get('params', {})

    if plan_id:
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return ErrorResponse(msg='执行方案不存在', code=4000)
        execution = JobExecution.objects.create(
            plan=plan, template=plan.template, status='pending',
            variables=variables, triggered_by='api',
            target_config={'static_hosts': target_hosts},
        )
    elif script_id:
        try:
            script = Script.objects.get(id=script_id)
        except Script.DoesNotExist:
            return ErrorResponse(msg='脚本不存在', code=4000)
        execution = JobExecution.objects.create(
            status='pending', variables=variables, triggered_by='api',
            target_config={'static_hosts': target_hosts},
        )
    else:
        return ErrorResponse(msg='请提供 plan_id 或 script_id', code=4000)

    from job_platform.services.executor import async_execute_plan
    async_execute_plan(execution.id)

    return DetailResponse(data={'execution_id': execution.id}, msg='执行已触发')


# ──────────────────────────────────────────────
# OpsFlow Pipeline 端点（从 opsflow/core/apigw/ 迁移）
# ──────────────────────────────────────────────


@api_view(['POST'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def trigger_pipeline(request):
    """触发 OpsFlow Pipeline 执行 — 提供 template_id 或完整 pipeline_tree"""
    template_id = request.data.get('template_id')
    scheme_id = request.data.get('scheme_id')
    params = request.data.get('params', {})
    pipeline_tree = request.data.get('pipeline_tree')

    if not template_id and not pipeline_tree:
        return ErrorResponse(msg='请提供 template_id 或 pipeline_tree', code=4000)

    from opsflow.models import FlowTemplate, FlowExecution

    if template_id:
        try:
            template = FlowTemplate.objects.get(id=template_id)
        except FlowTemplate.DoesNotExist:
            return ErrorResponse(msg='Template not found', code=4000)

        execution = FlowExecution.objects.create(
            template=template,
            created_by=getattr(request.auth.app, 'created_by', None) if hasattr(request, 'auth') and request.auth else None,
            context={'trigger': 'open_api', 'params': params},
        )
        # 应用执行方案
        if scheme_id:
            from opsflow.models import ExecutionScheme
            try:
                scheme = ExecutionScheme.objects.get(id=scheme_id, template=template)
                if scheme.excluded_nodes:
                    execution.excluded_nodes = scheme.excluded_nodes
                    execution.save(update_fields=['excluded_nodes'])
            except ExecutionScheme.DoesNotExist:
                pass
    else:
        # 直接提供 pipeline_tree
        execution = FlowExecution.objects.create(
            template=None,
            created_by=None,
            context={
                'trigger': 'open_api',
                'params': params,
                'pipeline_tree': pipeline_tree,
            },
        )

    from opsflow.core.flow_engine import FlowEngine
    engine = FlowEngine(execution)
    engine.start(sync=False)

    return DetailResponse(data={
        'execution_id': execution.id,
        'status': execution.status,
    }, msg='Pipeline 已触发执行')


@api_view(['GET'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def query_execution(request, execution_id):
    """查询 Pipeline 执行状态"""
    from opsflow.models import FlowExecution
    try:
        execution = FlowExecution.objects.get(id=execution_id)
    except FlowExecution.DoesNotExist:
        return ErrorResponse(msg='Execution not found', code=4000)

    return DetailResponse(data={
        'execution_id': execution.id,
        'status': execution.status,
        'started_at': execution.started_at,
        'ended_at': execution.ended_at,
        'current_node': execution.current_node,
        'node_status': execution.node_status,
    })


@api_view(['GET'])
@authentication_classes(AUTH_CLASSES)
@throttle_classes(THROTTLE_CLASSES)
def list_pipeline_templates(request):
    """列出已发布 Pipeline 模板"""
    from opsflow.models import FlowTemplate
    templates = FlowTemplate.objects.filter(is_draft=False).values(
        'id', 'name', 'category', 'description', 'version',
    )
    return DetailResponse(data=list(templates))
