"""API 网关公开端点 — 供第三方系统集成调用"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response

from .auth import ApiTokenAuthentication


@api_view(['POST'])
@authentication_classes([ApiTokenAuthentication])
@permission_classes([IsAuthenticated])
def trigger_execution(request):
    """触发模板执行"""
    template_id = request.data.get('template_id')
    scheme_id = request.data.get('scheme_id')
    params = request.data.get('params', {})

    if not template_id:
        return ErrorResponse(msg='template_id is required', data=None, code=4000)

    from opsflow.models import FlowTemplate, FlowExecution
    try:
        template = FlowTemplate.objects.get(id=template_id)
    except FlowTemplate.DoesNotExist:
        return ErrorResponse(msg='Template not found', data=None, code=4000)

    execution = FlowExecution.objects.create(
        template=template,
        created_by=request.user,
        context={'trigger': 'apigw', 'params': params},
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

    from opsflow.core.flow_engine import FlowEngine
    engine = FlowEngine(execution)
    engine.start(sync=False)

    return DetailResponse(data={'execution_id': execution.id, 'status': execution.status}, msg='Execution started')


@api_view(['GET'])
@authentication_classes([ApiTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_execution_status(request, execution_id):
    """查询执行状态"""
    from opsflow.models import FlowExecution
    try:
        execution = FlowExecution.objects.get(id=execution_id)
    except FlowExecution.DoesNotExist:
        return ErrorResponse(msg='Execution not found', data=None, code=4000)

    return DetailResponse(data={
        'execution_id': execution.id,
        'status': execution.status,
        'started_at': execution.started_at,
        'ended_at': execution.ended_at,
    })


@api_view(['GET'])
@authentication_classes([ApiTokenAuthentication])
@permission_classes([IsAuthenticated])
def list_templates(request):
    """列出已发布模板"""
    from opsflow.models import FlowTemplate
    templates = FlowTemplate.objects.filter(is_draft=False).values('id', 'name', 'category', 'description', 'version')
    return DetailResponse(data=list(templates))
