import { opsflowRequest, prefix, createCrudApi } from './request'

const T = prefix + 'templates/'

export const templateCrud = createCrudApi('templates')

export function CreateFromAi(data: { input: string; target_hosts?: string[]; global_vars?: any }) {
  return opsflowRequest({
    url: prefix + 'templates/create_from_ai/',
    method: 'post',
    data,
    timeout: 60000,
  })
}

export function CreateDrPipeline(data: { dr_group_id: string; target_hosts?: string[]; global_vars?: any }) {
  return opsflowRequest({
    url: prefix + 'templates/create_dr_pipeline/',
    method: 'post',
    data,
    timeout: 60000,
  })
}

export function ConfirmDraft(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/confirm_draft/`, method: 'post' })
}

export function GetDiff(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/diff/`, method: 'get' })
}

export function AiLayout(data: { nodes: any[]; edges: any[] }) {
  return opsflowRequest({
    url: prefix + 'templates/ai_layout/',
    method: 'post',
    data,
    timeout: 30000,
  })
}

export function AnalyzePipeline(data: { nodes: any[]; edges: any[] }) {
  return opsflowRequest({
    url: prefix + 'templates/analyze/',
    method: 'post',
    data,
    timeout: 30000,
  })
}

export function RefinePipeline(data: { input: string; nodes: any[]; edges: any[]; target_hosts?: string[]; chat_history?: { role: string; content: string }[] }) {
  return opsflowRequest({
    url: prefix + 'templates/refine/',
    method: 'post',
    data,
    timeout: 60000,
  })
}

/* ---------- Version management ---------- */
export function PublishTemplate(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/publish/`, method: 'post' })
}

export function GetTemplateVersions(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/versions/`, method: 'get' })
}

export function RollbackTemplate(id: number, version: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/rollback/`, method: 'post', data: { version } })
}

export function ExportTemplate(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/export/`, method: 'get' })
}

export function ImportTemplate(data: any) {
  return opsflowRequest({ url: prefix + 'templates/import_template/', method: 'post', data })
}

export function GetTemplateCategories() {
  return opsflowRequest({ url: prefix + 'templates/categories/', method: 'get' })
}

export function GetHookVariables(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/hook_variables/`, method: 'get' })
}

export function UpdateHookVariables(id: number, data: any) {
  return opsflowRequest({ url: prefix + `templates/${id}/hook_variables/`, method: 'post', data })
}

/* ---------- Global Variable System (Phase 1-2) ---------- */
export function GetGlobalVariables(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/global-variables/`, method: 'get' })
}

export function UpdateGlobalVariables(id: number, data: { global_vars: any }) {
  return opsflowRequest({ url: prefix + `templates/${id}/global-variables/`, method: 'post', data })
}

export function PatchGlobalVariables(id: number, data: { global_vars: any }) {
  return opsflowRequest({ url: prefix + `templates/${id}/global-variables/`, method: 'patch', data })
}

export function GetVariableBrowser(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/variable-browser/`, method: 'get' })
}

export function HookVariable(id: number, data: {
  var_key: string;
  node_id?: string;
  tag_code?: string;
  var_type?: string;
  description?: string;
  promote_type?: 'output' | 'input';
  meta?: Record<string, any>;
  value?: any;
}) {
  return opsflowRequest({ url: prefix + `templates/${id}/hook-variable/`, method: 'post', data })
}

export function UnhookVariable(id: number, data: { var_key: string }) {
  return opsflowRequest({ url: prefix + `templates/${id}/unhook-variable/`, method: 'post', data })
}

export function GetVariableTypes() {
  return opsflowRequest({ url: prefix + 'plugins/variable_types/', method: 'get' })
}

/* ---------- Subprocess Version Tracking (Phase 3-4) ---------- */
export function GetSubprocessStatus(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/subprocess-status/`, method: 'get' })
}

export function UpdateSubprocessRefs(id: number) {
  return opsflowRequest({ url: prefix + `templates/${id}/update-subprocess-refs/`, method: 'post' })
}

/* ---------- Execution Scheme Management ---------- */
export function GetSchemes(templateId: number) {
  return opsflowRequest({ url: prefix + `templates/${templateId}/schemes/`, method: 'get' })
}

export function CreateScheme(templateId: number, data: any) {
  return opsflowRequest({ url: prefix + `templates/${templateId}/schemes/`, method: 'post', data })
}

export function UpdateScheme(templateId: number, schemeId: number, data: any) {
  return opsflowRequest({ url: prefix + `templates/${templateId}/schemes/${schemeId}/`, method: 'patch', data })
}

export function DeleteScheme(templateId: number, schemeId: number) {
  return opsflowRequest({ url: prefix + `templates/${templateId}/schemes/${schemeId}/`, method: 'delete' })
}

/* ---------- CRUD named re-exports (for compatibility) ---------- */
export const GetTemplates = templateCrud.list
export const GetTemplateDetail = templateCrud.detail
export const CreateTemplate = templateCrud.create
export const UpdateTemplate = templateCrud.update
export const DeleteTemplate = templateCrud.delete
