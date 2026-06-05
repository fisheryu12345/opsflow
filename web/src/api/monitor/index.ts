/**
 * 监控告警中心 API — 策略/告警事件/通知组/分派/屏蔽/采集/看板
 */
import { request } from '/@/utils/service'

const prefix = '/api/monitor'

/** 通用 CRUD API 工厂 */
function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: number | string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: number | string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: number | string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

// ═══════════════════════════════════════════════
// 策略管理
// ═══════════════════════════════════════════════
export const strategyApi = {
  ...createCrudApi('strategies'),
  toggle: (id: number) => request({ url: `${prefix}/strategies/${id}/toggle/`, method: 'post' }),
  clone: (id: number) => request({ url: `${prefix}/strategies/${id}/clone/`, method: 'post' }),
  validate: (data: any) => request({ url: `${prefix}/strategies/validate/`, method: 'post', data }),
}

export const itemApi = createCrudApi('items')

// ═══════════════════════════════════════════════
// 告警事件
// ═══════════════════════════════════════════════
export const alertEventApi = {
  ...createCrudApi('alert-events'),
  clear: (days?: number) => request({ url: `${prefix}/alert-events/clear/`, method: 'post', data: { days: days || 30 } }),
}

export const alertApi = {
  ...createCrudApi('alerts'),
  acknowledge: (id: number) => request({ url: `${prefix}/alerts/${id}/acknowledge/`, method: 'post' }),
  resolve: (id: number) => request({ url: `${prefix}/alerts/${id}/resolve/`, method: 'post' }),
  close: (id: number) => request({ url: `${prefix}/alerts/${id}/close/`, method: 'post' }),
  assign: (id: number, assignee: string) => request({ url: `${prefix}/alerts/${id}/assign/`, method: 'post', data: { assignee } }),
  batchAck: (ids: number[]) => request({ url: `${prefix}/alerts/batch_ack/`, method: 'post', data: { ids } }),
  batchClose: (ids: number[]) => request({ url: `${prefix}/alerts/batch_close/`, method: 'post', data: { ids } }),
  createIncident: (id: number) => request({ url: `${prefix}/alerts/${id}/create_incident/`, method: 'post' }),
}

// ═══════════════════════════════════════════════
// 通知组 & 值班
// ═══════════════════════════════════════════════
export const notifyGroupApi = {
  ...createCrudApi('notify-groups'),
  testNotify: (id: number, channel: string) =>
    request({ url: `${prefix}/notify-groups/${id}/test_notify/`, method: 'post', data: { channel } }),
}

export const dutyPlanApi = {
  ...createCrudApi('duty-plans'),
  calendar: (id: number, year: number, month: number) =>
    request({ url: `${prefix}/duty-plans/${id}/calendar/`, method: 'get', params: { year, month } }),
}

export const dutyArrangeApi = createCrudApi('duty-arranges')

// ═══════════════════════════════════════════════
// 告警分派 & 动作插件
// ═══════════════════════════════════════════════
export const assignGroupApi = {
  ...createCrudApi('assign-groups'),
  reorder: (ids: number[]) => request({ url: `${prefix}/assign-groups/reorder/`, method: 'post', data: { ids } }),
}

export const actionPluginApi = {
  ...createCrudApi('action-plugins'),
  test: (id: number) => request({ url: `${prefix}/action-plugins/${id}/test/`, method: 'post' }),
}

// ═══════════════════════════════════════════════
// 屏蔽计划 & 采集配置
// ═══════════════════════════════════════════════
export const shieldPlanApi = {
  ...createCrudApi('shield-plans'),
  toggle: (id: number) => request({ url: `${prefix}/shield-plans/${id}/toggle/`, method: 'post' }),
}

export const collectConfigApi = {
  ...createCrudApi('collect-configs'),
  test: (id: number) => request({ url: `${prefix}/collect-configs/${id}/test/`, method: 'post' }),
}

// ═══════════════════════════════════════════════
// 看板 & 统计
// ═══════════════════════════════════════════════
export const dashboardApi = {
  summary: () => request({ url: `${prefix}/dashboard/summary/`, method: 'get' }),
  trend: (days?: number) => request({ url: `${prefix}/dashboard/trend/`, method: 'get', params: { days } }),
  severityDist: () => request({ url: `${prefix}/dashboard/severity_dist/`, method: 'get' }),
  topAlerts: (n?: number) => request({ url: `${prefix}/dashboard/top_alerts/`, method: 'get', params: { n } }),
  statusDist: () => request({ url: `${prefix}/dashboard/status_dist/`, method: 'get' }),
  durationDist: () => request({ url: `${prefix}/dashboard/duration_dist/`, method: 'get' }),
}
