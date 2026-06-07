# OpsFlow Quick Start

From template creation to execution monitoring — complete your first ops pipeline in 5 minutes.

---

## Overview

```
Create Template → Design Pipeline → Publish Version → Submit Execution → Monitor & Approve
  ①                ②                  ③                 ④                  ⑤
```

Four core pages: **Design Canvas** → **Template Management** → **Execution Records** → **Monitor Detail**

---

## 1. Create Template

Three ways to create a template:

| Method | How | When |
|--------|-----|------|
| 🤖 **AI Generate** | Describe your workflow in natural language via the AI chat panel | Starting from scratch with a clear requirement |
| 📄 **Blank Canvas** | Click "New Template" → choose "Blank Canvas" | Want full manual control |
| 📋 **Clone Existing** | Click "New Template" → choose "Clone from Existing" | Basing on an existing template |

**Draft vs Published:**
- A new template is a **Draft** (`is_draft=true`) — editable but non-executable
- Click **Publish** after design to make it executable
- Publishing creates a **version snapshot** — executions read the snapshot, not the live edit

---

## 2. Design Pipeline

### Node Types

| Node | Icon | Purpose |
|------|------|---------|
| Start/End | 🟢🔴 | Pipeline start and end points |
| Task Node | ▢ | Executes operations (Shell, API, etc.), **must select a plugin** |
| Exclusive Gateway | 🔷(×) | Conditional branching |
| Parallel Gateway | 🔷(+) | Execute multiple branches in parallel |
| Converge Gateway | 🔷(⊕) | Parallel branch join point |
| Approval Node | 🔷(🔒) | Requires human approval to proceed |
| Subprocess | ⬜ | Reuse another template as a step |

### Key Operations

1. **Drag nodes from the Stencil** (left panel) onto the canvas
2. **Task nodes MUST select a plugin** (e.g., Shell, Ansible), or they cannot execute
3. **Configure parameters**: Click a node → right Property Panel → set command, timeout, retry policy
4. **Edge conditions**: Edges from Exclusive Gateways can have conditions like `${node_2.cpu} > 80`
5. **Variable references**: Use `${node_id.output_key}` in parameters to reference other nodes' outputs
6. **Save**: Click save button frequently during design

### Shortcuts

- `Ctrl+Z` / `Ctrl+Y`: Undo / Redo
- `Delete` / `Backspace`: Delete selected node
- Mouse wheel: Zoom canvas
- Drag canvas empty area: Pan view

---

## 3. Publish Version

After design:

1. Click **Save** to save the draft
2. Click **Publish** (or the execution wizard triggers it automatically)
3. After publishing, the version is **frozen** — edit it creates a new version

> **Note**: Executions always use the published snapshot, never the live edit. This ensures isolation.

---

## 4. Execution Flow (5-Step Wizard)

Click the **▶ Execute** button in the toolbar to open the 5-step submission wizard:

| Step | Content | Description |
|------|---------|-------------|
| ① Validation | AI validates pipeline topology | Checks node integrity, edge correctness, engine compatibility |
| ② Change Request | Link a ServiceNow CR | Optional — associates this execution with a change management process |
| ③ Parameters | Set variables | Override template global variable defaults |
| ④ Risk Assessment | AI analyzes change impact | Each risk item must be acknowledged individually |
| ⑤ Schedule | Timed or manual trigger | Auto-execute at a specified time or trigger after approval |

### State Transitions

```
pending → running → completed  ✓
                   → failed     ✗  → Retry / Skip
                   → cancelled  ✕
         → paused  ⏸  → resume
```

---

## 5. Monitor & Troubleshoot

### Monitor Canvas

Go to **Execution Records** → click an execution ID to enter detail view:

- Node colors reflect real-time status:
  - 🟢 Green = Completed
  - 🟡 Yellow = Running
  - 🔴 Red = Failed
  - ⚪ Gray = Pending
  - 🟣 Purple = Pending Approval

### Node Operations

| Action | Description | When to Use |
|--------|-------------|-------------|
| Retry | Re-execute a failed node | Temporary failure resolved |
| Skip | Skip a failed node, continue | Non-critical step failed |
| Force Fail | Force-mark a node as failed | Node stuck indefinitely |
| Pause | Pause the entire pipeline | Manual intervention needed |
| Cancel | Cancel the entire execution | Issue found, stop execution |

### Approval Nodes

When the pipeline includes an approval node, execution pauses at that node:

1. Go to **Approval Center** to view pending items
2. Click **Approve** or **Reject**
3. After approval, the pipeline automatically continues

### Logs

The right panel provides three tabs:
- **Logs**: Execution log timeline
- **Traces**: Node trace table, click a node to view inputs/outputs
- **Data**: Node input/output details (stdout, stderr)

---

## 6. FAQ

### Q: Why did my node fail?

Common causes:
- **Plugin not selected**: Task nodes must have a plugin chosen
- **Incomplete parameters**: Required fields are missing
- **Timeout**: Node execution exceeded `timeout_seconds`
- **Host unreachable**: Target hosts in `target_hosts` are not reachable
- **Bad variable reference**: `${node_id.key}` references a non-existent node or output

### Q: How do I reference another node's output?

Use the `${node_id.output_key}` syntax in parameters.
For example, a Shell node's stdout can be referenced as `${node_2.stdout}`.
The Property Panel's "Output Parameters" section has a copy button for each output.

### Q: What's the difference between Draft and Published?

| | Draft | Published |
|--|-------|-----------|
| Editable | ✅ Yes | ❌ No (must create new version) |
| Executable | ❌ No | ✅ Yes |
| Version Snapshot | ❌ None | ✅ Yes (execution isolation) |

### Q: How do I write condition expressions?

On edges from Exclusive Gateways, select the `custom` label and enter:
```
${node_2.cpu} > 80
${_result} == True
${memory_usage} < 4096
```

### Q: Can I retry after an execution fails/completes?

- **Failed nodes**: Yes — Retry or Skip in the monitor detail view
- **Completed nodes**: No
- **Cancelled executions**: No — must re-submit

### Q: How do I set up scheduled execution?

In the wizard's Step 5, choose **Scheduled Execution**:
1. Pick a date (must be within the change request's window)
2. Pick a time
3. Submit — the system triggers automatically at the specified time

### Q: Do multiple branches execute simultaneously?

Yes — use **Parallel Gateway** for multi-branch parallel execution.
All branches converge at a **Converge Gateway** before the pipeline continues.
