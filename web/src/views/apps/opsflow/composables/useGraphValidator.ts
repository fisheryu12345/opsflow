import { ElMessage } from 'element-plus'

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 画布校验 — 保存/执行前检测常见问题
 */
export function useGraphValidator() {

  function checkOrphanNodes(nodes: any[], edges: any[]): string[] {
    const warnings: string[] = []
    const connected = new Set<string>()
    for (const e of edges) {
      if (e.from) connected.add(e.from)
      if (e.to) connected.add(e.to)
    }
    for (const n of nodes) {
      if (!connected.has(n.id) && n.node_type !== 'start_event' && n.node_type !== 'end_event') {
        warnings.push(`Node "${n.label || n.id}" has no connections`)
      }
    }
    return warnings
  }

  function checkUnconfiguredTasks(nodes: any[]): string[] {
    const errors: string[] = []
    for (const n of nodes) {
      if (n.node_type === 'atom' && !n.atom_type) {
        errors.push(`Task node "${n.label || n.id}" has no plugin configured`)
      }
    }
    return errors
  }

  function checkMissingGatewayPaths(nodes: any[], edges: any[]): string[] {
    const warnings: string[] = []
    const outCount: Record<string, number> = {}
    for (const e of edges) {
      outCount[e.from] = (outCount[e.from] || 0) + 1
    }
    for (const n of nodes) {
      if (n.node_type === 'exclusive_gateway' && (outCount[n.id] || 0) < 2) {
        warnings.push(`Gateway "${n.label || n.id}" should have at least 2 outgoing paths`)
      }
    }
    return warnings
  }

  function validate(nodes: any[], edges: any[]): ValidationResult {
    const errors: string[] = []
    const warnings: string[] = []

    errors.push(...checkUnconfiguredTasks(nodes))
    warnings.push(...checkOrphanNodes(nodes, edges))
    warnings.push(...checkMissingGatewayPaths(nodes, edges))

    return { valid: errors.length === 0, errors, warnings }
  }

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

  return { validate, showValidation, checkOrphanNodes, checkUnconfiguredTasks }
}
