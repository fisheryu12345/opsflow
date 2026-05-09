import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/daily_signals/'

export function GetList(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
