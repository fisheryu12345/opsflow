import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

export function GetLogs(params?: any) {
  return opsflowRequest({ url: prefix + 'logs/', method: 'get', params })
}

export function GetLogDetail(id: number) {
  return opsflowRequest({ url: prefix + `logs/${id}/`, method: 'get' })
}
