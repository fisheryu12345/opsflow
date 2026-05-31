import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetAuditLogs(params?: any) {
  return request({ url: prefix + 'audit/', method: 'get', params })
}

export function GetAuditDetail(id: number) {
  return request({ url: prefix + `audit/${id}/`, method: 'get' })
}

/* Collection */
export function CollectTemplate(id: number) {
  return request({ url: prefix + `templates/${id}/collect/`, method: 'post' })
}

export function UncollectTemplate(id: number) {
  return request({ url: prefix + `templates/${id}/uncollect/`, method: 'post' })
}

export function IsTemplateCollected(id: number) {
  return request({ url: prefix + `templates/${id}/is_collected/`, method: 'get' })
}
