import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

/** Get all registered plugins (summary) */
export function GetPlugins(params?: any) {
  return opsflowRequest({ url: prefix + 'plugins/', method: 'get', params })
}

/** Get single plugin detail + full form_schema */
export function GetPluginDetail(code: string) {
  return opsflowRequest({ url: prefix + `plugins/${code}/`, method: 'get' })
}

/** Get plugin group tree */
export function GetPluginGroups() {
  return opsflowRequest({ url: prefix + 'plugins/groups/', method: 'get' })
}
