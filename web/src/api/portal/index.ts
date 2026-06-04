/**
 * 运维门户 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/portal'

export function GetDashboard() {
  return request({ url: `${prefix}/dashboard/`, method: 'get' })
}

export function GetMyTasks() {
  return request({ url: `${prefix}/my-tasks/`, method: 'get' })
}

export function GetQuickStats() {
  return request({ url: `${prefix}/quick-stats/`, method: 'get' })
}
