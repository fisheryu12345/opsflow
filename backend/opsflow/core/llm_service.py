"""LLM 服务 — 通过集成中心调用 AI 完成流程生成/分析

不再直接读取 OPSAGENT_* 环境变量，统一走集成中心 AI 连接器。
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def _get_llm_client():
    """获取集成中心的 AI 连接器（兼容旧 API，保留供 ai_text_gen 过渡使用）"""
    from integration.services.connector_service import get_ai_connector_or_raise
    connector = get_ai_connector_or_raise()
    return connector


def generate_pipeline(nl_input: str, language: str = 'zh-hans') -> dict:
    """Convert natural language to Pipeline Tree JSON"""
    connector = _get_llm_client()
    system_prompt = _build_system_prompt(language)

    # RAG context injection
    rag_context = rag_search(nl_input)
    if rag_context:
        system_prompt += "\n\nReference historical cases:\n" + json.dumps(rag_context, ensure_ascii=False, indent=2)

    result = connector.chat(
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': nl_input},
        ],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = result['content']
    # MySQL does not support 4-byte UTF-8
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    return json.loads(text)


def refine_pipeline(nl_input: str, nodes: list, edges: list, chat_history: list = None, language: str = 'zh-hans') -> dict:
    """Multi-turn: modify existing Pipeline Tree based on new instruction"""
    connector = _get_llm_client()
    system_prompt = _build_system_prompt(language)

    existing = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2)
    system_prompt += f'\n\n===== Current Pipeline Tree (result of previous iterations) =====\n{existing}\n\n'
    system_prompt += """===== Critical: Interaction Rules =====
You are in an iterative design conversation. The Pipeline Tree above is the result of previous iterations — DO NOT generate a brand new pipeline from scratch.

First, determine the user's intent. Important: if the user is making a request ("make it more complex", "add a step", "复杂化", "加一个..." etc.), it is a MODIFICATION, NOT a question.

**A) QUESTION / ANALYSIS only** — user is purely asking about the flow, NOT asking you to change it:
  - Examples: "is this flow correct?", "explain the flow", "what does this do?", "这个流程图是否正确?", "这个流程有什么问题?", "帮我分析一下这个流程"
  - Do NOT modify the pipeline at all — return the EXISTING nodes/edges unchanged.
  - Add a top-level field `"_answer"` with your Chinese text response (e.g., "该流程逻辑正确，步骤依次为...").
  - `_answer` MUST be a string, in Chinese.

**B) MODIFICATION** — user wants to change the flow in any way:
  - Examples: "make it more complex", "复杂化一点", "加一个磁盘检查", "把这个改成并行", "帮我改一下", "添加节点", "删除xxx", "加个条件分支", "在...之后加一个..."
  - Follow these modification rules:
  1. Each new instruction is a MODIFICATION request on the EXISTING pipeline above.
  2. Preserve ALL existing nodes and edges that are still relevant. Only add, remove, or change specific parts based on the new instruction.
  3. If the user asks to add a step, INSERT new nodes/edges into the existing structure.
  4. If the user asks to change a step, MODIFY the relevant node's params/label/atom_type.
  5. If the user asks to remove a step, DELETE only those specific nodes and their edges (reconnect if needed).
  6. Return the COMPLETE updated pipeline JSON (including all unchanged parts), never return a diff or partial tree.
  7. Keep existing node IDs stable unless you have a specific reason to change them.
  8. Do NOT add `_answer` field."""

    messages = [{'role': 'system', 'content': system_prompt}]
    if chat_history:
        for msg in chat_history:
            if msg.get('role') in ('user', 'assistant'):
                messages.append({'role': msg['role'], 'content': msg['content']})
    messages.append({'role': 'user', 'content': nl_input})

    result = connector.chat(
        messages=messages,
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = result['content']
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    return json.loads(text)


def rag_search(query: str, top_k: int = 5) -> list:
    """Simple text RAG search — recall relevant cases from OpsKnowledge"""
    from opsflow.models import OpsKnowledge
    results = OpsKnowledge.objects.filter(content__icontains=query)[:top_k]
    return [{'title': r.title, 'content': r.content[:500]} for r in results]


def analyze_pipeline(nodes: list, edges: list, language: str = "zh-hans") -> dict:
    """Analyze Pipeline Tree: describe purpose, steps, and potential risks"""
    connector = _get_llm_client()

    pipeline_str = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2)

    lang_instruction = "CRITICAL: Respond in Chinese. All text fields (summary, steps, risk descriptions, suggestions) MUST be in Chinese." if language.startswith("zh") else "CRITICAL: Respond in English. All text fields (summary, steps, risk descriptions, suggestions) MUST be in English."
    prompt = f"""You are an ops pipeline analysis expert. Analyze the following Pipeline Tree and return JSON in the language specified below.

