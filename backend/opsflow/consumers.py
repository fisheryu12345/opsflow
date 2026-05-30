import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class FlowMonitorConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket 消费者 — 推送执行状态到画布

    消息类型:
      - init_state: 连接时初始快照
      - node_status: 节点状态变更（completed/failed/running）
      - tower_job_update: Tower 作业实时状态（含进度和 artifacts）
      - execution_completed: 执行完成/失败通知
    """

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

    async def tower_job_update(self, event):
        """接收 Tower 作业实时状态推送（来自 ansible_trigger.poll_job 内部）

        前端用此消息更新:
          - 节点颜色（pending→灰, running→黄, success→绿, failed→红）
          - 进度条（0~100）
          - 实时日志片段
          - artifacts 预览
        """
        await self.send_json({
            'type': 'tower_job_update',
            'node_id': event['node_id'],
            'tower_status': event['tower_status'],
            'bamboo_status': event['bamboo_status'],
            'progress': event.get('progress', 0),
            'artifacts': event.get('artifacts', {}),
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
