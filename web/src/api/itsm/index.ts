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

// ===== Legacy ITSM (Incident/Change models) =====
export const incidentApi = createCrudApi('incidents')
export const changeApi = createCrudApi('changes')
export const serviceRequestApi = createCrudApi('service-requests')
export const problemApi = createCrudApi('problems')
export const serviceCategoryApi = createCrudApi('service-categories')
export const slaPolicyApi = createCrudApi('sla-policies')

export function AssignIncident(id: string, userId: number) {
  return request({ url: `${prefix}/incidents/${id}/assign/`, method: 'post', data: { user_id: userId } })
}
export function ResolveIncident(id: string, resolution: string) {
  return request({ url: `${prefix}/incidents/${id}/resolve/`, method: 'post', data: { resolution } })
}
export function CloseIncident(id: string) {
  return request({ url: `${prefix}/incidents/${id}/close/`, method: 'post' })
}
export function ApproveChange(id: string, note?: string) {
  return request({ url: `${prefix}/changes/${id}/approve/`, method: 'post', data: { note } })
}
export function RejectChange(id: string, note?: string) {
  return request({ url: `${prefix}/changes/${id}/reject/`, method: 'post', data: { note } })
}

// ===== Workflow Engine (pipeline-driven) =====
export const workflowApi = createCrudApi('workflows')
export const workflowVersionApi = createCrudApi('workflow-versions')
export const stateApi = createCrudApi('states')
export const transitionApi = createCrudApi('transitions')
export const fieldApi = createCrudApi('fields')
export const ticketApi = createCrudApi('tickets')

// Workflow deploy
export function DeployWorkflow(id: string, message?: string) {
  return request({ url: `${prefix}/workflows/${id}/deploy/`, method: 'post', data: { message } })
}

// Ticket operations
export function SubmitTicket(id: string) {
  return request({ url: `${prefix}/tickets/${id}/submit/`, method: 'post' })
}
export function ApproveTicketNode(id: string, stateId: number, comment?: string) {
  return request({ url: `${prefix}/tickets/${id}/approve/`, method: 'post', data: { state_id: stateId, comment } })
}
export function RejectTicketNode(id: string, stateId: number, comment?: string) {
  return request({ url: `${prefix}/tickets/${id}/reject/`, method: 'post', data: { state_id: stateId, comment } })
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
