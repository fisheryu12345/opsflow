# backend/opsagent/management/commands/ops.py
from django.core.management.base import BaseCommand
import asyncio


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

        try:
            from conf.env import OPSAGENT_API_KEY, OPSAGENT_BASE_URL, OPSAGENT_MODEL
        except ImportError:
            OPSAGENT_API_KEY = ''
            OPSAGENT_BASE_URL = None
            OPSAGENT_MODEL = 'gpt-4o'

        api_key = options['api_key'] or os.environ.get('OPENAI_API_KEY') or OPSAGENT_API_KEY
        base_url = options['base_url'] or os.environ.get('OPENAI_BASE_URL') or OPSAGENT_BASE_URL
        model = options['model'] or os.environ.get('OPENAI_MODEL') or OPSAGENT_MODEL

        if not api_key:
            self.stderr.write(self.style.ERROR(
                "No API key configured. Set OPSAGENT_API_KEY in conf/env.py, "
                "or OPENAI_API_KEY env var, or use --api-key."
            ))
            return

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        client.model_name = model

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
