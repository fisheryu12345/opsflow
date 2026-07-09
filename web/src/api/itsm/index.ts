/**
 * ITSM API — 事件/变更 + 工作流引擎 + AI 生成 + 看板 + 委托
 */
import { request } from '/@/utils/service'

const prefix = '/api/itsm'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

// ===== Service Catalog & SLA =====
export const serviceCategoryApi = createCrudApi('service-categories')
export const slaPolicyApi = createCrudApi('sla-policies')

// ===== Workflow Engine (pipeline-driven) =====
export const workflowApi = createCrudApi('workflows')
export const workflowVersionApi = createCrudApi('workflow-versions')
export const stateApi = createCrudApi('states')
export const transitionApi = createCrudApi('transitions')
export const fieldApi = createCrudApi('fields')
// Rollback workflow version
export function RollbackVersion(id: string, message?: string) {
  return request({ url: prefix + '/workflow-versions/' + id + '/rollback/', method: 'post', data: { message } })
}
export const ticketApi = createCrudApi('tickets')

// Workflow deploy
export function DeployWorkflow(id: string, message?: string) {
  return request({ url: `${prefix}/workflows/${id}/deploy/`, method: 'post', data: { message } })
}

// Designer sync operations
export function StateSync(workflowId: number, states: any[]) {
  return request({ url: `${prefix}/states/sync/`, method: 'post', data: { workflow_id: workflowId, states } })
}
export function TransitionSync(workflowId: number, transitions: any[]) {
  return request({ url: `${prefix}/transitions/sync/`, method: 'post', data: { workflow_id: workflowId, transitions } })
}
export function FieldBatchUpdate(stateId: number, fields: any[]) {
  return request({ url: `${prefix}/fields/batch_update/`, method: 'post', data: { state_id: stateId, fields } })
}
export function UploadTicketFile(id: number, file: File, fieldKey?: string) {
  const formData = new FormData()
  formData.append('file', file)
  if (fieldKey) formData.append('field_key', fieldKey)
  return request({ url: `${prefix}/tickets/${id}/upload-file/`, method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}

// Ticket operations
export function SubmitTicket(id: string) {
  return request({ url: `${prefix}/tickets/${id}/submit/`, method: 'post' })
}
export function NodeSubmit(id: string, data: { state_id: number; fields: Record<string, any> }) {
  return request({ url: `${prefix}/tickets/${id}/node_submit/`, method: 'post', data })
}
export function ApproveTicketNode(id: string, stateId: number, comment?: string, fields?: Record<string, any>) {
  return request({ url: `${prefix}/tickets/${id}/approve/`, method: 'post', data: { state_id: stateId, comment, fields } })
}
export function RejectTicketNode(id: string, stateId: number, comment?: string, fields?: Record<string, any>) {
  return request({ url: `${prefix}/tickets/${id}/reject/`, method: 'post', data: { state_id: stateId, comment, fields } })
}
export function SuspendTicket(id: string) {
  return request({ url: `${prefix}/tickets/${id}/suspend/`, method: 'post' })
}
export function ResumeTicket(id: string) {
  return request({ url: `${prefix}/tickets/${id}/resume/`, method: 'post' })
}
export function CloseTicket(id: string) {
  return request({ url: `${prefix}/tickets/${id}/close/`, method: 'post' })
}
export function AssignTicket(id: string, userId: number, reason?: string) {
  return request({ url: `${prefix}/tickets/${id}/assign/`, method: 'post', data: { user_id: userId, reason } })
}

// ===== Service Catalog（服务目录） =====
export const serviceItemApi = createCrudApi('service-items')
export function SubmitServiceItem(id: string | number, data: { form_data?: Record<string, any>; title?: string; priority?: string }) {
  return request({ url: `${prefix}/service-items/${id}/submit/`, method: 'post', data })
}
export function GetTicketStatus(id: string) {
  return request({ url: `${prefix}/tickets/${id}/status/`, method: 'get' })
}

// ===== AI Generation =====
export function AIGenerateWorkflow(description: string, itsmType?: string) {
  return request({ url: `${prefix}/ai/generate-workflow/`, method: 'post', data: { description, itsm_type: itsmType || 'change' } })
}
export function AIGenerateFields(description: string) {
  return request({ url: `${prefix}/ai/generate-fields/`, method: 'post', data: { description } })
}

// ===== Dashboard (看板) =====
export const dashboardApi = {
  summary: () => request({ url: `${prefix}/dashboard/summary/`, method: 'get' }),
  myTasks: () => request({ url: `${prefix}/dashboard/my_tasks/`, method: 'get' }),
  trend: () => request({ url: `${prefix}/dashboard/trend/`, method: 'get' }),
  statusDist: () => request({ url: `${prefix}/dashboard/status_dist/`, method: 'get' }),
  overdue: () => request({ url: `${prefix}/dashboard/overdue/`, method: 'get' }),
}

// ===== Delegation (审批委托) =====
export const delegationApi = createCrudApi('delegations')
export function ToggleDelegation(id: string) {
  return request({ url: `${prefix}/delegations/${id}/toggle_active/`, method: 'post' })
}
export function GetMyDelegations() {
  return request({ url: `${prefix}/delegations/my_delegations/`, method: 'get' })
}

// ===== Escalation (升级层级) =====
export const escalationApi = createCrudApi('escalation-levels')

