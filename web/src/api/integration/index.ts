/**
 * 集成中心 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/integration'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

export const connectorDefinitionApi = createCrudApi('connector-definitions')
export const connectorInstanceApi = createCrudApi('connector-instances')
export const credentialApi = createCrudApi('credentials')
export const callLogApi = createCrudApi('call-logs')

export function HealthCheck(id: string) {
  return request({ url: `${prefix}/connector-instances/${id}/health_check/`, method: 'post' })
}

export function ToggleInstance(id: string) {
  return request({ url: `${prefix}/connector-instances/${id}/toggle_active/`, method: 'post' })
}

export function DecryptCredential(id: string) {
  return request({ url: `${prefix}/credentials/${id}/decrypt/`, method: 'post' })
}
