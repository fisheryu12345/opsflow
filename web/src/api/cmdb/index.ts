/**
 * CMDB API
 */
import { request } from '/@/utils/service'

const prefix = '/api/cmdb'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

export const modelDefinitionApi = createCrudApi('model-definitions')
export const modelFieldApi = createCrudApi('model-fields')
export const bizApi = createCrudApi('bizs')
export const setApi = createCrudApi('sets')
export const moduleApi = createCrudApi('modules')
export const hostApi = createCrudApi('hosts')
export const topologyApi = createCrudApi('topology')

export function GetBizTopology(id: string) {
  return request({ url: `${prefix}/bizs/${id}/topology/`, method: 'get' })
}

export function GetHostGraph(params: { ip?: string; hostname?: string }) {
  return request({ url: `${prefix}/topology/host_graph/`, method: 'get', params })
}

export function GetImpactAnalysis(params: { node_id: string; node_type?: string }) {
  return request({ url: `${prefix}/topology/impact/`, method: 'get', params })
}

export function SearchNodes(q: string) {
  return request({ url: `${prefix}/topology/search/`, method: 'get', params: { q } })
}

export function BatchImportHosts(data: any[]) {
  return request({ url: `${prefix}/hosts/batch_import/`, method: 'post', data })
}
