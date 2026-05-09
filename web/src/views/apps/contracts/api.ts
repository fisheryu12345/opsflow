import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/contracts/'

export function GetList(params: any) {
  return request({ url: apiPrefix, method: 'get', params })
}

export function GetStatistics() {
  return request({ url: apiPrefix + 'statistics/', method: 'get' })
}
