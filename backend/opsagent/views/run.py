import asyncio
import os
import re
import uuid
from typing import Optional

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openai import AsyncOpenAI

from opsagent.cli.repl import OpsREPL
from opsagent.core.types import AgentContext, RiskEnv
from opsagent.models import Session
from opsagent.serializers import TaskRunInputSerializer, TaskRunResultSerializer


class TaskRunViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskRunInputSerializer

    def create(self, request):
        ser = TaskRunInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_input = ser.validated_data['input']
        environment_id = ser.validated_data.get('environment_id')

        session_id = timezone.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]

        env_type = RiskEnv.DEVELOPMENT
        env_name = None
        if environment_id:
            from opsagent.models import EnvironmentContext
            try:
                env = EnvironmentContext.objects.get(id=environment_id, is_active=True)
                env_type = env.env_type
                env_name = env.name
            except EnvironmentContext.DoesNotExist:
                pass

        session = Session.objects.create(
            session_id=session_id,
            operator=request.user.username if request.user.is_authenticated else 'admin',
            mode='oneshot',
            status='active',
            task_status='running',
            user_input=user_input,
        )

        api_key: Optional[str] = None
        base_url: Optional[str] = None
        model_name: Optional[str] = None

        # 1) Try Integration Center AI connector first
        try:
            from integration.services.connector_service import get_ai_connector
            connector = get_ai_connector()
            if connector is not None:
                inst = connector.instance
                cfg = inst.config if inst else {}
                api_key = api_key or getattr(connector, '_load_credential', lambda: None)()
                base_url = base_url or cfg.get('api_base') or os.environ.get('OPENAI_BASE_URL')
                model_name = model_name or cfg.get('model') or os.environ.get('OPENAI_MODEL')
        except ImportError:
            pass

        # 2) Fallback to env vars / conf.env
        if not api_key:
            try:
                from conf.env import OPSAGENT_API_KEY, OPSAGENT_BASE_URL, OPSAGENT_MODEL
            except ImportError:
                OPSAGENT_API_KEY = ''
                OPSAGENT_BASE_URL = None
                OPSAGENT_MODEL = 'gpt-4o'
            api_key = os.environ.get('OPENAI_API_KEY') or OPSAGENT_API_KEY
            base_url = os.environ.get('OPENAI_BASE_URL') or OPSAGENT_BASE_URL
            model_name = os.environ.get('OPENAI_MODEL') or os.environ.get('OPENAI_MODEL_NAME') or OPSAGENT_MODEL

        if not api_key:
            raise ValueError(
                "No API key configured. Set up an AI connector in Integration Center, "
                "or set OPSAGENT_API_KEY in conf/env.py, or OPENAI_API_KEY env var."
            )

        # Strip 4-byte UTF-8 (emoji etc.) to avoid MySQL utf8mb4 connection issues
        def _sanitize(text: str) -> str:
            return re.sub(r'[\U00010000-\U0010FFFF]', '', text) if text else ''

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        client.model_name = model_name or 'gpt-4o'

        try:
            tool_calls_log = []

            ctx = AgentContext(
                session_id=session_id,
                operator=request.user.username,
                environment_name=env_name,
                env_type=env_type,
            )

            def on_tool(name, args, assessment):
                tool_calls_log.append({
                    'tool_name': name,
                    'arguments': args,
                    'assessment': {
                        'score': assessment.score,
                        'decision': assessment.decision.value,
                        'reason': assessment.reason,
                    },
                    'status': 'running',
                    'result': None,
                    'error': None,
                })

            async def on_approval(name, args, assessment):
                return True

            def on_response(text):
                nonlocal final_output
                final_output['text'] = text

            final_output = {'text': ''}

            repl = OpsREPL(llm_client=client)
            result_text = asyncio.run(repl.agent.run(
                user_input, ctx,
                on_tool_call=on_tool,
                on_approval_needed=on_approval,
                on_response=on_response,
            ))

            session.summary = _sanitize(result_text[:2000])
            session.result_json = {
                'tool_calls': tool_calls_log,
                'final_output': _sanitize(result_text),
            }
            session.status = 'completed'
            session.task_status = 'completed'
            session.ended_at = timezone.now()
            session.save()

            result_ser = TaskRunResultSerializer(instance={
                'session_id': session_id,
                'user_input': user_input,
                'output': result_text,
                'status': 'completed',
                'tool_calls': tool_calls_log,
            })
            return Response({'code': 2000, 'msg': 'success', 'data': result_ser.data})

        except Exception as exc:
            session.status = 'aborted'
            session.task_status = 'failed'
            session.result_json = {'error': str(exc)}
            session.ended_at = timezone.now()
            session.save()
            return Response(
                {'code': 4000, 'msg': f'Execution failed: {exc}', 'data': None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, pk=None):
        try:
            session = Session.objects.get(session_id=pk)
        except Session.DoesNotExist:
            return Response(
                {'code': 4000, 'msg': 'Session not found', 'data': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        tool_calls = session.result_json.get('tool_calls', []) if session.result_json else []
        final_output = session.result_json.get('final_output', '') if session.result_json else ''

        result_ser = TaskRunResultSerializer(instance={
            'session_id': session.session_id,
            'user_input': session.user_input,
            'output': final_output,
            'status': session.task_status,
            'tool_calls': tool_calls,
        })
        return Response({'code': 2000, 'msg': 'success', 'data': result_ser.data})
