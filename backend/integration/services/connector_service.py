"""集成中心 — 连接器服务层

提供按类型/状态查找连接器的便捷函数，供外部模块（opsflow、opsagent）调用。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_ai_connector() -> Optional[object]:
    """获取当前活跃的 AI 连接器实例

    按 ConnectorDefinition.category='ai' 且 is_active=True 查找，
    返回 OpenAIConnector / AnthropicConnector 适配器实例。
    未找到时返回 None。

    使用方在获取到适配器后调用 .chat() 方法进行 AI 对话。
    """
    try:
        from integration.models.connector import ConnectorDefinition, ConnectorInstance

        # 在所有 AI 类型的连接器定义中取最新创建的活跃实例
        instance = ConnectorInstance.objects.filter(
            definition__category='ai',
            definition__is_active=True,
            is_active=True,
        ).order_by('-id').first()

        if not instance:
            logger.warning("[Integration] No active AI connector instance found")
            return None

        # 动态加载适配器
        provider_class = instance.definition.provider_class
        if not provider_class:
            logger.error("[Integration] ConnectorDefinition %s has no provider_class", instance.definition.code)
            return None

        module_path, class_name = provider_class.rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)
        connector = adapter_cls(instance)
        return connector
    except Exception as e:
        logger.exception("[Integration] Failed to get AI connector: %s", e)
        return None


def get_ai_connector_or_raise():
    """获取 AI 连接器，找不到时抛出异常"""
    connector = get_ai_connector()
    if connector is None:
        raise RuntimeError(
            "No active AI connector configured. "
            "Please go to Integration Center and add an AI service connector (e.g. OpenAI/DeepSeek) "
            "with valid credentials."
        )
    return connector
