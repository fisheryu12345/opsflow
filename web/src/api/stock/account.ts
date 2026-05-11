import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/tradingaccount/'

export function getAccountList() {
  return request({
    url: apiPrefix,
    method: 'get',
  })
}

export function updateAccount(id: number, data: Record<string, any>) {
  return request({
    url: apiPrefix + id + '/',
    method: 'put',
    data,
  })
}

export function patchAccount(id: number, data: Record<string, any>) {
  return request({
    url: apiPrefix + id + '/',
    method: 'patch',
    data,
  })
}
