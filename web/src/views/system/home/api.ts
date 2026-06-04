/**
 * OpsFlow Dashboard API
 */
import { opsflowRequest } from '/@/views/apps/opsflow/api/request'

export function GetDashboardStats(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/dashboard/stats/', method: 'get', params })
}

export function GetDashboardTrend(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/dashboard/trend/', method: 'get', params })
}

export function GetDashboardTopTemplates(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/dashboard/top-templates/', method: 'get', params })
}

export function GetDashboardUserActivity(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/dashboard/user-activity/', method: 'get', params })
}

export function GetDashboardStatusDistribution(params?: any) {
  return opsflowRequest({ url: '/api/opsflow/dashboard/status-distribution/', method: 'get', params })
}
