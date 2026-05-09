import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/trade_log/'

export function GetList(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
