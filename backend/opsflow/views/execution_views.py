"""FlowExecution ViewSet — 执行 CRUD

标准 CRUD 操作保留在此文件中。生命周期、节点命令、审批、
轨迹查询已提取到 views/mixins/ 中的 Mixin 类。
"""

from rest_framework import viewsets, exceptions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from opsflow.models import FlowExecution
from iam.models import Project
from iam.permissions import TenantPermission, EnvironmentGatePermission
from iam.resolvers import has_project_role
from opsflow.serializers import FlowExecutionSerializer, FlowExecutionDetailSerializer
from opsflow.views.base import ProjectFilteredViewSet
from opsflow.views.mixins.execution_lifecycle import ExecutionLifecycleMixin
from opsflow.views.mixins.execution_node_command import ExecutionNodeCommandMixin
from opsflow.views.mixins.execution_approval import ExecutionApprovalMixin
from opsflow.views.mixins.execution_trace import ExecutionTraceMixin
from dvadmin.utils.json_response import DetailResponse, ErrorResponse


class FlowExecutionViewSet(
    ExecutionLifecycleMixin,
    ExecutionNodeCommandMixin,
    ExecutionApprovalMixin,
    ExecutionTraceMixin,
    ProjectFilteredViewSet,
):
    queryset = FlowExecution.objects.all()
    serializer_class = FlowExecutionSerializer
    permission_classes = [IsAuthenticated, TenantPermission, EnvironmentGatePermission]
    filterset_fields = ['status', 'template', 'project', 'created_by', 'environment']
    ordering = ['-created_at']
    project_field = 'project'

    def get_queryset(self):
        """自动按当前用户过滤，只显示自己创建的流程"""
        qs = super().get_queryset()
        return qs.filter(created_by=self.request.user).select_related(
            'template', 'schedule_plan', 'created_by'
        )

    def get_serializer_class(self):
        """详情页使用 FlowExecutionDetailSerializer（含 state_tree + trace_summary）"""
        if self.action == 'retrieve':
            return FlowExecutionDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        # 设置项目归属 + 权限校验
        project_id = self.request.query_params.get('project_id')
        if project_id:
            if not has_project_role(self.request.user, int(project_id), 'editor'):
                raise exceptions.PermissionDenied(
                    'You need at least editor role to execute pipelines in this project'
                )
            project_kwargs = {'project_id': int(project_id)}
        else:
            from iam.models import Project
            default = Project.objects.first()
            project_kwargs = {'project': default} if default else {}

        # Resolve environment from request (validated by EnvironmentGatePermission)
        env_id = self.request.data.get('environment_id')
        if env_id:
            project_kwargs['environment_id'] = int(env_id)

        execution = serializer.save(created_by=self.request.user, **project_kwargs)
        # 为新执行初始化 state_tree
        if not execution.state_tree:
            execution.state_tree = {}
        # 冻结创建时的模板快照到专用字段（实现执行隔离）
        template = execution.template
        if template and template.pipeline_tree:
            snapshot_tree = template.snapshot.get('pipeline_tree') if template.snapshot else None
            # 检测 snapshot 是否过期：模板当前节点数 > snapshot 节点数 → 用当前树
            if snapshot_tree:
                sn_nd = len(snapshot_tree.get('nodes', []) or [])
                cur_nd = len(template.pipeline_tree.get('nodes', []) or [])
                if cur_nd > sn_nd:
                    snapshot_tree = template.pipeline_tree
            if not snapshot_tree:
                snapshot_tree = template.pipeline_tree
            execution.template_snapshot = {
                'pipeline_tree': snapshot_tree,
                'global_vars': template.global_vars,
                'template_version': template.version,
            }
            execution.save(update_fields=['state_tree', 'template_snapshot'])
            # ── 执行节点持久化 ──
            from opsflow.core.node_sync import sync_execution_nodes
            sync_execution_nodes(execution)
            # ── 结束 ──

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # ── 执行方案支持 ──
        scheme_id = request.data.get('scheme_id')
        if scheme_id and serializer.instance:
            from opsflow.models import ExecutionScheme
            try:
                scheme = ExecutionScheme.objects.get(id=scheme_id, template=serializer.instance.template)
                if scheme.excluded_nodes:
                    serializer.instance.excluded_nodes = scheme.excluded_nodes
                    serializer.instance.save(update_fields=['excluded_nodes'])
            except ExecutionScheme.DoesNotExist:
                pass
        # ── 结束 ──
        # ── 变量覆盖支持 ──
        variable_overrides = request.data.get('variable_overrides', {})
        if variable_overrides and serializer.instance and serializer.instance.template_snapshot:
            frozen_vars = dict(serializer.instance.template_snapshot.get('global_vars', {}))
            for key, value in variable_overrides.items():
                if key in frozen_vars:
                    if isinstance(frozen_vars[key], dict) and 'value' in frozen_vars[key]:
                        frozen_vars[key] = dict(frozen_vars[key])
                        frozen_vars[key]['value'] = value
                    else:
                        frozen_vars[key] = value
            serializer.instance.template_snapshot['global_vars'] = frozen_vars
            serializer.instance.save(update_fields=['template_snapshot'])
        # ── 结束 ──
        return DetailResponse(data=serializer.data, msg="创建成功")

    @action(detail=False, methods=['post'])
    def dry_run(self, request):
        """Dry Run — 用 test 原子替换后执行，不保存模板

        接收前端已替换好的 pipeline_tree，直接创建执行记录并启动。
        """
        import datetime
        from opsflow.core.flow_engine import FlowEngine
        from opsflow.core.node_sync import sync_execution_nodes
        from opsflow.models import FlowTemplate

        template_id = request.data.get('template')
        pipeline_tree = request.data.get('pipeline_tree')

        if not template_id or not pipeline_tree:
            return ErrorResponse(msg="缺少 template 或 pipeline_tree 参数", code=4000, status=400)

        try:
            template = FlowTemplate.objects.get(id=template_id)
        except FlowTemplate.DoesNotExist:
            return ErrorResponse(msg="模板不存在", code=4000, status=404)

        # 项目归属（复用 perform_create 的逻辑）
        project_id = request.query_params.get('project_id')
        if project_id:
            user_project_ids = self.get_user_project_ids()
            if int(project_id) not in user_project_ids:
                from rest_framework import exceptions
                raise exceptions.PermissionDenied('无权在当前项目创建资源')
            project = None  # 用 project_id 直接设
        else:
            project = Project.objects.first()

        execution = FlowExecution(
            template=template,
            project_id=int(project_id) if project_id else (project.id if project else None),
            created_by=request.user,
            status='pending',
            node_status={},
            state_tree={},
            context={'dry_run': True},
            template_snapshot={
                'pipeline_tree': pipeline_tree,
                'global_vars': {},
                'template_version': template.version,
            },
        )
        execution.save()

        # 同步执行节点
        sync_execution_nodes(execution)

        # 启动执行
        engine = FlowEngine(execution)
        engine.start()

        return DetailResponse(data={"id": execution.id}, msg="Dry run 执行已创建")