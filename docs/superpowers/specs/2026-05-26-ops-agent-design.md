# Ops Agent — LLM 驱动的运维 Agent 架构设计

**日期：** 2026-05-26
**定位：** 全栈运维 CLI Agent，LLM 驱动，分级审批，审计完备
**参考：** Claude Code 架构哲学

---

## 1. 概述

### 1.1 目标

设计一个类似 Claude Code 的 CLI 工具，面向 IT 运维场景。用户通过自然语言下指令，Agent 自动调用工具（SSH、K8s、DB、Cloud API、监控等）执行运维操作。

### 1.2 核心设计原则（取自 Claude Code）

| 原则 | 运维场景应用 |
|------|-------------|
| 薄 Agent Loop | 主循环只负责 think→tool→observe，不做复杂状态机 |
| 工具即函数 | 每个运维工具是一个 Python 函数 + JSON Schema |
| 权限分层 | 读/低风险/高风险三级，环境感知（prod > staging > dev） |
| 子代理隔离 | 高危操作 fork 独立子代理，限制工具集和 blast radius |
| 全程审计 | 每次 tool call 记录输入/输出/决策/审批，不可变日志 |

### 1.3 设计决策汇总

| 维度 | 决策 |
|------|------|
| 定位 | LLM 驱动的全栈运维 Agent |
| 场景 | 服务器运维 + 云基础设施管理 |
| 交互 | CLI 为主（REPL + 管道模式） |
| 安全 | 分级审批：三维度风险评估 × 四级审批策略 |
| 构建方式 | 参考 Claude Code 架构，从零设计 Python 实现 |
| LLM | 多 Provider 支持（Claude / OpenAI / 本地模型） |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Layer                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │   REPL   │  │  管道模式 │  │ 审计查询 │  │  会话管理        │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      Agent Core  ( ~500 行 )                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  User Input → [LLM Think → Tool Select → Safety Check →      │   │
│  │                Execute → Observe → Think → Response ]         │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  Tool System │  │  Safety Engine   │  │  Context Manager     │   │
│  │              │  │                  │  │                      │   │
│  │ · ToolDef    │  │ · Risk Scorer    │  │ · Global Context     │   │
│  │ · Registry   │  │ · Approval Gate  │  │ · Environment Ctx    │   │
│  │ · Sandbox    │  │ · Trust Policy   │  │ · Session Context    │   │
│  │ · Preview    │  │ · Blast Radius   │  │ · Memory Store       │   │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘   │
│         │                   │                       │               │
│  ┌──────┴───────────────────┴───────────────────────┴───────────┐   │
│  │                    Infrastructure                             │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │  │LLM      │  │Audit Log │  │Session   │  │Config/Plugin │  │   │
│  │  │Provider │  │(append-  │  │Manager   │  │Manager       │  │   │
│  │  │         │  │ only)    │  │          │  │              │  │   │
│  │  └─────────┘  └──────────┘  └──────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Loop（核心引擎）

```python
async def agent_loop(user_input: str, context: AgentContext):
    messages = [system_prompt(context), *context.history, user_message(user_input)]
    
    while True:
        response = await llm.chat(messages, tools=available_tools)
        
        if response.is_text:
            yield response.text  # 流式输出给 CLI
            break
        
        for tool_call in response.tool_calls:
            decision = await safety.check(tool_call, context)
            if decision == SafetyDecision.ASK:
                yield await cli.ask_user(tool_call)
            elif decision == SafetyDecision.DENY:
                yield f"Blocked: {tool_call.reason}"
                continue
            
            result = await tool.execute(tool_call)
            audit.log(tool_call, result, decision)
            messages.append(tool_result(tool_call, result))
```

设计要点：
- 薄循环，无复杂状态机
- 每次 tool call 经过安全引擎
- 每次 tool call 记录审计日志
- 单次用户输入可能产生多轮 tool call

---

## 4. 分级安全引擎

### 4.1 风险评估模型

```
风险分数 = 操作类型权重 × 目标环境系数 × 影响范围系数
```

