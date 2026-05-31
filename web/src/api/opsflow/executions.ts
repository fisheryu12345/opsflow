import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetExecutions(params?: any) {
  return request({ url: prefix + 'executions/', method: 'get', params })
}

export function GetExecutionDetail(id: number) {
  return request({ url: prefix + `executions/${id}/`, method: 'get' })
}

export function CreateExecution(data: any) {
  return request({ url: prefix + 'executions/', method: 'post', data })
}

export function StartExecution(id: number) {
  return request({ url: prefix + `executions/${id}/start/`, method: 'post' })
}

export function PauseExecution(id: number) {
  return request({ url: prefix + `executions/${id}/pause/`, method: 'post' })
}

export function ResumeExecution(id: number) {
  return request({ url: prefix + `executions/${id}/resume/`, method: 'post' })
}

export function RetryNode(id: number, node_id: string) {
  return request({ url: prefix + `executions/${id}/retry_node/`, method: 'post', data: { node_id } })
}

export function SkipNode(id: number, node_id: string) {
  return request({ url: prefix + `executions/${id}/skip_node/`, method: 'post', data: { node_id } })
}

export function CancelExecution(id: number) {
  return request({ url: prefix + `executions/${id}/cancel/`, method: 'post' })
}