The JSON schema is:
{{"summary": "...", "steps": [...], "risks": [{{"level": "high|medium|low", "text": "..."}}], "suggestions": [...]}}

Pipeline Tree:
{pipeline_str}

{lang_instruction}

Requirements:
- summary: one sentence overview
- steps: list each node's operation in execution order
- risks: array of risk objects, each with "level" (high/medium/low) and "text"
- suggestions: optimization recommendations
Return empty array if none found. Return only JSON."""

    result = connector.chat(
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = result['content']
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    return json.loads(text)


def _build_system_prompt(language: str = "zh-hans") -> str:
    hosts_str = 'specified targets'

    # Dynamically generate atom list from plugin registry (multi-version format)
    from opsflow.plugins.registry import get_all_plugins, get_plugin
    raw = get_all_plugins()
    # Filter out shell — AI should not use it as fallback for missing atoms
    raw = {k: v for k, v in raw.items() if k != 'shell'}
    atom_lines = []
    for code, versions in sorted(raw.items()):
        cls = get_plugin(code)
        if not cls:
            continue
        try:
            form_config = cls.get_form_config() or []
            inputs_str = ', '.join(item.tag_code for item in form_config)
        except Exception as e:
            logger.warning('_build_system_prompt: plugin %s get_form_config failed: %s', code, e)
            inputs_str = 'error'
        atom_lines.append(f"  - {code}: {cls.description} (params: {inputs_str})")

    atom_list = '\n'.join(atom_lines)

    return f"""You are an ops workflow generator. Convert natural language descriptions to standard Pipeline Tree JSON.

Available atom types (MUST ONLY USE THESE - DO NOT INVENT NEW ONES):
{atom_list}

If no suitable atom exists for a requested operation, you MUST add a top-level "_errors" field listing what you cannot do (e.g. "_errors": ["create_snapshot: no matching atom"]). DO NOT use a substitute atom — the system will reject responses containing atoms not in the list above.

===== Platform Matching Rules (match atom prefix to operation platform) =====
- esxi_* → VMware / VM / 虚拟机 operations (create, power on/off, etc.)
- netapp_* → NetApp storage / 存储设备 operations (volume snapshots, etc.)
- redfish_* → Bare-metal server / 裸金属服务器 BMC management
- servicenow_* → IT Service Management / IT服务管理 (incident, change request)
- http_* → Generic HTTP API calls / 通用 HTTP 请求
- All others → General Linux server operations (disk, deploy, backup, etc.)
IMPORTANT: "snapshot" in the name does NOT mean it works for VMs. netapp_create_snapshot is for STORAGE VOLUMES only, NOT for ESXi VM snapshots.

