from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue='er_execute')
def execute_pipeline_task(self, execution_id):
    """Celery 任务 — 异步执行 Pipeline"""
    from opsflow.models import FlowExecution
    from opsflow.core.flow_engine import FlowEngine
    try:
        execution = FlowExecution.objects.get(id=execution_id)
        engine = FlowEngine(execution)
        engine.run()
    except FlowExecution.DoesNotExist:
        pass
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(queue='er_execute')
def notify_node_status(execution_id, node_id, status, message=''):
    """Celery 任务 — 推送节点状态到 WebSocket"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'execution_{execution_id}',
        {
            'type': 'node_status',
            'node_id': node_id,
            'status': status,
            'message': message,
        }
    )
