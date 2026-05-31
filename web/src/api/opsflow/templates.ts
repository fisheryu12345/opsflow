import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetTemplates(params?: any) {
  return request({ url: prefix + 'templates/', method: 'get', params })
}

export function GetTemplateDetail(id: number) {
  return request({ url: prefix + `templates/${id}/`, method: 'get' })
}

export function CreateTemplate(data: any) {
  return request({ url: prefix + 'templates/', method: 'post', data })
}

export function UpdateTemplate(id: number, data: any) {
  return request({ url: prefix + `templates/${id}/`, method: 'patch', data })
}

export function DeleteTemplate(id: number) {
  return request({ url: prefix + `templates/${id}/`, method: 'delete' })
}

export function CreateFromAi(data: { input: string; target_hosts?: string[]; global_vars?: any }) {
  return request({
    url: prefix + 'templates/create_from_ai/',
    method: 'post',
    data,
    timeout: 60000,
  })
}

export function ConfirmDraft(id: number) {
  return request({ url: prefix + `templates/${id}/confirm_draft/`, method: 'post' })
}

export function GetDiff(id: number) {
  return request({ url: prefix + `templates/${id}/diff/`, method: 'get' })
}

export function AiLayout(data: { nodes: any[]; edges: any[] }) {
  return request({
    url: prefix + 'templates/ai_layout/',
    method: 'post',
    data,
    timeout: 30000,
  })
}

export function AnalyzePipeline(data: { nodes: any[]; edges: any[] }) {
  return request({
    url: prefix + 'templates/analyze/',
    method: 'post',
    data,
    timeout: 30000,
  })
}

export function RefinePipeline(data: { input: string; nodes: any[]; edges: any[]; target_hosts?: string[] }) {
  return request({
    url: prefix + 'templates/refine/',
    method: 'post',
    data,
    timeout: 60000,
  })
}

/* ---------- Version management ---------- */
export function PublishTemplate(id: number) {
  return request({ url: prefix + `templates/${id}/publish/`, method: 'post' })
}

export function GetTemplateVersions(id: number) {
  return request({ url: prefix + `templates/${id}/versions/`, method: 'get' })
}

export function RollbackTemplate(id: number, version: number) {
  return request({ url: prefix + `templates/${id}/rollback/`, method: 'post', data: { version } })
}

export function ExportTemplate(id: number) {
  return request({ url: prefix + `templates/${id}/export/`, method: 'get' })
}

export function ImportTemplate(data: any) {
  return request({ url: prefix + 'templates/import_template/', method: 'post', data })
}

export function GetTemplateCategories() {
  return request({ url: prefix + 'templates/categories/', method: 'get' })
}

export function GetHookVariables(id: number) {
  return request({ url: prefix + `templates/${id}/hook_variables/`, method: 'get' })
}

export function UpdateHookVariables(id: number, data: any) {
  return request({ url: prefix + `templates/${id}/hook_variables/`, method: 'post', data })
}

/* ---------- Global Variable System (Phase 1-2) ---------- */
export function GetGlobalVariables(id: number) {
  return request({ url: prefix + `templates/${id}/global-variables/`, method: 'get' })
}

export function UpdateGlobalVariables(id: number, data: { global_vars: any }) {
  return request({ url: prefix + `templates/${id}/global-variables/`, method: 'post', data })
}

export function PatchGlobalVariables(id: number, data: { global_vars: any }) {
  return request({ url: prefix + `templates/${id}/global-variables/`, method: 'patch', data })
}

export function GetVariableBrowser(id: number) {
  return request({ url: prefix + `templates/${id}/variable-browser/`, method: 'get' })
}

export function HookVariable(id: number, data: { var_key: string; node_id: string; tag_code?: string; var_type?: string; description?: string }) {
  return request({ url: prefix + `templates/${id}/hook-variable/`, method: 'post', data })
}

export function UnhookVariable(id: number, data: { var_key: string }) {
  return request({ url: prefix + `templates/${id}/unhook-variable/`, method: 'post', data })
}

export function GetVariableTypes() {
  return request({ url: prefix + 'plugins/variable_types/', method: 'get' })
}

/* ---------- Subprocess Version Tracking (Phase 3-4) ---------- */
export function GetSubprocessStatus(id: number) {
  return request({ url: prefix + `templates/${id}/subprocess-status/`, method: 'get' })
}

export function UpdateSubprocessRefs(id: number) {
  return request({ url: prefix + `templates/${id}/update-subprocess-refs/`, method: 'post' })
}
