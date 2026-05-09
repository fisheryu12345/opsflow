import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/tradingaccount/'

export function getAccountList() {
  return request({
    url: apiPrefix,
    method: 'get',
  })
}
