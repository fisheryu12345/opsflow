import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/strategy/'

export function GetList(params: any) {
  return request({ url: apiPrefix, method: 'get', params })
}

export function GetObj(id: number) {
  return request({ url: apiPrefix + id, method: 'get' })
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
