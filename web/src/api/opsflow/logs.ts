import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetLogs(params?: any) {
  return request({ url: prefix + 'logs/', method: 'get', params })
}

export function GetLogDetail(id: number) {
  return request({ url: prefix + `logs/${id}/`, method: 'get' })
}