| 维度 | 分类 | 系数 | 示例 |
|------|------|------|------|
| **操作类型** | READ | 0 | cat, ls, df, ps, kubectl get, SELECT |
| | LOW_WRITE | 1 | touch, echo append, restart single pod |
| | MEDIUM_WRITE | 3 | package install, config change, scale deployment |
| | HIGH_WRITE | 7 | restart database, iptables, DROP TABLE |
| | CRITICAL | 10 | rm -rf, drop database, terraform destroy |
| **目标环境** | dev/staging | 0.3 | |
| | canary | 0.6 | |
| | production | 1.0 | |
| **影响范围** | single | 0.5 | 单台机器/单实例 |
| | group | 0.8 | 一组节点/一个 service |
| | cluster-wide | 1.0 | 整个集群/跨区域 |

### 4.2 审批策略

| 总风险分 | 行为 |
|----------|------|
| 0 | **AUTO** — 静默执行 |
| 0.1 ~ 2.0 | **AUTO** — 执行但回显结果 |
| 2.1 ~ 5.0 | **ASK** — 显示操作摘要，需确认 |
| 5.1+ | **ASK + BLAST RADIUS** — 显示影响范围估算，需显式输入 `yes` 确认 |

### 4.3 与 Claude Code 权限模型的关键区别

| | Claude Code | 运维 Agent |
|------|------------|---------|
| 决策维度 | 工具名 | 工具名 + 参数 + 环境 + 范围 |
| 用户记忆 | 会话级 allow | 持久化信任策略 + 过期机制 |
| 风险评估 | 无（二元 allow/deny） | 5 级分数制 |
| 上下文 | 本地文件系统 | 多目标多环境 |

---

## 5. 工具系统

### 5.1 工具协议

```python
class ToolDef:
    name: str
    description: str          # LLM 选工具的依据
    parameters: dict          # JSON Schema
    risk_level: RiskLevel     # READ / LOW_WRITE / MEDIUM_WRITE / HIGH_WRITE / CRITICAL
    risk_scorer: Callable | None  # 可选，按参数动态评分
    handler: AsyncCallable
    requires_approval: bool
```

### 5.2 第一方工具集（内置）

| 类别 | 工具 | 风险 | 说明 |
|------|------|------|------|
| **远程执行** | `ssh_exec` | 按命令评分 | SSH 执行命令，返回 stdout/stderr/exit_code |
| | `ssh_script` | MEDIUM+ | 上传脚本并执行 |
| **文件系统** | `fs_read` | READ | 读文件，支持 tail/head/正则过滤 |
| | `fs_write` | MEDIUM | 写入文件（原子写 + 自动备份原文件） |
| | `fs_search` | READ | 按模式搜索文件内容 |
| **数据库** | `db_query` | READ | 只读 SQL 查询，结果分页 |
| | `db_exec` | HIGH | 写 SQL，自动开启事务，需确认 |
| **K8s** | `k8s_get` | READ | kubectl get 的封装 |
| | `k8s_describe` | READ | 资源详情 + events |
| | `k8s_logs` | READ | Pod 日志，支持时间范围 |
| | `k8s_apply` | MEDIUM | 应用 YAML，先 diff 再 apply |
| | `k8s_scale` | MEDIUM | 扩缩容 |
| | `k8s_restart` | HIGH | 滚动重启 |
| **云 API** | `cloud_list` | READ | 列出资源 |
| | `cloud_describe` | READ | 单个资源详情 |
| | `cloud_modify` | HIGH | 修改云资源属性 |
| **监控** | `promql_query` | READ | Prometheus 即时/范围查询 |
| | `grafana_dashboard` | READ | 获取仪表盘数据 |
| | `alert_list` | READ | 当前活跃告警 |
| | `alert_ack` | LOW | 确认/静默告警 |
| **通用** | `http_call` | 按方法评分 | HTTP 请求 |
| | `python_eval` | 按代码评分 | 执行 Python 片段 |
| | `subagent` | 按任务评分 | 启动子代理 |

### 5.3 工具沙箱预览

高风险工具（≥ MEDIUM）默认在预览模式下运行——先展示将要做的事情，再实际执行。

### 5.4 工具发现

插件化设计：丢到 `tools/` 目录即自动注册。

---

## 6. 上下文与记忆系统

### 6.1 三层上下文模型

| 层级 | 内容 | 生命周期 |
|------|------|----------|
| **全局上下文** | 运维规范 & 操作手册、团队知识库、On-call 排班 | 持久 |
| **环境上下文** | OPS_CONTEXT.md、CMDB 拓扑、凭证、约束 | 目标切换时加载 |
| **会话上下文** | 当前目标、历史操作、任务状态、子代理状态 | 会话级 |

