import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/account-contracts/'

export function GetList(params?: any) {
  return request({ url: apiPrefix, method: 'get', params })
}

export function ToggleProduct(data: { product_code: string; account?: number }) {
  return request({ url: apiPrefix + 'toggle/', method: 'post', data })
}

export function GetAvailable(params?: { account?: number }) {
  return request({ url: apiPrefix + 'available/', method: 'get', params })
}

export function BatchToggle(data: { product_codes: string[]; active: boolean; account?: number }) {
  return request({ url: apiPrefix + 'batch_toggle/', method: 'post', data })
}
