"""标准化错误码 — 全系统统一错误分类和封装

使用方式（view 中）:
    from opsflow.core.error_codes import ErrorCodes, api_success, api_error
    return api_success(...)
    return api_error(ErrorCodes.INVALID_STATE, ...)
"""

from dataclasses import dataclass
from typing import Any

from rest_framework.response import Response


@dataclass(frozen=True)
class _ErrorCode:
    code: int
    message: str


class ErrorCodes:
    """错误码常量"""
    # 通用 (10xxx)
    SUCCESS = _ErrorCode(2000, "success")
    UNKNOWN_ERROR = _ErrorCode(10001, "未知错误")
    VALIDATION_ERROR = _ErrorCode(10002, "参数校验失败")
    NOT_FOUND = _ErrorCode(10003, "资源不存在")
    PERMISSION_DENIED = _ErrorCode(10004, "权限不足")
    NOT_SUPPORTED = _ErrorCode(10005, "当前系统暂不支持该功能")

    # Template (20xxx)
    DRAFT_REQUIRED = _ErrorCode(20001, "仅草稿模板可执行此操作")
    PUBLISHED_REQUIRED = _ErrorCode(20002, "仅已发布模板可执行此操作")
    VERSION_NOT_FOUND = _ErrorCode(20003, "版本号不存在")
    SAFETY_CHECK_FAILED = _ErrorCode(20004, "流程存在安全风险")
    BAMBOO_INCOMPATIBLE = _ErrorCode(20005, "流程不兼容 bamboo-engine")
    NOTHING_TO_PUBLISH = _ErrorCode(20006, "无变更，无需发布")

    # Execution (30xxx)
    INVALID_STATE = _ErrorCode(30001, "当前状态不允许操作")
    NODE_ID_REQUIRED = _ErrorCode(30002, "node_id 是必填参数")
    NODE_COMMAND_FAILED = _ErrorCode(30003, "节点操作执行失败")
    EXECUTION_NOT_FOUND = _ErrorCode(30004, "执行实例不存在")

    # Schedule (40xxx)
    INVALID_CRON = _ErrorCode(40001, "Cron 表达式无效")
    INVALID_TIMEZONE = _ErrorCode(40002, "无效的时区")
    PAST_SCHEDULE = _ErrorCode(40003, "执行时间必须在未来")
    DRAFT_TEMPLATE = _ErrorCode(40004, "草稿模板不可创建调度")

    # Plugin (50xxx)
    PLUGIN_NOT_FOUND = _ErrorCode(50001, "未知插件")
    PLUGIN_EXECUTION_ERROR = _ErrorCode(50002, "插件执行异常")


def api_success(data: Any = None, msg: str = "success") -> Response:
    """标准成功响应"""
    return Response({'code': 2000, 'msg': msg, 'data': data})


def api_error(err: _ErrorCode, msg: str | None = None,
              data: Any = None, http_status: int = 400) -> Response:
    """标准错误响应"""
    return Response(
        {'code': err.code, 'msg': msg or err.message, 'data': data},
        status=http_status,
    )
