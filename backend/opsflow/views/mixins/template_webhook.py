"""Template Webhook — 模板 Webhook 回调配置端点 Mixin"""

import logging

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from opsflow.models import WebhookConfig, WebhookLog
from dvadmin.utils.json_response import DetailResponse, SuccessResponse

logger = logging.getLogger(__name__)


class TemplateWebhookMixin:
    """模板 Webhook CRUD + 日志查询"""

    @action(detail=True, methods=['get', 'post'])
    def webhooks(self, request, pk=None):
        """获取/创建模板的 Webhook 配置列表"""
        template = self.get_object()

        if request.method == 'GET':
            hooks = WebhookConfig.objects.filter(template=template)
            data = [
                {
                    'id': h.id,
                    'name': h.name,
                    'url': h.url,
                    'trigger_events': h.trigger_events,
                    'retry_count': h.retry_count,
                    'retry_interval': h.retry_interval,
                    'enabled': h.enabled,
                    'has_secret': bool(h.secret),
                    'created_at': h.created_at.isoformat(),
                }
                for h in hooks
            ]
            return SuccessResponse(data=data)

        # POST: 创建
        name = request.data.get('name', '')
        url = request.data.get('url', '')
        trigger_events = request.data.get('trigger_events', ['completed'])
        secret = request.data.get('secret', '')
        retry_count = request.data.get('retry_count', 3)
        retry_interval = request.data.get('retry_interval', 10)
        enabled = request.data.get('enabled', True)

        if not name or not url:
            return Response({'code': 4000, 'msg': 'name and url are required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        wh = WebhookConfig.objects.create(
            template=template,
            name=name,
            url=url,
            secret=secret,
            trigger_events=trigger_events,
            retry_count=retry_count,
            retry_interval=retry_interval,
            enabled=enabled,
            created_by=request.user,
        )
        return DetailResponse(data={'id': wh.id, 'name': wh.name})

    @action(detail=True, methods=['patch', 'delete'], url_path='webhooks/(?P<webhook_id>[^/.]+)')
    def webhook_detail(self, request, pk=None, webhook_id=None):
        """更新/删除单个 Webhook 配置"""
        template = self.get_object()
        try:
            wh = WebhookConfig.objects.get(id=webhook_id, template=template)
        except WebhookConfig.DoesNotExist:
            return Response({'code': 4000, 'msg': 'Webhook not found', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            wh.delete()
            return Response({'code': 2000, 'msg': 'success', 'data': None})

        # PATCH
        for field in ('name', 'url', 'secret', 'trigger_events',
                      'retry_count', 'retry_interval', 'enabled'):
            if field in request.data:
                setattr(wh, field, request.data[field])
        wh.save()
        return DetailResponse(data={'id': wh.id})

    @action(detail=True, methods=['get'], url_path='webhooks/(?P<webhook_id>[^/.]+)/logs')
    def webhook_logs(self, request, pk=None, webhook_id=None):
        """获取 Webhook 投递日志"""
        template = self.get_object()
        try:
            wh = WebhookConfig.objects.get(id=webhook_id, template=template)
        except WebhookConfig.DoesNotExist:
            return Response({'code': 4000, 'msg': 'Webhook not found', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)

        logs = WebhookLog.objects.filter(webhook=wh)[:50]
        data = [
            {
                'id': log.id,
                'event': log.event,
                'status': log.status,
                'response_status': log.response_status,
                'retry_count': log.retry_count,
                'error_message': log.error_message,
                'created_at': log.created_at.isoformat(),
            }
            for log in logs
        ]
        return SuccessResponse(data=data)
