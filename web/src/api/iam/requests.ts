import { request } from '/@/utils/service'

const prefix = '/api/iam/'

export function GetRequests(params?: any) {
  return request({ url: prefix + 'requests/', method: 'get', params })
}

export function GetRequestDetail(id: number) {
  return request({ url: prefix + `requests/${id}/`, method: 'get' })
}

export function CreateRequest(data: any) {
  return request({ url: prefix + 'requests/', method: 'post', data })
}

export function ApproveRequest(id: number, data?: any) {
  return request({ url: prefix + `requests/${id}/approve/`, method: 'post', data })
}

export function RejectRequest(id: number, data?: any) {
  return request({ url: prefix + `requests/${id}/reject/`, method: 'post', data })
}
