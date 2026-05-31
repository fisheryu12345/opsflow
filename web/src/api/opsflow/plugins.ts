import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

/** 获取所有已注册插件列表（摘要信息） */
export function GetPlugins(params?: any) {
  return request({ url: prefix + 'plugins/', method: 'get', params })
}

/** 获取单个插件详情 + 完整 form_schema */
export function GetPluginDetail(code: string) {
  return request({ url: prefix + `plugins/${code}/`, method: 'get' })
}

/** 获取插件分组树 */
export function GetPluginGroups() {
  return request({ url: prefix + 'plugins/groups/', method: 'get' })
}
