"""审计日志工具 — 记录用户操作到 OperationRecord 表

用法:
    log_operation(request.user, 'publish', 'template', template.id, template.name, request)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def log_operation(
    user,
    action: str,
    resource_type: str,
    resource_id: str = '',
    resource_name: str = '',
    detail: Optional[dict] = None,
    request=None,
):
    """记录操作审计"""
    try:
        from opsflow.models import OperationRecord
        record = OperationRecord(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            resource_name=resource_name,
            detail=detail or {},
            operator=user if user and not user.is_anonymous else None,
            ip_address=_get_client_ip(request) if request else '',
        )
        record.save()
    except Exception as e:
        logger.warning("[audit] Failed to log operation: %s", e)


def _get_client_ip(request):
    """从 request 提取客户端 IP"""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
