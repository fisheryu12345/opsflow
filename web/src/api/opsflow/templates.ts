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
