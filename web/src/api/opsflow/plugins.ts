import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

/** Get all registered plugins (summary) */
export function GetPlugins(params?: any) {
  return request({ url: prefix + 'plugins/', method: 'get', params })
}

/** Get single plugin detail + full form_schema */
export function GetPluginDetail(code: string) {
  return request({ url: prefix + `plugins/${code}/`, method: 'get' })
}

/** Get plugin group tree */
export function GetPluginGroups() {
  return request({ url: prefix + 'plugins/groups/', method: 'get' })
}
