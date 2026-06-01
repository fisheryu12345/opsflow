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
