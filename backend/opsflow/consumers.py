import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class FlowMonitorConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket 消费者 — 推送执行状态到画布"""

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'execution_{self.execution_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # 连接后发送当前状态快照
        execution_data = await self.get_execution_state()
        if execution_data:
            await self.send_json({
                'type': 'init_state',
                'data': execution_data
            })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive_json(self, content):
        msg_type = content.get('type', '')
        if msg_type == 'ping':
            await self.send_json({'type': 'pong'})

    async def node_status(self, event):
        """接收 Celery 任务推送的节点状态变更"""
        await self.send_json({
            'type': 'node_status',
            'node_id': event['node_id'],
            'status': event['status'],
            'message': event.get('message', ''),
        })

    async def execution_completed(self, event):
        """执行完成通知"""
        await self.send_json({
            'type': 'execution_completed',
            'status': event['status'],
        })

    @database_sync_to_async
    def get_execution_state(self):
        from .models import FlowExecution
        try:
            execution = FlowExecution.objects.get(id=self.execution_id)
            return {
                'id': execution.id,
                'status': execution.status,
                'node_status': execution.node_status,
                'current_node': execution.current_node,
            }
        except FlowExecution.DoesNotExist:
            return None
