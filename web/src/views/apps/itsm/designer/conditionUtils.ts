// ── Condition types & utilities ──
// Copied from opsflow to avoid cross-app imports

export interface VariableOption {
  source: string
  sourceLabel: string
  field: string
  fieldLabel: string
  fieldType: string
  sourceType: 'node' | 'global' | 'project' | 'system'
  value?: any
}

export interface ConditionRule {
  valueType: string
  source: string
  field: string
  fieldLabel?: string
  fieldType?: string
  op: string
  value: string
}

export interface ConditionStruct {
  logic: 'AND' | 'OR'
  rules: ConditionRule[]
}

/** Condition operator list — BoolRule-compatible only */
export const CONDITION_OPS = ['==', '!=', '>', '<', '>=', '<=', 'in', 'notin'] as const

/** Filter available operators by field type */
export function opsForType(fieldType: 'string' | 'number' | 'boolean'): string[] {
  if (fieldType === 'boolean') return ['==', '!=']
  if (fieldType === 'number') return ['==', '!=', '>', '<', '>=', '<=']
  return ['==', '!=', '>', '<', '>=', '<=', 'in', 'notin']
}

/**
 * Structured conditions → ${...} expression string
 *
 * Rules:
 *   {source: "node_1", field: "cpu", op: ">", value: "80"}
 *   → "${node_1.cpu} > 80"
 *
 * String values are auto-quoted:
 *   {fieldType: "string", value: "ok"}
 *   → "${node_1.status} == \"ok\""
 *
 * Multi-condition AND/OR:
 *   [{...}, {...}] with logic "AND"
 *   → "${node_1.cpu} > 80 AND ${node_1.mem} < 50"
 */
export function generateConditionExpr(rules: ConditionRule[], logic: 'AND' | 'OR'): string {
  if (!rules || rules.length === 0) return ''

  const parts = rules.map((r) => {
    const ref = `\${${r.source}.${r.field}}`

    // Quote string values (not boolean or number)
    // in/notin need array literal: ["a","b"] not "a,b"
    let val = r.value
    if (r.op === 'in' || r.op === 'notin') {
      const items = r.value.split(',').map(v => `"${v.trim().replace(/"/g, '\\"')}"`).filter(Boolean)
      val = `[${items.join(', ')}]`
    } else if (r.fieldType === 'string' || (r.valueType === 'string' && r.fieldType !== 'boolean' && r.fieldType !== 'number')) {
      val = `"${r.value.replace(/"/g, '\\"')}"`
    }

    return `${ref} ${r.op} ${val}`
  })

  return parts.join(` ${logic} `)
}
