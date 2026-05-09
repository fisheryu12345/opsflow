import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/contracts/'

export function GetList(params: any) {
  return request({ url: apiPrefix, method: 'get', params })
}

export function GetObj(id: number) {
  return request({ url: apiPrefix + id + '/', method: 'get' })
}

export function AddObj(obj: any) {
  return request({ url: apiPrefix, method: 'post', data: obj })
}

export function UpdateObj(obj: any) {
  return request({ url: apiPrefix + obj.id + '/', method: 'put', data: obj })
}

export function DelObj(id: number) {
  return request({ url: apiPrefix + id + '/', method: 'delete' })
}

export function ActivateContracts(ids: number[]) {
  return request({ url: apiPrefix + 'activate/', method: 'post', data: { ids } })
}

export function DeactivateContracts(ids: number[]) {
  return request({ url: apiPrefix + 'deactivate/', method: 'post', data: { ids } })
}

export function ToggleActive(id: number) {
  return request({ url: apiPrefix + id + '/toggle_active/', method: 'post' })
}

export function GetStatistics() {
  return request({ url: apiPrefix + 'statistics/', method: 'get' })
}

export function GetExchanges() {
  return request({ url: apiPrefix + 'exchanges/', method: 'get' })
}
