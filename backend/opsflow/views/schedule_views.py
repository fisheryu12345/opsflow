import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import SchedulePlan, FlowExecution
from opsflow.serializers import SchedulePlanSerializer, FlowExecutionSerializer
from opsflow.core.scheduler_service import opsflow_scheduler
from dvadmin.utils.json_response import DetailResponse, SuccessResponse

logger = logging.getLogger(__name__)


class SchedulePlanViewSet(viewsets.ModelViewSet):
    queryset = SchedulePlan.objects.all()
    serializer_class = SchedulePlanSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['template', 'status', 'schedule_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        plan = serializer.save(created_by=self.request.user)
        if plan.template and plan.template.pipeline_tree:
            plan.template_snapshot = plan.template.pipeline_tree
            plan.save(update_fields=['template_snapshot'])
        if not opsflow_scheduler._started:
            logger.warning(
                f"调度器未启动，计划 '{plan.name}' 已保存到数据库但不会自动触发。"
                f"请运行 `python manage.py start_opsflow_scheduler` 或设置 OPSFLOW_SCHEDULER_AUTOSTART=True"
            )
        opsflow_scheduler.add_plan(plan)

    def perform_update(self, serializer):
        plan = serializer.save()
        opsflow_scheduler.update_plan(plan)

    def perform_destroy(self, instance):
        opsflow_scheduler.remove_plan(instance)
        instance.delete()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return SuccessResponse(data=serializer.data, page=int(request.query_params.get('page', 1)),
                                   limit=self.paginator.get_page_size(request) if hasattr(self.paginator, 'get_page_size') else 10,
                                   total=self.paginator.page.paginator.count if hasattr(self.paginator, 'page') else queryset.count())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, total=queryset.count())

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        plan = self.get_object()
        if plan.status != SchedulePlan.Status.ACTIVE:
            return Response(
                {'code': 4000, 'msg': '仅运行中的调度可暂停', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        plan.status = SchedulePlan.Status.PAUSED
        plan.is_active = False
        plan.save(update_fields=['status', 'is_active'])
        opsflow_scheduler.pause_plan(plan)
        return DetailResponse(data=SchedulePlanSerializer(plan).data, msg="调度已暂停")

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        plan = self.get_object()
        if plan.status != SchedulePlan.Status.PAUSED:
            return Response(
                {'code': 4000, 'msg': '仅已暂停的调度可恢复', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        plan.status = SchedulePlan.Status.ACTIVE
        plan.is_active = True
        plan.save(update_fields=['status', 'is_active'])
        opsflow_scheduler.resume_plan(plan)
        return DetailResponse(data=SchedulePlanSerializer(plan).data, msg="调度已恢复")

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """手动立即触发一次"""
        plan = self.get_object()
        opsflow_scheduler._execute_plan(plan.id)
        return DetailResponse(msg="手动触发已提交")

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """查看该调度产生的执行记录"""
        plan = self.get_object()
        executions = FlowExecution.objects.filter(
            template=plan.template, created_by=plan.created_by
        ).order_by('-created_at')[:50]
        ser = FlowExecutionSerializer(executions, many=True)
        return SuccessResponse(data=ser.data)
