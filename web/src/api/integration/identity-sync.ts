/**
 * Identity Sync API — LDAP/AD/SAML 身份同步相关调用
 */
import { request } from '/@/utils/service'

const base = '/api/iam/sync'

/** 获取所有身份同步源的同步状态概览 */
export function getSyncStatus() {
  return request({ url: `${base}/status/`, method: 'get' })
}

/** 触发指定实例的全量同步 */
export function triggerSync(instanceId: number) {
  return request({ url: `${base}/${instanceId}/trigger/`, method: 'post' })
}

/** 测试指定实例的连接 */
export function testConnection(instanceId: number) {
  return request({ url: `${base}/${instanceId}/test-connect/`, method: 'post' })
}

/** 获取指定实例的同步历史 */
export function getSyncHistory(instanceId: number) {
  return request({ url: `${base}/${instanceId}/history/`, method: 'get' })
}
