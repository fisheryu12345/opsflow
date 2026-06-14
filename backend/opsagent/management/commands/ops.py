# backend/opsagent/management/commands/ops.py
from django.core.management.base import BaseCommand
import asyncio
from typing import Optional


class Command(BaseCommand):
    help = 'OpsAgent — LLM-driven IT operations CLI'

    def add_arguments(self, parser):
        parser.add_argument('--run', type=str, help='One-shot: execute a single query and exit')
        parser.add_argument('--yes', action='store_true', help='Auto-approve all operations')
        parser.add_argument('--model', type=str, default=None, help='LLM model name')
        parser.add_argument('--api-key', type=str, help='OpenAI API key (or set OPENAI_API_KEY env var)')
        parser.add_argument('--base-url', type=str, help='OpenAI-compatible API base URL')

    def handle(self, *args, **options):
        import os
        from openai import AsyncOpenAI
        from opsagent.cli.repl import OpsREPL
        from integration.services.connector_service import get_ai_connector

        api_key: Optional[str] = options.get('api_key')
        base_url: Optional[str] = options.get('base_url')
        model: Optional[str] = options.get('model')

        # 1) Try Integration Center AI connector first
        if not api_key:
            connector = get_ai_connector()
            if connector is not None:
                inst = connector.instance
                cfg = inst.config if inst else {}
                api_key = api_key or getattr(connector, '_load_credential', lambda: None)()
                base_url = base_url or cfg.get('api_base') or os.environ.get('OPENAI_BASE_URL')
                model = model or cfg.get('model') or os.environ.get('OPENAI_MODEL')

        # 2) CLI args override
        api_key = options.get('api_key') or api_key
        base_url = options.get('base_url') or base_url
        model = options.get('model') or model

        if not api_key:
            self.stderr.write(self.style.ERROR(
                "No API key configured. Set up an AI connector in Integration Center."
            ))
            return

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        client.model_name = model or 'gpt-4o'

        repl = OpsREPL(llm_client=client)

        if options['run']:
            try:
                result = asyncio.run(repl.run_once(options['run'], auto_approve=options['yes']))
                self.stdout.write(self.style.SUCCESS("Done."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error: {e}"))
        else:
            try:
                asyncio.run(repl.repl_loop())
            except KeyboardInterrupt:
                self.stdout.write("\nExiting.")
