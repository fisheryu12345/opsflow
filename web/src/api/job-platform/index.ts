/**
 * 作业平台 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/job-platform'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

export const scriptApi = createCrudApi('scripts')
export const jobApi = createCrudApi('jobs')
export const executionApi = createCrudApi('executions')
export const dangerousRuleApi = createCrudApi('dangerous-rules')

export function RunJob(id: string, targetHosts: string[], params?: any) {
  return request({ url: `${prefix}/jobs/${id}/run/`, method: 'post', data: { target_hosts: targetHosts, params } })
}

export function CancelExecution(id: string) {
  return request({ url: `${prefix}/executions/${id}/cancel/`, method: 'post' })
}

export function GetExecutionLog(id: string) {
  return request({ url: `${prefix}/executions/${id}/log/`, method: 'get' })
}
