import { opsflowRequest } from './request'

export function GetTemplateCategories(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/template-categories/', method: 'get', params })
}
