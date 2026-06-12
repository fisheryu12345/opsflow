# agent — 模块索引

> 上次自动更新: 2026-06-12

---

## `agent/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `setup.py` |  | Setup for opsflow-agent — pip installable agent client |

## `agent\agent/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | OpsFlow Agent — 远程执行代理客户端 |
| `executor.py` | Agent command executor — runs scripts/commands locally | `BackgroundExecutor` — 后台执行器 — 异步执行 + 实时回传<br>`execute_command()` — 执行命令并返回结果<br>`execute_script_file()` — 将脚本写入临时文件后执行（支持多种解释器） |
| `main.py` | Agent main entry — daemon process entry point | `AgentDaemon` — Agent 守护进程<br>`main()` — CLI 入口 |
| `ws_client.py` | Agent WebSocket client — connects to opsflow server, receives commands | `WSClient` — WebSocket 客户端 — 与服务端保持长连接 |
