/**
 * 运维门户 API
 */
import { request } from '/@/utils/service'

const prefix = '/api/portal'

/**
 * 获取门户首页聚合数据
 */
export function GetDashboard() {
  return request({ url: `${prefix}/dashboard/`, method: 'get' })
}

/**
 * 获取我的待办
 */
export function GetMyTasks() {
  return request({ url: `${prefix}/my-tasks/`, method: 'get' })
}

/**
 * 快速概览统计
 */
export function GetQuickStats() {
  return request({ url: `${prefix}/quick-stats/`, method: 'get' })
}

/**
 * 获取近期系统活动
 * @param limit 返回条数，默认 20
 * @param hours 查询最近几小时，默认 72
 */
export function GetRecentActivity(limit = 20, hours = 72) {
  return request({
    url: `${prefix}/recent-activity/`,
    method: 'get',
    params: { limit, hours },
  })
}

/**
 * 获取用户收藏/最近操作
 */
export function GetFavorites() {
  return request({ url: `${prefix}/favorites/`, method: 'get' })
}

/**
 * 系统健康检查
 */
export function GetHealth() {
  return request({ url: `${prefix}/health/`, method: 'get' })
}
