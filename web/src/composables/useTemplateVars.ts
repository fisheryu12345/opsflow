import { request } from '/@/utils/service'

/**
 * Shared loading/normalization of an OpsFlow template's global variables.
 * Used by the ITSM TASK node form (TicketDetail) and the OpsFlow submit wizard,
 * both of which render the vars via <GlobalVarInput>.
 */

export interface TemplateVarsResult {
  /** key → variable config ({ value, type, label, meta, ... }) */
  vars: Record<string, any>
  /** key → initial form value */
  values: Record<string, any>
}

/** Fetch the raw global-variables map for a template. */
export async function fetchTemplateVars(templateId: number): Promise<Record<string, any>> {
  const res: any = await request({
    url: `/api/opsflow/templates/${templateId}/global-variables/`,
    method: 'get',
  })
  return res?.data || res || {}
}

/**
 * Normalize a raw global-variables map into render configs + initial values.
 * @param coerce  when true, apply input-type coercion (slider→number, multi/checkbox/cascader→array).
 */
export function normalizeTemplateVars(
  data: Record<string, any>,
  { coerce = false }: { coerce?: boolean } = {},
): TemplateVarsResult {
  const vars: Record<string, any> = {}
  const values: Record<string, any> = {}
  for (const [key, val] of Object.entries(data || {})) {
    if (val && typeof val === 'object' && 'value' in (val as any)) {
      const cfg = val as any
      vars[key] = cfg
      let v = cfg.value ?? (cfg.type === 'int' || cfg.type === 'float' ? undefined : '')
      if (coerce) {
        if (cfg.type === 'slider') v = typeof v === 'number' ? v : Number(v) || 0
        // Array-typed controls (checkbox/cascader/multiple select) need an array:
        // split comma strings, keep existing arrays, wrap a lone scalar, else [].
        const asArray = Array.isArray(v)
          ? v
          : typeof v === 'string'
            ? (v ? v.split(',').filter(Boolean) : [])
            : (v == null ? [] : [v])
        if (cfg.meta?.multiple) v = asArray
        if (cfg.type === 'checkbox' || cfg.type === 'cascader') v = asArray
      }
      values[key] = v
    } else {
      vars[key] = { value: val, type: 'input', label: key, description: '' }
      values[key] = val ?? ''
    }
  }
  return { vars, values }
}

/** Fetch + normalize in one call. */
export async function loadTemplateVars(
  templateId: number,
  opts?: { coerce?: boolean },
): Promise<TemplateVarsResult> {
  return normalizeTemplateVars(await fetchTemplateVars(templateId), opts)
}
