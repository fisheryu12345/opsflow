import datetime
import logging

from opsflow.core.ansible_trigger import execute_atom

logger = logging.getLogger(__name__)


class FlowEngine:
    """流程执行引擎 — 驱动 Pipeline Tree 执行"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    def start(self):
        """启动执行，创建 Celery 任务"""
        self.execution.status = 'running'
        self.execution.started_at = datetime.datetime.now()
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task
        execute_pipeline_task.delay(self.execution.id)

    def run(self):
        """执行 Pipeline（由 Celery worker 调用）"""
        try:
            self._execute_nodes()
            self.execution.status = 'completed'
        except Exception as e:
            logger.exception("Pipeline 执行失败")
            self.execution.status = 'failed'
        self.execution.ended_at = datetime.datetime.now()
        self.execution.save()
        self._notify_completed()

    def resume(self):
        """恢复暂停的执行"""
        from opsflow.tasks import execute_pipeline_task
        execute_pipeline_task.delay(self.execution.id)

    def retry(self, node_id):
        """重试指定失败节点"""
        node_status = self.execution.node_status or {}
        node_status[node_id] = 'pending'
        self.execution.node_status = node_status
        self.execution.current_node = node_id
        self.execution.status = 'running'
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task
        execute_pipeline_task.delay(self.execution.id)

    def skip(self, node_id):
        """跳过指定节点"""
        node_status = self.execution.node_status or {}
        node_status[node_id] = 'skipped'
        self.execution.node_status = node_status
        self.execution.save()

    def _execute_nodes(self):
        """按拓扑顺序执行节点（简化版：从第一个节点开始）"""
        tree = self.template.pipeline_tree
        nodes = tree.get('nodes', [])
        node_map = {n['id']: n for n in nodes}

        def run_node(node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)

            node = node_map.get(node_id)
            if not node:
                return

            # 跳过已完成的节点
            current_status = (self.execution.node_status or {}).get(node_id)
            if current_status in ('completed', 'skipped'):
                for next_id in node.get('next_on_success', []):
                    run_node(next_id, visited)
                return

            self.execution.current_node = node_id
            node_status = self.execution.node_status or {}
            node_status[node_id] = 'running'
            self.execution.node_status = node_status
            self.execution.save()
            self._notify_node(node_id, 'running')

            try:
                result = execute_atom(node, self.template.target_hosts)
                node_status[node_id] = 'completed'
                self.execution.node_status = node_status
                self.execution.save()
                self._notify_node(node_id, 'completed')
                self._log_result(node, result)

                for next_id in node.get('next_on_success', []):
                    run_node(next_id, visited)
            except Exception as exc:
                node_status[node_id] = 'failed'
                self.execution.node_status = node_status
                self.execution.save()
                self._notify_node(node_id, 'failed')
                self._log_error(node, str(exc))

                for next_id in node.get('next_on_failure', []):
                    run_node(next_id, visited)

        if nodes:
            run_node(nodes[0]['id'])

    def _log_result(self, node, result):
        from opsflow.models import OpsLog
        OpsLog.objects.create(
            execution=self.execution,
            step=node.get('id', ''),
            command=str(node.get('params', {})),
            stdout=result.get('stdout', ''),
            stderr=result.get('stderr', ''),
            returncode=result.get('returncode', 0),
            risk_level=node.get('risk_level', 'low'),
        )

    def _log_error(self, node, error_msg):
        from opsflow.models import OpsLog
        OpsLog.objects.create(
            execution=self.execution,
            step=node.get('id', ''),
            command=str(node.get('params', {})),
            stderr=error_msg,
            returncode=-1,
            risk_level=node.get('risk_level', 'medium'),
        )

    def _notify_node(self, node_id, status):
        from opsflow.tasks import notify_node_status
        notify_node_status.delay(self.execution.id, node_id, status)

    def _notify_completed(self):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'execution_{self.execution.id}',
            {'type': 'execution.completed', 'status': self.execution.status}
        )
