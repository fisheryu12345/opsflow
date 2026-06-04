/**
 * 监控告警中心 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/monitor'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

export const alertRuleApi = createCrudApi('alert-rules')
export const alertEventApi = createCrudApi('alert-events')
export const targetApi = createCrudApi('targets')

export function ToggleAlertRule(id: string) {
  return request({ url: `${prefix}/alert-rules/${id}/toggle/`, method: 'post' })
}

export function AcknowledgeAlert(id: string) {
  return request({ url: `${prefix}/alert-events/${id}/acknowledge/`, method: 'post' })
}

export function CreateIncidentFromAlert(id: string) {
  return request({ url: `${prefix}/alert-events/${id}/create_incident/`, method: 'post' })
}

export function ToggleTarget(id: string) {
  return request({ url: `${prefix}/targets/${id}/toggle/`, method: 'post' })
}
