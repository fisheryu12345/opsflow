/**
 * OpsFlow API 请求包装器 — 自动注入当前 project_id
 *
 * 所有 opsflow API 文件应改用此模块代替直接使用 service.ts。
 * 读取 opsflowStore.currentProjectId 自动附加 ?project_id=X 参数。
 */

import { request } from '/@/utils/service'

// 在模块作用域内无法直接 useOpsflowStore（需要 pinia 实例），
// 采用全局变量方式由 store 初始化时设入
let _currentProjectId: number | null = null

export function setProjectId(id: number | null) {
  _currentProjectId = id
}

export function getProjectId(): number | null {
  return _currentProjectId
}

export function opsflowRequest(config: any) {
  const params = { ...(config.params || {}) }
  if (_currentProjectId) {
    params.project_id = _currentProjectId
  }
  return request({ ...config, params })
}

/** API 基础路径 — 所有 opsflow API 文件应统一引用此常量 */
export const prefix = '/api/opsflow'

/**
 * CRUD API 工厂 — 减少重复的 5 函数模板代码
 *
 * 用法：const api = createCrudApi('templates')
 * // 即可使用 api.list(), api.detail(id), api.create(data), api.update(id, data), api.delete(id)
 */
export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => opsflowRequest({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: number) => opsflowRequest({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => opsflowRequest({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: number, data: any) => opsflowRequest({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: number) => opsflowRequest({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}
