import { ElMessage, ElMessageBox } from 'element-plus'

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 画布校验 — 保存/执行前检测常见问题
 *
 * 将后端正则校验逻辑提前到前端 X6 流程图编辑器中，
 * 在用户创建/编辑流程图时实时发现并提示，减少后端校验负担。
 *
 * 对应后端 bamboo_validator.py 前置的检查项：
 *   - 空流程 / 无有效节点
 *   - 环检测（Kahn 拓扑排序）
 *   - 节点出入度合法性（atom / 汇聚网关）
 *   - 网关标签完整性
 *   - 条件变量引用 ${node_id.key} 存在性
 */
export function useGraphValidator() {

  /** 无节点或只有 start/end */
  function checkEmptyFlow(nodes: any[]): string[] {
    const warnings: string[] = []
    const effective = nodes.filter(n =>
      n.node_type !== 'start_event' && n.node_type !== 'end_event'
    )
    if (nodes.length === 0) {
      warnings.push('空流程')
    } else if (effective.length === 0) {
      warnings.push('无有效节点')
    }
    return warnings
  }

  /** 未被任何边引用的孤立节点 */
  function checkOrphanNodes(nodes: any[], edges: any[]): string[] {
    const warnings: string[] = []
    const connected = new Set<string>()
    for (const e of edges) {
      if (e.from) connected.add(e.from)
      if (e.to) connected.add(e.to)
    }
    for (const n of nodes) {
      if (!connected.has(n.id) && n.node_type !== 'start_event' && n.node_type !== 'end_event') {
        warnings.push(`节点 "${n.label || n.id}" 没有连线，被孤立`)
      }
    }
    return warnings
  }

  /** 非 start_event 节点无入边检查（没有入边的节点永远不会被执行） */
  function checkZeroInDegree(nodes: any[], edges: any[]): string[] {
    const errors: string[] = []
    const inCount: Record<string, number> = {}
    for (const n of nodes) inCount[n.id] = 0
    for (const e of edges) {
      if (inCount[e.to] != null) inCount[e.to]++
    }
    for (const n of nodes) {
      if (n.node_type === 'start_event') continue
      if (inCount[n.id] === 0) {
        errors.push(`节点 "${n.label || n.id}" 入度=0，没有入边的节点永远不会被执行`)
      }
    }
    return errors
  }

  /** 未配置插件的 Task 节点 */
  function checkUnconfiguredTasks(nodes: any[]): string[] {
    const errors: string[] = []
    for (const n of nodes) {
      if (n.node_type === 'atom' && !n.atom_type) {
        errors.push(`活动节点 "${n.label || n.id}" 未配置插件`)
      }
    }
    return errors
  }

  /** 网关出边路径不足（排他/条件并行网关至少 2 条） */
  function checkMissingGatewayPaths(nodes: any[], edges: any[]): string[] {
    const warnings: string[] = []
    const outCount: Record<string, number> = {}
    for (const e of edges) {
      outCount[e.from] = (outCount[e.from] || 0) + 1
    }
    for (const n of nodes) {
      if (n.node_type === 'exclusive_gateway' && (outCount[n.id] || 0) < 2) {
        warnings.push(`排他网关 "${n.label || n.id}" 应有至少 2 条出边`)
      }
      if (n.node_type === 'conditional_parallel_gateway' && (outCount[n.id] || 0) < 2) {
        warnings.push(`条件并行网关 "${n.label || n.id}" 应有至少 2 条出边`)
      }
    }
    return warnings
  }

  /** 环检测 — Kahn 拓扑排序（同后端 bamboo_validator） */
  function checkCycle(nodes: any[], edges: any[]): string[] {
    const errors: string[] = []
    const effectiveIds = new Set(nodes.map(n => n.id))
    const inDegree: Record<string, number> = {}
    const outEdges: Record<string, string[]> = {}

    for (const n of nodes) {
      inDegree[n.id] = 0
      outEdges[n.id] = []
    }
    for (const e of edges) {
      if (effectiveIds.has(e.from) && effectiveIds.has(e.to)) {
        outEdges[e.from].push(e.to)
        inDegree[e.to] = (inDegree[e.to] || 0) + 1
      }
    }

    const queue = Object.entries(inDegree).filter(([_, d]) => d === 0).map(([id]) => id)
    let visited = 0
    while (queue.length) {
      const nid = queue.shift()!
      visited++
      for (const target of outEdges[nid] || []) {
        inDegree[target]--
        if (inDegree[target] <= 0) queue.push(target)
      }
    }

    if (visited !== Object.keys(inDegree).length) {
      errors.push('流程中存在环，bamboo-engine 不支持')
    }
    return errors
  }

  /** 汇聚网关出入度检查 */
  function checkConvergeGatewayDegree(nodes: any[], edges: any[]): string[] {
    const warnings: string[] = []
    for (const n of nodes) {
      if (n.node_type !== 'converge_gateway') continue
      const inEdges = edges.filter(e => e.to === n.id)
      const outEdges = edges.filter(e => e.from === n.id)
      if (inEdges.length < 2) {
        warnings.push(`汇聚网关 "${n.label || n.id}" 入边少于 2 条，建议改用直接连接`)
      }
      if (outEdges.length > 1) {
        warnings.push(`汇聚网关 "${n.label || n.id}" 有多条出边，将取第一条`)
      }
    }
    return warnings
  }

  /** 条件变量引用校验 — 检查 ${node_id.key} 中 node_id 是否存在 */
  function checkConditionRefs(nodes: any[], edges: any[]): string[] {
    const errors: string[] = []
    const nodeIds = new Set(nodes.map(n => n.id))
    const EXPR_PATTERN = /\$\{([^}]*)\}/g
    const VAR_REF_PATTERN = /([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)/g

    for (const e of edges) {
      const cond = (e.condition || '').trim()
      if (!cond) continue
      let match: RegExpExecArray | null
      EXPR_PATTERN.lastIndex = 0
      while ((match = EXPR_PATTERN.exec(cond)) !== null) {
        const expr = match[1]
        let varMatch: RegExpExecArray | null
        VAR_REF_PATTERN.lastIndex = 0
        while ((varMatch = VAR_REF_PATTERN.exec(expr)) !== null) {
          const refNodeId = varMatch[1]
          if (!nodeIds.has(refNodeId)) {
            errors.push(`边 ${e.from}→${e.to} 的条件引用不存在的节点 '${refNodeId}'`)
          }
        }
      }
    }
    return errors
  }

  /** 综合校验 — 运行所有检查 */
  function validate(nodes: any[], edges: any[]): ValidationResult {
    const errors: string[] = []
    const warnings: string[] = []

    warnings.push(...checkEmptyFlow(nodes))
    errors.push(...checkUnconfiguredTasks(nodes))
    errors.push(...checkZeroInDegree(nodes, edges))
    warnings.push(...checkOrphanNodes(nodes, edges))
    warnings.push(...checkMissingGatewayPaths(nodes, edges))
    errors.push(...checkCycle(nodes, edges))
    warnings.push(...checkConvergeGatewayDegree(nodes, edges))
    errors.push(...checkConditionRefs(nodes, edges))

    return { valid: errors.length === 0, errors, warnings }
  }

  /** 显示校验结果 */
  function showValidation(result: ValidationResult): boolean {
    if (result.errors.length > 0) {
      result.errors.forEach(e => ElMessage.error(e))
      return false
    }
    if (result.warnings.length > 0) {
      result.warnings.forEach(w => ElMessage.warning(w))
    }
    return true
  }

  return { validate, showValidation }
}
