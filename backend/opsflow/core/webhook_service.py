"""Webhook 回调服务 — 执行完成/失败时发送 HTTP 回调

参考 bk_sops gcloud/taskflow3/domains/callback.py TaskCallBacker

架构:
  1. signals/handlers.py COMPLETED/FAILED → WebhookService.dispatch()
  2. dispatch() 查询模板绑定的 WebhookConfig → 异步发送
  3. webhook_send 任务: POST + HMAC 签名 + Redis 幂等锁 + 重试
"""

import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 回调服务"""

    @staticmethod
    def dispatch(execution, event: str):
        """根据 execution 的模板查询 webhooks 配置，异步发送

        Args:
            execution: FlowExecution 实例（已保存，含 ID）
            event: 'completed' 或 'failed'
        """
        from opsflow.models import WebhookConfig

        webhooks = WebhookConfig.objects.filter(
            template=execution.template,
            enabled=True,
            trigger_events__contains=[event],
        )
        if not webhooks.exists():
            logger.debug("[Webhook] No webhooks configured for template %s event=%s",
                         execution.template_id, event)
            return

        for wh in webhooks:
            from opsflow.tasks import webhook_send
            webhook_send.delay(
                webhook_id=wh.id,
                execution_id=execution.id,
                event=event,
            )
            logger.info("[Webhook] Dispatched webhook '%s' (id=%s) for execution %s event=%s",
                        wh.name, wh.id, execution.id, event)

    @staticmethod
    def send(webhook_id: int, execution_id: int, event: str):
        """同步发送 webhook POST 请求

        Args:
            webhook_id: WebhookConfig ID
            execution_id: FlowExecution ID
            event: 'completed' 或 'failed'
        """
        from opsflow.models import WebhookConfig, WebhookLog, FlowExecution
        import requests

        try:
            wh = WebhookConfig.objects.get(id=webhook_id)
            execution = FlowExecution.objects.get(id=execution_id)
        except (WebhookConfig.DoesNotExist, FlowExecution.DoesNotExist):
            logger.error("[Webhook] webhook %s or execution %s not found",
                         webhook_id, execution_id)
            return

        # 构建请求体
        body = {
            'event': event,
            'execution_id': execution.id,
            'template_id': execution.template_id,
            'template_name': execution.template.name,
            'status': execution.status,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'ended_at': execution.ended_at.isoformat() if execution.ended_at else None,
        }

        # 创建发送日志
        log = WebhookLog.objects.create(
            webhook=wh,
            execution=execution,
            event=event,
            request_url=wh.url,
            request_body=body,
        )

        # 构建 headers
        headers = {'Content-Type': 'application/json'}
        if wh.secret:
            signature = WebhookService._sign(body, wh.secret)
            headers['X-OpsFlow-Signature'] = signature

        # 发送
        try:
            resp = requests.post(
                wh.url,
                json=body,
                headers=headers,
                timeout=30,
            )
            log.response_status = resp.status_code
            log.response_body = resp.text[:5000]  # 截断过长响应
            if resp.ok:
                log.status = WebhookLog.Status.SUCCESS
                logger.info("[Webhook] Sent to %s (status=%s)", wh.url, resp.status_code)
            else:
                log.status = WebhookLog.Status.FAILED
                log.error_message = f"HTTP {resp.status_code}"
                logger.warning("[Webhook] %s returned %s", wh.url, resp.status_code)
                # 触发重试
                if log.retry_count < wh.retry_count:
                    WebhookService._schedule_retry(log, wh)
        except requests.RequestException as e:
            log.status = WebhookLog.Status.FAILED
            log.error_message = str(e)
            logger.warning("[Webhook] Request to %s failed: %s", wh.url, e)
            if log.retry_count < wh.retry_count:
                WebhookService._schedule_retry(log, wh)

        log.save()

    @staticmethod
    def _sign(body: dict, secret: str) -> str:
        """HMAC-SHA256 签名"""
        payload = json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'), payload, hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _schedule_retry(log, wh):
        """安排重试"""
        from opsflow.tasks import webhook_send

        log.retry_count += 1
        log.save(update_fields=['retry_count'])

        webhook_send.apply_async(
            kwargs={
                'webhook_id': wh.id,
                'execution_id': log.execution_id,
                'event': log.event,
            },
            countdown=wh.retry_interval,
        )
        logger.info("[Webhook] Scheduled retry #%d for webhook %s in %ds",
                    log.retry_count, wh.name, wh.retry_interval)
