/**
 * 开放 API 管理后台 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/open-api'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

export const apiAppApi = createCrudApi('apps')
export const apiTokenApi = createCrudApi('tokens')
export const webhookSubApi = createCrudApi('webhooks')
export const openApiLogApi = createCrudApi('call-logs')

export function RevokeToken(id: string) {
  return request({ url: `${prefix}/tokens/${id}/revoke/`, method: 'post' })
}
