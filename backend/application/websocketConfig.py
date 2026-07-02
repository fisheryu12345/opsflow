# -*- coding: utf-8 -*-
"""Django Channels WebSocket consumers — message center + real-time push

路由: ws/<str:service_uid>/ → DvadminWebSocket → MegCenter
认证：JWT 编码在 service_uid URL 参数中
"""

import json
import logging
import urllib

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from jwt import InvalidSignatureError

from application import settings

logger = logging.getLogger(__name__)


# -- Database helpers (sync-to-async bridge) ----------------------------------


@database_sync_to_async
def _get_message_unread(user_id):
    """获取用户的未读消息数量"""
    from common.models import MessageCenterTargetUser
    count = MessageCenterTargetUser.objects.filter(users=user_id, is_read=False).count()
    return count or 0


@database_sync_to_async
def _get_message_center_instance(message_id):
    """查询消息中心的目标用户 ID 列表"""
    from common.models import MessageCenter
    qs = MessageCenter.objects.filter(id=message_id).values_list('target_user', flat=True)
    return list(qs) if qs else []


def request_data(scope):
    """解析 query string（兼容旧代码调用）"""
    query_string = scope.get('query_string', b'').decode('utf-8')
    return urllib.parse.parse_qs(query_string)


# -- Consumers ----------------------------------------------------------------


class DvadminWebSocket(AsyncJsonWebsocketConsumer):
    """WebSocket 基类 — JWT 认证 + user_{id} 组管理"""

    async def connect(self):
        try:
            import jwt
            self.service_uid = self.scope["url_route"]["kwargs"]["service_uid"]
            decoded_result = jwt.decode(self.service_uid, settings.SECRET_KEY, algorithms=["HS256"])
            if decoded_result:
                self.user_id = decoded_result.get('user_id')
                self.chat_group_name = "user_" + str(self.user_id)
                await self.channel_layer.group_add(
                    self.chat_group_name,
                    self.channel_name
                )
                await self.accept()
                # 连接成功后推送未读消息数（使用旧格式保持前端兼容）
                unread_count = await _get_message_unread(self.user_id)
                if unread_count:
                    await self.send_json({
                        'sender': 'system',
                        'contentType': 'SYSTEM',
                        'content': "请查看您的未读消息~",
                        'unread': unread_count,
                    })
        except InvalidSignatureError:
            await self.disconnect(None)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
        try:
            await self.close(close_code)
        except Exception:
            pass


class MegCenter(DvadminWebSocket):
    """
    消息中心 WebSocket 处理器

    接收服务端推送（push_message）并转发到前端；
    接收客户端消息（receive）按 topic 路由处理。
    """

    async def receive(self, text_data):
        """处理前端发来的消息 — 按 topic 路由"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        topic = data.get('topic')
        if topic == 'notification':
            # 消息中继：前端发送 message_id，服务端查询目标用户后推送
            message_id = data.get('payload', {}).get('message_id')
            if message_id:
                user_list = await _get_message_center_instance(message_id)
                for send_user in user_list:
                    await self.channel_layer.group_send(
                        f"user_{send_user}",
                        {'type': 'push.message', 'json': data},
                    )
        # topic == 'heartbeat' 或未知 topic → 静默忽略
        # 心跳由前端定时发送 {token}，无需服务端处理

    async def push_message(self, event):
        """接收服务端 group_send 消息，推送到前端 WebSocket"""
        message = event['json']
        await self.send(text_data=json.dumps(message))