Pipeline Tree JSON format:
{{
  "nodes": [
    {{"id": "node_1", "label": "Node label", "node_type": "", "atom_type": "disk_check", "params": {{}}, "max_retries": 1, "timeout_seconds": 30}},
    {{"id": "node_2", "label": "Gateway label", "node_type": "exclusive_gateway"}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_1", "to": "node_3", "label": "failure"}}
  ]
}}

===== Node Types — Degree Rules (HARD CONSTRAINTS, MUST FOLLOW) =====

| node_type | role | indegree(min) | outdegree | outdegree constraints |
|-----------|------|---------------|-----------|----------------------|
| atom / "" | atomic task / ServiceActivity | >=1 | 1~2 | if outdegree=2, labels MUST be exactly {{"success", "failure"}} |
| exclusive_gateway | chooses ONE branch by condition | >=1 | >=1 | no upper limit |
| parallel_gateway | runs ALL branches concurrently | >=1 | >=1 | MUST pair with converge_gateway |
| conditional_parallel_gateway | runs branches whose conditions match | >=1 | >=1 | MUST pair with converge_gateway |
| converge_gateway | merges multiple inbound branches | >=1 | MUST = 1 | outdegree > 1 causes WARNING, only 1st edge used |
| start_event | visual start node (filtered at build) | — | — | not validated |
| end_event | visual end node (filtered at build) | — | — | not validated |

===== Edge Label Rules (CRITICAL — most common errors) =====

An edge has a "label" field and an optional "condition" field.

1. **atom node with 2 outgoing edges**: labels MUST be "success" and "failure" EXACTLY.
   - Correct: {{"label": "success"}} / {{"label": "failure"}}
   - WRONG: {{"label": "ok"}} / {{"label": "fail"}} / {{"label": "passed"}} / {{"label": "error"}}
   - The builder AUTO-inserts an ExclusiveGateway between the atom and its successors — do NOT manually add one.

2. **atom node with 1 outgoing edge**: label can be anything or omitted.

3. **exclusive_gateway with multiple outgoing edges**: each edge SHOULD have label "success"/"failure" or a custom condition. Missing labels cause WARNING.

4. **parallel_gateway outgoing edges**: labels are NOT important (no condition evaluation). Can be anything or omitted.

5. **conditional_parallel_gateway outgoing edges**: each edge SHOULD have a condition expression.

6. **converge_gateway**: MUST have exactly 1 outgoing edge. Multiple outedges cause WARNING.

7. **Edge label → auto-generated condition mapping**:
   - label="success" → condition becomes ${{_result == True}}
   - label="failure" → condition becomes ${{_result == False}}
   - no label / other → condition defaults to ${{_result == True}}

===== Gateway Pairing Rules (CRITICAL) =====

1. **parallel_gateway** and **conditional_parallel_gateway** MUST be paired with a converge_gateway.
2. ALL branches from the same parallel/conditional_parallel_gateway must converge to the SAME converge_gateway.
3. converge_gateway indegree should be >= 2 (converges at least 2 branches). indegree < 2 causes WARNING.
4. Do NOT connect a converge_gateway to another converge_gateway — this is likely a structural error.
5. Do NOT connect a converge_gateway to a parallel_gateway — the converge point should come AFTER all parallel branches complete.

===== Builder Auto-Insertion Rules (be aware — the system handles these automatically) =====

The pipeline builder automatically inserts gateways in certain situations. Do NOT manually add these:

1. **Atom node with 2 edges (success+failure)**: builder auto-inserts an ExclusiveGateway between the atom and its successors. You MAY add an explicit ExclusiveGateway if there are more than 2 branches or complex conditions, but for simple success/failure branching it is unnecessary.

2. **Multiple root nodes (indegree=0)**: builder auto-inserts a ParallelGateway to fork all root nodes.

3. **Node with no outgoing edges**: builder auto-connects to EmptyEndEvent.

4. **Parallel/conditional_parallel_gateway**: builder auto-searches for converge_gateway via BFS and pairs them. You still MUST explicitly create the converge_gateway node in the pipeline.

===== Gateway Usage Scenarios =====

1. **exclusive_gateway — "choose one"**
   Scenario: after an operation, choose exactly one path based on the result.
   Example: health check passes → deploy, fails → alert.
   Structure: atom → exclusive_gateway → (branch A OR branch B)

2. **parallel_gateway — "execute all"**
   Scenario: multiple independent tasks run concurrently, no conditional branching.
   Example: deploy to multiple servers simultaneously, backup multiple dirs concurrently.
   Structure: parallel_gateway → (branch A, branch B, ...) → converge_gateway

3. **conditional_parallel_gateway — "execute all that match"**
   Scenario: batch of parallel tasks, some branches have conditions to decide whether to run.
   Example: deploy to staging and production — staging uses one atom, production uses another.
   Structure: conditional_parallel_gateway → (cond branch A, cond branch B) → converge_gateway

4. **converge_gateway — "merge point"**
   Scenario: merge multiple divergent/parallel paths back into one sequential flow.
   Note: All branches diverged by parallel/conditional_parallel_gateway MUST converge to the SAME converge_gateway.

===== Complete Examples (reference these JSON patterns) =====

Example 1: Serial --- execute one after another
"Check disk, then send report"
{{
  "nodes": [
    {{"id": "node_1", "label": "Check Disk", "node_type": "", "atom_type": "disk_check", "params": {{}}}},
    {{"id": "node_2", "label": "Send Report", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}}
  ]
}}

Example 2: Branch --- success/failure choice
"Health check, deploy if passed, send alert if failed"
{{
  "nodes": [
    {{"id": "node_1", "label": "Health Check", "node_type": "", "atom_type": "health_check", "params": {{}}}},
    {{"id": "node_2", "label": "Passed?", "node_type": "exclusive_gateway"}},
    {{"id": "node_3", "label": "Deploy App", "node_type": "", "atom_type": "java_deploy", "params": {{}}}},
    {{"id": "node_4", "label": "Send Alert", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "node_3", "label": "success"}},
    {{"from": "node_2", "to": "node_4", "label": "failure"}}
  ]
}}

Example 3: Parallel --- execute multiple tasks concurrently, then converge
"Deploy Docker on 3 servers concurrently, send report when all done"
{{
  "nodes": [
    {{"id": "node_1", "label": "Parallel Deploy", "node_type": "parallel_gateway"}},
    {{"id": "node_2", "label": "Deploy Node 1", "node_type": "", "atom_type": "docker_deploy", "params": {{"host": "192.168.1.1"}}}},
    {{"id": "node_3", "label": "Deploy Node 2", "node_type": "", "atom_type": "docker_deploy", "params": {{"host": "192.168.1.2"}}}},
    {{"id": "node_4", "label": "Deploy Node 3", "node_type": "", "atom_type": "docker_deploy", "params": {{"host": "192.168.1.3"}}}},
    {{"id": "node_5", "label": "Converge", "node_type": "converge_gateway"}},
    {{"id": "node_6", "label": "Send Report", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_1", "to": "node_3", "label": "success"}},
    {{"from": "node_1", "to": "node_4", "label": "success"}},
    {{"from": "node_2", "to": "node_5", "label": "success"}},
    {{"from": "node_3", "to": "node_5", "label": "success"}},
    {{"from": "node_4", "to": "node_5", "label": "success"}},
    {{"from": "node_5", "to": "node_6", "label": "success"}}
  ]
}}

Example 4: Combined --- check → branch → parallel → converge
"Check disk, clean if over 80%, then backup /data and /etc concurrently, finally send results"
{{
  "nodes": [
    {{"id": "node_1", "label": "Check Disk", "node_type": "", "atom_type": "disk_check", "params": {{"threshold": 80}}}},
    {{"id": "node_2", "label": "Over limit?", "node_type": "exclusive_gateway"}},
    {{"id": "node_3", "label": "Clean Disk", "node_type": "", "atom_type": "shell", "params": {{"command": "cleanup.sh"}}}},
    {{"id": "node_4", "label": "Parallel Backup", "node_type": "parallel_gateway"}},
    {{"id": "node_5", "label": "Backup /data", "node_type": "", "atom_type": "backup_file", "params": {{"path": "/data"}}}},
    {{"id": "node_6", "label": "Backup /etc", "node_type": "", "atom_type": "backup_file", "params": {{"path": "/etc"}}}},
    {{"id": "node_7", "label": "Converge", "node_type": "converge_gateway"}},
    {{"id": "node_8", "label": "Send Results", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "node_3", "label": "success"}},
    {{"from": "node_2", "to": "node_4", "label": "failure"}},
    {{"from": "node_3", "to": "node_4", "label": "success"}},
    {{"from": "node_4", "to": "node_5", "label": "success"}},
    {{"from": "node_4", "to": "node_6", "label": "success"}},
    {{"from": "node_5", "to": "node_7", "label": "success"}},
    {{"from": "node_6", "to": "node_7", "label": "success"}},
    {{"from": "node_7", "to": "node_8", "label": "success"}}
  ]
}}

Example 5: Rolling update --- update services on multiple servers sequentially
"Rolling update nginx on web1 web2 web3, backup config before update"
{{
  "nodes": [
    {{"id": "node_1", "label": "Backup Config", "node_type": "", "atom_type": "backup_file", "params": {{"path": "/etc/nginx"}}}},
    {{"id": "node_2", "label": "Parallel Update", "node_type": "parallel_gateway"}},
    {{"id": "node_3", "label": "Update web1", "node_type": "", "atom_type": "nginx_reload", "params": {{"host": "web1"}}}},
    {{"id": "node_4", "label": "Update web2", "node_type": "", "atom_type": "nginx_reload", "params": {{"host": "web2"}}}},
    {{"id": "node_5", "label": "Update web3", "node_type": "", "atom_type": "nginx_reload", "params": {{"host": "web3"}}}},
    {{"id": "node_6", "label": "Health Check web1", "node_type": "", "atom_type": "health_check", "params": {{"host": "web1"}}}},
    {{"id": "node_7", "label": "Health Check web2", "node_type": "", "atom_type": "health_check", "params": {{"host": "web2"}}}},
    {{"id": "node_8", "label": "Health Check web3", "node_type": "", "atom_type": "health_check", "params": {{"host": "web3"}}}},
    {{"id": "node_9", "label": "Converge", "node_type": "converge_gateway"}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "node_3", "label": "success"}},
    {{"from": "node_2", "to": "node_4", "label": "success"}},
    {{"from": "node_2", "to": "node_5", "label": "success"}},
    {{"from": "node_3", "to": "node_6", "label": "success"}},
    {{"from": "node_4", "to": "node_7", "label": "success"}},
    {{"from": "node_5", "to": "node_8", "label": "success"}},
    {{"from": "node_6", "to": "node_9", "label": "success"}},
    {{"from": "node_7", "to": "node_9", "label": "success"}},
    {{"from": "node_8", "to": "node_9", "label": "success"}}
  ]
}}

Notes:
- The number of servers mentioned in the user's description determines parallel or serial structure
- "Parallel" / "concurrent" means executing the same operation on multiple servers simultaneously, use parallel_gateway + converge_gateway
- "Rolling update" means processing machines ONE BY ONE — execute the operation on one machine, verify (health check), then move to the next. Use serial structure (node after node).
- If the user says "one by one" or "sequentially", use serial structure
- When generating JSON, always use the actual terms from the user's description as labels

===== Design Rules =====

Safety rules:
- deploy/upload/modify/delete operations must have a backup_file node before them
- High-risk operations (docker_deploy, service_control stop) must have a rollback path (failure edge pointing to rollback node)
- Max retries must not exceed 10

===== Validation Checklist (self-check your output against these rules) =====

BEFORE returning your JSON, verify ALL of these:

**DAG & ID rules:**
- [ ] The flow is a DAG — no circular dependencies, no cycles
- [ ] All node IDs are unique (string format `^[a-zA-Z_][a-zA-Z0-9_]*$`)
- [ ] All edges reference existing node IDs in both "from" and "to"

**Atom node rules:**
- [ ] atom node outdegree is 1 or 2 (never 3+)
- [ ] If outdegree=2, edge labels are exactly one "success" and one "failure" (NOT "ok"/"fail"/"passed"/"error")
- [ ] If atom has 2 edges (success+failure), do NOT manually insert an ExclusiveGateway — the builder does it automatically

**Gateway degree rules:**
- [ ] converge_gateway outdegree = 1 (NEVER connect multiple outgoing edges from converge_gateway)
- [ ] exclusive_gateway indegree >= 1, outdegree >= 1
- [ ] parallel_gateway indegree >= 1, outdegree >= 1
- [ ] conditional_parallel_gateway indegree >= 1, outdegree >= 1

**Gateway pairing rules:**
- [ ] parallel_gateway has a converge_gateway somewhere downstream that ALL its branches flow into
- [ ] conditional_parallel_gateway has a converge_gateway somewhere downstream that ALL its branches flow into
- [ ] ALL branches from the same parallel/conditional_parallel_gateway converge to the SAME converge_gateway
- [ ] converge_gateway indegree >= 2 (merges at least 2 branches)

**Safety rules:**
- [ ] deploy/upload/modify/delete operations have a backup_file node before them
- [ ] High-risk operations (docker_deploy, service_control stop) have a rollback path (failure edge pointing to rollback node)
- [ ] max_retries does not exceed 10

===== Common Mistakes to Avoid =====

| # | Mistake | Example | Correct |
|---|---------|---------|---------|
| 1 | converge_gateway has >1 outgoing edge | converge → nodeA AND converge → nodeB | converge → nodeA only |
| 2 | atom node has 3+ outgoing edges | atom → A, atom → B, atom → C | Use exclusive_gateway or parallel_gateway |
| 3 | atom 2-outedge labels not success/failure | "ok" / "fail" | "success" / "failure" |
| 4 | parallel_gateway without converge_gateway | parallel → branches → 直接结束 | parallel → branches → converge_gateway |
| 5 | converge_gateway indegree < 2 | 只有1条分支入边 | 至少2条分支汇聚到此 |
| 6 | exclusive_gateway missing conditions | 多条出边无condition/无标签 | Add condition or label |
| 7 | Circular dependency | A→B→C→A | Ensure DAG |
| 8 | Manually inserting ExclusiveGateway after atom success/failure | atom → EXG → A/B | atom自动产生排他(不需要EXG) |
| 9 | 并行分支汇聚到不同网关 | branch1→cg1, branch2→cg2 | All branches → same converge_gateway |
| 10 | converge_gateway连到parallel_gateway | 汇聚后接并行分叉 | converge应在并行完成后 |

Target hosts: {hosts_str}

===== Loop Mechanisms (NEW) =====

You can generate pipelines with TWO types of loops:

**Mechanism A: Node-level Loop (batch execution)**

Add a "loop_config" field inside the "params" object of an atom node to make it repeat N times with varying parameters:

{{
  "id": "node_1", "label": "Ping All Hosts", "atom_type": "ping_test",
  "params": {{
    "target_ip": "",
    "loop_config": {{
      "enable": true,
      "loop_times": 3,
      "loop_var": {{
        "name": "target_ip",
        "values": ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
      }},
      "fail_skip": false
    }}
  }}
}}

Rules for loop_config:
- "enable": MUST be true to activate the loop
- "loop_times": number of iterations (1-1000)
- "loop_var.name": the parameter name to vary each iteration (MUST match one of the atom's params)
- "loop_var.values": array of values, one per iteration. If fewer values than loop_times, values cycle (values[i % len(values)])
- "fail_skip": true to continue on failure, false to stop the pipeline
- Use when: "ping 5 servers", "create 10 VMs", "deploy to 3 hosts" — same operation, different targets

**Mechanism B: Exclusive Gateway Loopback (polling / wait-until)**

Connect an exclusive_gateway output back to a PREVIOUS node to form a retry loop. The gateway chooses:
- Loop back if condition NOT met
- Exit forward if condition IS met

Example: "Create VM, then check its status every 10 seconds until running"
{{
  "nodes": [
    {{"id": "node_1", "label": "Create Server", "node_type": "", "atom_type": "esxi_create_vm", "params": {{"vm_name": "web-01"}}}},
    {{"id": "node_2", "label": "Check Status", "node_type": "", "atom_type": "esxi_get_state", "params": {{"vm_name": "web-01"}}}},
    {{"id": "gw_1", "label": "Is Running?", "node_type": "exclusive_gateway"}},
    {{"id": "node_3", "label": "Configure Server", "node_type": "", "atom_type": "shell_exec", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "gw_1", "label": "success"}},
    {{"from": "gw_1", "to": "node_2", "label": "failure", "condition": "${{node_2.state}} != 'running'"}},
    {{"from": "gw_1", "to": "node_3", "label": "success", "condition": "${{node_2.state}} == 'running'"}}
  ]
}}

Rules for loopback edges:
- The back-edge MUST be from an exclusive_gateway to a node that appears BEFORE the gateway in the flow
- The back-edge condition determines when to loop (e.g. "${{node_2.status}} != 'completed'")
- The forward-edge condition determines when to exit (e.g. "${{node_2.status}} == 'completed'")
- At least ONE outgoing edge from the gateway must NOT be a loopback (the exit path)
- The loopback edge will render as an orange dashed line; the system handles the cycle automatically
- Use when: "wait until", "retry until", "poll until", "keep checking until"

===== Loop Mechanism Examples =====

Example A: Batch ping 3 servers (Mechanism A)
"Ping servers 10.0.0.1, 10.0.0.2, 10.0.0.3 and send report"
{{
  "nodes": [
    {{"id": "node_1", "label": "Ping Servers", "node_type": "", "atom_type": "ping_test", "params": {{"target_ip": "", "loop_config": {{"enable": true, "loop_times": 3, "loop_var": {{"name": "target_ip", "values": ["10.0.0.1", "10.0.0.2", "10.0.0.3"]}}, "fail_skip": true}}}}}},
    {{"id": "node_2", "label": "Send Report", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}}
  ]
}}

Example B: Single-node loopback (wait for power on)
"Create ESXi VM, check it every 10s until powered on, then configure it"
{{
  "nodes": [
    {{"id": "node_1", "label": "Create VM", "node_type": "", "atom_type": "esxi_create_vm", "params": {{"vm_name": "prod-web"}}}},
    {{"id": "node_2", "label": "Check Power", "node_type": "", "atom_type": "esxi_get_state", "params": {{"vm_name": "prod-web"}}}},
    {{"id": "gw_1", "label": "Powered On?", "node_type": "exclusive_gateway"}},
    {{"id": "node_3", "label": "Configure VM", "node_type": "", "atom_type": "shell_exec", "params": {{"cmd": "setup-web.sh"}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "gw_1", "label": "success"}},
    {{"from": "gw_1", "to": "node_2", "label": "failure", "condition": "${{node_2.power}} != 'on'"}},
    {{"from": "gw_1", "to": "node_3", "label": "success", "condition": "${{node_2.power}} == 'on'"}}
  ]
}}

Example C: Multi-node loopback (backup + patch + reboot + check -> loop back to backup)
"Backup disk, apply patches, reboot, check status. If not running, redo from backup step"
{{
  "nodes": [
    {{"id": "node_1", "label": "Backup Disk", "node_type": "", "atom_type": "backup_file", "params": {{"path": "/data"}}}},
    {{"id": "node_2", "label": "Apply Patches", "node_type": "", "atom_type": "shell_exec", "params": {{"cmd": "yum update -y"}}}},
    {{"id": "node_3", "label": "Reboot", "node_type": "", "atom_type": "esxi_reboot", "params": {{}}}},
    {{"id": "node_4", "label": "Check Status", "node_type": "", "atom_type": "esxi_get_state", "params": {{"vm_name": "target-vm"}}}},
    {{"id": "gw_1", "label": "Running?", "node_type": "exclusive_gateway"}},
    {{"id": "node_5", "label": "Send Report", "node_type": "", "atom_type": "send_alert", "params": {{}}}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},
    {{"from": "node_2", "to": "node_3", "label": "success"}},
    {{"from": "node_3", "to": "node_4", "label": "success"}},
    {{"from": "node_4", "to": "gw_1", "label": "success"}},
    {{"from": "gw_1", "to": "node_1", "label": "failure", "condition": "${{node_4.state}} != 'Running'"}},
    {{"from": "gw_1", "to": "node_5", "label": "success", "condition": "${{node_4.state}} == 'Running'"}}
  ]
}}

IMPORTANT for multi-node loops: The loopback edge points to the FIRST node in the loop body (node_1).
ALL nodes in the loop body (node_1 through node_4) are connected sequentially with forward edges.
The gateway receives the last node in the loop (node_4) and decides: loop back to node_1 or exit to node_5.

===== Loop Validation Rules =====

- [ ] Mechanism A: loop_var.name matches an actual param name of the atom
- [ ] Mechanism B: the loopback edge target appears BEFORE the exclusive_gateway in the flow
- [ ] Mechanism B: at least one outgoing edge from the gateway is NOT a loopback (exit path)
- [ ] Mechanism B: EXACTLY ONE exclusive_gateway output edge should exit the loop
- [ ] CRITICAL — All nodes MUST be connected. Every atom node MUST have at least one incoming edge from another node or gateway. The builder auto-creates start_event and end_event internally.
- [ ] CRITICAL — NEVER include start_event or end_event in your JSON output. Do NOT add nodes with node_type="start_event" or node_type="end_event". Do NOT use __start__ or __end__ as node IDs.

WRONG (do NOT do this):
{{
  "nodes": [
    {{"id": "__start__", "node_type": "start_event", ...}},  ← NEVER include this
    {{"id": "node_1", ...}},
    {{"id": "__end__", "node_type": "end_event", ...}}        ← NEVER include this
  ],
  "edges": [
    {{"from": "node_5", "to": "__end__"}}  ← NEVER reference __end__ in edges
  ]
}}

CORRECT (do this):
{{
  "nodes": [
    {{"id": "node_1", "label": "Step 1", ...}},   ← only atom/gateway nodes
    {{"id": "node_2", "label": "Step 2", ...}},
    {{"id": "gw_1", "label": "Check", "node_type": "exclusive_gateway"}}
  ],
  "edges": [
    {{"from": "node_1", "to": "node_2", "label": "success"}},   ← edges only between atom/gateway nodes
    {{"from": "node_2", "to": "gw_1", "label": "success"}}
  ]
}}
The first node (node_1) will be auto-connected to start_event by the builder. The last leaf node will be auto-connected to end_event.
- [ ] CRITICAL — Loopback does NOT mean orphan: even with loopback edges, every node including the loop target must have a forward-path incoming edge. The loopback edge from the gateway provides an additional cycle path, NOT the only incoming path.

Language: Respond in {"Chinese" if language.startswith("zh") else "English"}. All labels, descriptions and user-facing text should be in the specified language.

Return only JSON object, no explanations."""
