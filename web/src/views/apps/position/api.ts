import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/position/'

export function GetList(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
