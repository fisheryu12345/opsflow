/**
 * ITSM API
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
