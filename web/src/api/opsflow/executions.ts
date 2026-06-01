import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

export function GetExecutions(params?: any) {
  return opsflowRequest({ url: prefix + 'executions/', method: 'get', params })
}

export function GetExecutionDetail(id: number) {
  return opsflowRequest({ url: prefix + `executions/${id}/`, method: 'get' })
}

export function CreateExecution(data: any) {
  return opsflowRequest({ url: prefix + 'executions/', method: 'post', data })
}

export function StartExecution(id: number) {
  return opsflowRequest({ url: prefix + `executions/${id}/start/`, method: 'post' })
}

export function PauseExecution(id: number) {
  return opsflowRequest({ url: prefix + `executions/${id}/pause/`, method: 'post' })
}

export function ResumeExecution(id: number) {
  return opsflowRequest({ url: prefix + `executions/${id}/resume/`, method: 'post' })
}

export function RetryNode(id: number, node_id: string) {
  return opsflowRequest({ url: prefix + `executions/${id}/retry_node/`, method: 'post', data: { node_id } })
}

export function SkipNode(id: number, node_id: string) {
  return opsflowRequest({ url: prefix + `executions/${id}/skip_node/`, method: 'post', data: { node_id } })
}

export function CancelExecution(id: number) {
  return opsflowRequest({ url: prefix + `executions/${id}/cancel/`, method: 'post' })
}

export function ForceFailNode(id: number, node_id: string, reason?: string) {
  const data: any = { node_id }
  if (reason) data.reason = reason
  return opsflowRequest({ url: prefix + `executions/${id}/force_fail/`, method: 'post', data })
}

// -- Approval --

export function ApproveNode(id: number, node_id: string, comment?: string) {
  const data: any = { node_id }
  if (comment) data.comment = comment
  return opsflowRequest({ url: prefix + `executions/${id}/approve/`, method: 'post', data })
}

export function RejectNode(id: number, node_id: string, reason?: string) {
  const data: any = { node_id }
  if (reason) data.reason = reason
  return opsflowRequest({ url: prefix + `executions/${id}/reject/`, method: 'post', data })
}

// -- Batch operations --

export function BatchRetryNodes(id: number, node_ids?: string[]) {
  const data: any = {}
  if (node_ids) data.node_ids = node_ids
  return opsflowRequest({ url: prefix + `executions/${id}/batch_retry/`, method: 'post', data })
}

export function BatchSkipNodes(id: number, node_ids?: string[]) {
  const data: any = {}
  if (node_ids) data.node_ids = node_ids
  return opsflowRequest({ url: prefix + `executions/${id}/batch_skip/`, method: 'post', data })
}

// -- Pending Approval --

export function GetPendingApprovals() {
  return opsflowRequest({ url: prefix + 'executions/pending_approval/', method: 'get' })
}

export function RetrySubprocessNode(id: number, node_id: string) {
  return opsflowRequest({ url: prefix + `executions/${id}/retry_subprocess/`, method: 'post', data: { node_id } })
}

// -- Traces --

export function GetExecutionTraces(id: number, node_id?: string) {
  const params: any = {}
  if (node_id) params.node_id = node_id
  return opsflowRequest({ url: prefix + `executions/${id}/traces/`, method: 'get', params })
}

export function GetNodeTraceLog(id: number, node_id: string) {
  return opsflowRequest({ url: prefix + `executions/${id}/trace_log/`, method: 'get', params: { node_id } })
}
