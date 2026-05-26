# backend/opsagent/cli/repl.py
import asyncio
import datetime
from opsagent.core.agent_loop import AgentLoop
from opsagent.core.context import ContextManager
from opsagent.core.types import AgentContext, RiskEnv
from opsagent.tools import auto_discover


class OpsREPL:
    def __init__(self, llm_client, ctx_manager: ContextManager | None = None):
        auto_discover()
        self.llm = llm_client
        self.ctx_manager = ctx_manager or ContextManager()
        self.agent = AgentLoop(llm_client=llm_client, context_manager=self.ctx_manager)
        self.history: list[dict] = []
        self.current_env: str | None = None

    def banner(self) -> str:
        from opsagent.cli.render import c
        return "\n".join([
            "",
            c("  ██████╗ ██████╗ ███████╗", "cyan"),
            c("  ╚════██╗██╔═══██╗██╔════╝", "cyan"),
            c("   █████╔╝██████╔╝███████╗", "cyan"),
            c("  ╚═══██╗██╔═══╝ ╚════██║", "cyan"),
            c("  ██████╔╝██║     ███████║", "cyan"),
            c("   ╚═════╝ ╚═╝     ╚══════╝", "cyan"),
            "",
            f"  Environment: {self.current_env or '(none)'}",
            f"  Session: {datetime.datetime.now().strftime('%Y-%m-%d-%H%M')}",
            "",
        ])

    async def run_once(self, user_input: str, auto_approve: bool = False) -> str:
        from opsagent.cli.render import tool_call_banner, tool_result_banner, approval_prompt

        ctx = AgentContext(
            session_id=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            operator="admin",
            environment_name=self.current_env,
        )

        tool_results = []

        def on_tool(name, args, assessment):
            print(tool_call_banner(name, args, assessment))

        async def on_approval(name, args, assessment):
            if auto_approve:
                return True
            print(approval_prompt(name, args, assessment))
            try:
                return input().strip().lower() == 'y'
            except (EOFError, KeyboardInterrupt):
                return False

        def on_response(text):
            print(f"\n{text}")

        result = await self.agent.run(
            user_input, ctx, history=self.history,
            on_tool_call=on_tool,
            on_approval_needed=on_approval,
            on_response=on_response,
        )
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": result})
        return result

    async def repl_loop(self):
        print(self.banner())
        while True:
            try:
                user_input = input("ops> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not user_input:
                continue
            if user_input.lower() in ('exit', 'quit', 'q'):
                break

            await self.run_once(user_input)
