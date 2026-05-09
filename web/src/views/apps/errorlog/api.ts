import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/error_log/'

export function GetList(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}

export function DelObj(id: number) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
  })
}