### 6.2 环境上下文（OPS_CONTEXT.md）

每个环境目录下放一个 `OPS_CONTEXT.md`，是运维团队维护的约束文件。Agent 每次决策前必读。内容包括：集群拓扑、关键服务映射、变更窗口约束、凭证路径等。

### 6.3 记忆类型

| 记忆类型 | 示例 |
|----------|------|
| **故障模式** | "上次 user-svc 504 是因为 Redis 连接池耗尽" |
| **操作经验** | "该集群 kubelet 对资源压力敏感，扩容前先检查节点条件" |
| **团队偏好** | "DBA 要求所有 schema 变更走 Jira 审批" |
| **临时约束** | "双11压测期间 user-svc 不能重启" (带过期时间) |

---

## 7. 子代理系统

### 7.1 核心场景

| 场景 | 父代理 | 子代理 | 隔离级别 |
|------|--------|--------|----------|
| **故障诊断** | 收到告警 | 并行查日志/指标/DB 慢查询 | 只读工具集 |
| **批量巡检** | 检查所有环境 | 每环境一个子代理并发 | 只读工具集 |
| **安全操作** | 需重启数据库 | 子代理受限执行，父代理观察 | 有限写 + 超时 |
| **跨团队** | DBA 和 SRE 分开审计 | 各自独立记录 | 按角色分配工具 |

### 7.2 隔离三个维度

- **工具集限制** — 指定可用的工具列表
- **目标范围限制** — 限制 IP 段 / namespace / 资源类型
- **时间限制** — 超时强制终止

### 7.3 子代理审批继承

子代理继承安全引擎但阈值更严格（默认只读）。

---

## 8. CLI 交互

### 8.1 两种模式

- **REPL 模式**（默认）— 交互式对话
- **管道模式** — `ops run "指令" --yes`，适合脚本化和 cron

### 8.2 关键特性

- 实时回显：每个 tool call 执行时流式显示
- Markdown 表格：结构化数据用表格呈现
- 会话回放：`ops session replay <id>`
- 颜色/符号语义：✓ ⚠ ✗ 🔒 ⏱

---

## 9. 审计与合规

### 9.1 审计记录格式

每次 tool call 的完整记录（JSON），包含：session_id、operator、target、tool、parameters、risk_assessment、execution 详情、LLM 决策理由、内容哈希。

### 9.2 三种审计视图

- **按会话** — 复盘一次事故处理过程
- **按目标** — 安全审查特定资源上的操作
- **按操作类型** — 合规检查高危操作列表

### 9.3 存储要求

- 防篡改：每日哈希链
- 不可删除：append-only，无 delete API
- 合规保留：可配置保留期（默认 365 天）
- 集成：支持 Syslog / Elasticsearch / Webhook sink

---

## 10. 调用链示例

```
用户: "user-svc 延迟升高，帮我排查"
  │
  ├─[1]─→ Agent Loop 接收输入
  │        ├─ 加载环境上下文 (k8s prod)
  │        └─ 构建 messages
  │
  ├─[2]─→ LLM Think → 决策：并行启动 3 个子代理
  │
  ├─[3]─→ Safety Engine 检查 → subagent(read_only) → Risk 0 → AUTO
  │
  ├─[4]─→ 并行执行 3 个子代理
  │        ├─ Subagent A: k8s_get + k8s_describe
  │        ├─ Subagent B: promql_query + grafana_dashboard
  │        └─ Subagent C: db_query (慢查询分析)
  │        └─ 每个 tool call → Audit Log
  │
  ├─[5]─→ LLM 汇总子代理结果 → 生成诊断
  │
  ├─[6]─→ Response → CLI 渲染
  │
  └─[7]─→ Context 更新 (临时约束)
```

---

## 11. 关键技术决策

1. **Python 实现** — 运维生态（Ansible/kubernetes-client/sqlalchemy）都在 Python
2. **多 LLM Provider** — Claude（主力推理）/ OpenAI（备选）/ 本地模型（敏感环境离线部署）
3. **异步优先** — 子代理并行、流式输出、超时控制都依赖 asyncio
4. **无状态 Agent + 持久化 Context** — Agent 本身无状态，上下文随目标切换加载
