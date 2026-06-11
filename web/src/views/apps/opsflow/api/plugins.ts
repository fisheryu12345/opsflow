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
export function GetPluginGroups(params?: any) {
  return opsflowRequest({ url: prefix + 'plugins/groups/', method: 'get', params })
}

/** Get single plugin visibility config */
export function GetPluginVisibility(code: string) {
  return opsflowRequest({ url: prefix + `plugins/${code}/visibility/`, method: 'get' })
}

/** Set single plugin visibility (project whitelist) */
export function SetPluginVisibility(code: string, project_ids: number[]) {
  return opsflowRequest({
    url: prefix + `plugins/${code}/visibility/`,
    method: 'post',
    data: { project_ids },
  })
}

/** Get all plugins visibility list (for admin panel) */
export function GetPluginsVisibilityList() {
  return opsflowRequest({ url: prefix + 'plugins/visibility-list/', method: 'get' })
}

/** Batch update plugin visibility */
export function BatchSetPluginsVisibility(plugins: { code: string; project_ids: number[] }[]) {
  return opsflowRequest({
    url: prefix + 'plugins/batch-visibility/',
    method: 'post',
    data: { plugins },
  })
}

/** Scan plugin directory and register new plugins (hot reload) */
export function ReloadPlugins() {
  return opsflowRequest({ url: prefix + 'plugins/reload/', method: 'post' })
}
