import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/closed-positions/'

export function GetList(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
