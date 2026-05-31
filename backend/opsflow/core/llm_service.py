import os
import json
import re
from openai import OpenAI


def _get_llm_client():
    """Get OpenAI-compatible client (reuses DeepSeek config from conf/env.py)"""
    from conf.env import OPSAGENT_API_KEY, OPSAGENT_BASE_URL, OPSAGENT_MODEL
    api_key = os.environ.get('OPENAI_API_KEY') or OPSAGENT_API_KEY
    base_url = os.environ.get('OPENAI_BASE_URL') or OPSAGENT_BASE_URL
    model = os.environ.get('OPENAI_MODEL') or OPSAGENT_MODEL
    return OpenAI(api_key=api_key, base_url=base_url), model


def generate_pipeline(nl_input: str, target_hosts: list = None) -> dict:
    """Convert natural language to Pipeline Tree JSON"""
    client, model = _get_llm_client()
    system_prompt = _build_system_prompt(target_hosts or [])

    # RAG context injection
    rag_context = rag_search(nl_input)
    if rag_context:
        system_prompt += "\n\nReference historical cases:\n" + json.dumps(rag_context, ensure_ascii=False, indent=2)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': nl_input},
        ],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = response.choices[0].message.content
    # MySQL does not support 4-byte UTF-8
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    result = json.loads(text)
    return result


def refine_pipeline(nl_input: str, nodes: list, edges: list, target_hosts: list = None) -> dict:
    """Multi-turn: modify existing Pipeline Tree based on new instruction"""
    client, model = _get_llm_client()
    system_prompt = _build_system_prompt(target_hosts or [])

    existing = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2)
    system_prompt += f'\n\n===== Current Pipeline Tree (result of previous iterations) =====\n{existing}\n\n'
    system_prompt += """===== Critical: Iterative Modification Rules =====
You are in an iterative design conversation. The Pipeline Tree above is the result of previous iterations — DO NOT generate a brand new pipeline from scratch.

Rules:
1. Each new instruction is a MODIFICATION request on the EXISTING pipeline above.
2. Preserve ALL existing nodes and edges that are still relevant. Only add, remove, or change specific parts based on the new instruction.
3. If the user asks to add a step, INSERT new nodes/edges into the existing structure.
4. If the user asks to change a step, MODIFY the relevant node's params/label/atom_type.
5. If the user asks to remove a step, DELETE only those specific nodes and their edges (reconnect if needed).
6. Return the COMPLETE updated pipeline JSON (including all unchanged parts), never return a diff or partial tree.
7. Keep existing node IDs stable unless you have a specific reason to change them."""


    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': nl_input},
        ],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = response.choices[0].message.content
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    result = json.loads(text)
    return result




def rag_search(query: str, top_k: int = 5) -> list:
    """Simple text RAG search — recall relevant cases from OpsKnowledge"""
    from opsflow.models import OpsKnowledge
    results = OpsKnowledge.objects.filter(content__icontains=query)[:top_k]
    return [{'title': r.title, 'content': r.content[:500]} for r in results]


def analyze_pipeline(nodes: list, edges: list) -> dict:
    """Analyze Pipeline Tree: describe purpose, steps, and potential risks"""
    client, model = _get_llm_client()

    pipeline_str = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, indent=2)

    prompt = f"""You are an ops pipeline analysis expert. Analyze the following Pipeline Tree and return JSON in English:

{{"summary": "Brief pipeline overview (one sentence)", "steps": ["Step description", ...], "risks": ["Risk description", ...], "suggestions": ["Suggestion", ...]}}

Pipeline Tree:
{pipeline_str}

Requirements:
- steps: list each node's operation in execution order
- risks: analyze potential risks (e.g., missing backup, no rollback path)
- suggestions: provide optimization recommendations
Return empty array for risks if none found. Return only JSON."""

    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    text = response.choices[0].message.content
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    return json.loads(text)


def _build_system_prompt(target_hosts: list) -> str:
    hosts_str = ', '.join(target_hosts) if target_hosts else 'target hosts (specified by user)'

    # Dynamically generate atom list from plugin registry
    from opsflow.plugins.registry import get_all_plugins
    atoms = get_all_plugins()
    # Filter out shell — AI should not use it as fallback for missing atoms
    atoms = {k: v for k, v in atoms.items() if k != 'shell'}
    atom_lines = []
    for code, cls in sorted(atoms.items()):
        form_config = cls.get_form_config() or []
        inputs_str = ', '.join(item.tag_code for item in form_config)
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

Node types and degree rules:
  - atom: ServiceActivity, indegree>=1, outdegree 1-2 (2 edges must be success/failure)
  - exclusive_gateway: selects one branch based on condition, indegree>=1, outdegree>=1
  - parallel_gateway: executes all branches in parallel, must pair with converge_gateway, indegree>=1, outdegree>=1
  - conditional_parallel_gateway: conditionally executes branches in parallel, must pair with converge_gateway, indegree>=1, outdegree>=1
  - converge_gateway: merges multiple branches into one, indegree>=1, outdegree=1

===== Important: Gateway Usage Scenarios (understand and use correctly) =====

1. exclusive_gateway --- "choose one"
   Scenario: after an operation, choose a path based on the result — only one path executes.
   Example: health check passes → deploy, fails → alert.
   Structure: atom → exclusive_gateway → (branch A OR branch B)

2. parallel_gateway --- "execute all"
   Scenario: multiple independent tasks run concurrently, no conditional branching.
   Example: run the same operation on multiple servers simultaneously, backup multiple dirs concurrently.
   Structure: parallel_gateway → (branch A, branch B) → converge_gateway (must pair)

3. conditional_parallel_gateway --- "execute all that match"
   Scenario: batch of parallel tasks, but some branches have conditions.
   Example: deploy to multiple environments — staging uses one logic, production uses another.
   Structure: conditional_parallel_gateway → (cond A, cond B) → converge_gateway (must pair)

4. converge_gateway --- "merge point"
   Scenario: merge multiple divergent paths back into one.
   Note: ALL branches diverged by parallel/conditional_parallel_gateway must converge to the SAME converge_gateway.

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

bamboo-engine constraints:
1. The flow must be a DAG (Directed Acyclic Graph) — no circular dependencies
2. Branch labels can only be "success" or "failure"
3. All node IDs must be unique
4. Nodes with only outgoing edges (no incoming) are start nodes
5. All branches of parallel_gateway and conditional_parallel_gateway must converge to the same converge_gateway
6. converge_gateway indegree must be >= 2 (converges at least 2 branches)
7. Regular atom nodes can have at most 2 outgoing edges (success + failure)
8. Target hosts: {hosts_str}

Return only JSON object, no explanations."""
