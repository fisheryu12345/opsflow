# -*- coding: utf-8 -*-
"""ViewSet for ConnectorDefinition and ConnectorInstance

连接器定义与实例 CRUD + 额外动作（启停、健康检查）
"""

from rest_framework.decorators import action
from rest_framework import filters

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse

from ..models.connector import ConnectorDefinition, ConnectorInstance
from ..serializers import (
    ConnectorDefinitionSerializer,
    ConnectorDefinitionCreateUpdateSerializer,
    ConnectorInstanceSerializer,
    ConnectorInstanceCreateUpdateSerializer,
)

FSM = 'connector_viewset'


class ConnectorDefinitionViewSet(CustomModelViewSet):
    """
    连接器定义管理

    list: 查询连接器定义列表
    create: 创建连接器定义
    update: 修改连接器定义
    retrieve: 连接器定义详情
    destroy: 删除连接器定义
    """
    model = ConnectorDefinition
    queryset = ConnectorDefinition.objects.all()
    serializer_class = ConnectorDefinitionSerializer
    create_serializer_class = ConnectorDefinitionCreateUpdateSerializer
    update_serializer_class = ConnectorDefinitionCreateUpdateSerializer
    filter_fields = ['category', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['sort_order', 'name']


class ConnectorInstanceViewSet(CustomModelViewSet):
    """
    连接器实例管理

    list: 查询实例列表
    create: 创建实例
    update: 修改实例
    retrieve: 实例详情
    destroy: 删除实例
    health_check: 手动触发健康检查
    toggle_active: 启用/禁用
    """
    model = ConnectorInstance
    queryset = ConnectorInstance.objects.all()
    serializer_class = ConnectorInstanceSerializer
    create_serializer_class = ConnectorInstanceCreateUpdateSerializer
    update_serializer_class = ConnectorInstanceCreateUpdateSerializer
    filter_fields = ['definition', 'status', 'is_active']
    search_fields = ['name']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def health_check(self, request, pk=None):
        """手动触发健康检查"""
        instance = self.get_object()
        from integration.services.health_service import run_health_check
        healthy, msg = run_health_check(instance)
        from django.utils import timezone
        instance.status = 'online' if healthy else 'error'
        instance.last_health_check = timezone.now()
        instance.last_health_message = msg
        instance.save(update_fields=['status', 'last_health_check', 'last_health_message'])
        return DetailResponse(data={
            'status': instance.status,
            'message': msg,
        }, msg='健康检查完成')

    @action(methods=['POST'], detail=True)
    def toggle_active(self, request, pk=None):
        """启用/禁用实例"""
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save(update_fields=['is_active'])
        status_text = '已启用' if instance.is_active else '已禁用'
        return DetailResponse(data={'is_active': instance.is_active}, msg=status_text)

    @action(methods=['POST'], detail=True)
    def ai_chat(self, request, pk=None):
        """AI 连接器对话测试 — 调用 AI 模型的 chat 接口

        仅适用于 category=ai 的连接器实例。
        请求体: {"prompt": "你好，请用中文回复", "model": "gpt-4o(可选)"}
        """
        import logging
        logger = logging.getLogger(__name__)
        instance = self.get_object()
        definition = instance.definition

        if definition.category != 'ai':
            return ErrorResponse(msg='此连接器不是 AI 服务类型', code=4000)

        provider_path = definition.provider_class
        if not provider_path:
            return ErrorResponse(msg='连接器定义未配置适配器类', code=4000)

        prompt = request.data.get('prompt', '').strip()
        if not prompt:
            return ErrorResponse(msg='请输入测试消息', code=4000)

        try:
            # 动态导入适配器
            from importlib import import_module
            module_path, class_name = provider_path.rsplit('.', 1)
            module = import_module(module_path)
            provider_class = getattr(module, class_name)

            provider = provider_class(instance)

            # 调用 chat 方法
            model = request.data.get('model') or None
            result = provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )

            # 记录调用日志
            try:
                from integration.models.integration_log import IntegrationLog
                IntegrationLog.objects.create(
                    instance=instance,
                    action='ai_chat_test',
                    request_data={'prompt': prompt, 'model': model or definition.config_schema.get('properties', {}).get('model', {}).get('default') if hasattr(definition, 'config_schema') else None},
                    response_data={'model': result.get('model'), 'usage': result.get('usage')},
                    status='success',
                    duration_ms=0,
                )
            except Exception as log_err:
                logger.warning("Failed to log AI chat: %s", log_err)

            return DetailResponse(data={
                'content': result.get('content', ''),
                'model': result.get('model', ''),
                'usage': result.get('usage', {}),
            }, msg='AI 对话测试成功')

        except ImportError as e:
            return ErrorResponse(msg=f'适配器加载失败: {e}', code=4000)
        except Exception as e:
            logger.error("AI chat error [%s]: %s", instance.name, e)
            return ErrorResponse(msg=f'调用失败: {str(e)}', code=4000)
