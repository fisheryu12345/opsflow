import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetDashboardStats(params?: any) {
  return request({ url: prefix + 'dashboard/stats/', method: 'get', params })
}

export function GetDashboardTrend(params?: any) {
  return request({ url: prefix + 'dashboard/trend/', method: 'get', params })
}

export function GetDashboardScheduleStats(params?: any) {
  return request({ url: prefix + 'dashboard/schedule-stats/', method: 'get', params })
}

export function GetDashboardTopTemplates(params?: any) {
  return request({ url: prefix + 'dashboard/top-templates/', method: 'get', params })
}

export function GetDashboardUserActivity(params?: any) {
  return request({ url: prefix + 'dashboard/user-activity/', method: 'get', params })
}

export function GetDashboardStatusDistribution(params?: any) {
  return request({ url: prefix + 'dashboard/status-distribution/', method: 'get', params })
}

export function GetDashboardNodeTypeDistribution(params?: any) {
  return request({ url: prefix + 'dashboard/node-type-distribution/', method: 'get', params })
}

/* ---------- Stats & Analysis endpoints ---------- */

export function GetDashboardDurationDistribution(params?: any) {
  return request({ url: prefix + 'dashboard/duration-distribution/', method: 'get', params })
}

export function GetDashboardNodeDurationTop(params?: any) {
  return request({ url: prefix + 'dashboard/node-duration-top/', method: 'get', params })
}

export function GetDashboardSuccessRateTrend(params?: any) {
  return request({ url: prefix + 'dashboard/success-rate-trend/', method: 'get', params })
}

export function GetDashboardTemplateStats(params?: any) {
  return request({ url: prefix + 'dashboard/template-stats/', method: 'get', params })
}

/* ---------- Mock data (used when backend API is unavailable) ---------- */

function daysAgo(n: number): string {
  const d = new Date(Date.now() - n * 86400000)
  return d.toISOString().slice(0, 10)
}

export function getMockStats() {
  return {
    total_executions: 247,
    running_executions: 3,
    completed_executions: 198,
    failed_executions: 28,
    cancelled_executions: 12,
    paused_executions: 6,
    total_templates: 24,
    published_templates: 16,
    draft_templates: 8,
    total_users: 12,
    active_users_7d: 7,
    total_nodes_executed: 1842,
    avg_duration_sec: 186,
    success_rate: 87.6,
    /* scheduler fields */
    total_schedule_plans: 10,
    active_schedule_plans: 7,
    paused_schedule_plans: 2,
    completed_schedule_plans: 1,
    expired_schedule_plans: 0,
    total_scheduled_runs: 136,
    next_scheduled_run: { id: 1, name: '日常巡检', next_run_at: '2026-06-01 09:00:00' },
    scheduled_executions_total: 112,
    scheduled_executions_completed: 98,
    scheduled_executions_failed: 10,
    scheduled_executions_running: 4,
    schedule_success_rate: 90.7,
  }
}

export function getMockTrend() {
  const items: any[] = []
  for (let i = 29; i >= 0; i--) {
    const total = Math.floor(Math.random() * 8) + 2
    const completed = Math.floor(total * (0.7 + Math.random() * 0.25))
    const failed = Math.floor((total - completed) * (0.3 + Math.random() * 0.5))
    const cancelled = total - completed - failed
    items.push({
      date: daysAgo(i),
      total,
      completed,
      failed,
      cancelled,
      avg_duration: Math.floor(Math.random() * 120) + 60,
    })
  }
  return items
}

export function getMockTopTemplates() {
  return [
    { id: 1, name: '日常巡检流程', count: 68, avg_duration: 145, success_rate: 97.1 },
    { id: 2, name: '故障自愈 - Web 服务', count: 42, avg_duration: 230, success_rate: 88.1 },
    { id: 3, name: '数据库备份验证', count: 35, avg_duration: 310, success_rate: 94.3 },
    { id: 4, name: '应用发布 - 金丝雀部署', count: 28, avg_duration: 420, success_rate: 85.7 },
    { id: 5, name: '网络设备配置备份', count: 22, avg_duration: 180, success_rate: 100 },
    { id: 6, name: '安全漏洞扫描流程', count: 18, avg_duration: 560, success_rate: 94.4 },
    { id: 7, name: 'ESXi 虚拟机部署', count: 15, avg_duration: 890, success_rate: 80.0 },
    { id: 8, name: 'ServiceNow 变更审批', count: 10, avg_duration: 7200, success_rate: 90.0 },
  ]
}

export function getMockUserActivity() {
  return [
    { username: 'admin', execution_count: 98, template_count: 15, last_active: daysAgo(0) },
    { username: 'operator1', execution_count: 56, template_count: 4, last_active: daysAgo(0) },
    { username: 'operator2', execution_count: 42, template_count: 3, last_active: daysAgo(1) },
    { username: 'devops01', execution_count: 28, template_count: 6, last_active: daysAgo(2) },
    { username: 'devops02', execution_count: 15, template_count: 2, last_active: daysAgo(3) },
    { username: 'viewer', execution_count: 5, template_count: 0, last_active: daysAgo(5) },
    { username: 'auditor', execution_count: 3, template_count: 0, last_active: daysAgo(7) },
  ]
}

export function getMockStatusDistribution() {
  return [
    { status: 'completed', count: 198, label: 'Completed' },
    { status: 'failed', count: 28, label: 'Failed' },
    { status: 'running', count: 3, label: 'Running' },
    { status: 'paused', count: 6, label: 'Paused' },
    { status: 'cancelled', count: 12, label: 'Cancelled' },
  ]
}

export function getMockNodeTypeDistribution() {
  return [
    { type: 'ansible', count: 892, label: 'Ansible' },
    { type: 'http', count: 456, label: 'HTTP' },
    { type: 'servicenow', count: 234, label: 'ServiceNow' },
    { type: 'esxi', count: 120, label: 'ESXi' },
    { type: 'other', count: 140, label: 'Other' },
  ]
}

/* ---------- Stats & Analysis mock data ---------- */

export function getMockDurationDistribution() {
  return [
    { range: '0-30s', count: 85 },
    { range: '30s-1m', count: 52 },
    { range: '1m-3m', count: 38 },
    { range: '3m-5m', count: 22 },
    { range: '5m-10m', count: 15 },
    { range: '10m-1h', count: 8 },
    { range: '>1h', count: 3 },
  ]
}

export function getMockNodeDurationTop() {
  return [
    { atom_type: 'java_deploy', avg_duration: 28450, count: 32, max_duration: 62000 },
    { atom_type: 'docker_deploy', avg_duration: 15320, count: 18, max_duration: 45000 },
    { atom_type: 'create_vm', avg_duration: 12180, count: 8, max_duration: 35000 },
    { atom_type: 'shell', avg_duration: 8450, count: 128, max_duration: 60000 },
    { atom_type: 'script_exec', avg_duration: 6200, count: 45, max_duration: 28000 },
    { atom_type: 'service_control', avg_duration: 3800, count: 67, max_duration: 15000 },
    { atom_type: 'api_call', avg_duration: 2400, count: 92, max_duration: 12000 },
    { atom_type: 'file_copy', avg_duration: 1800, count: 56, max_duration: 8000 },
    { atom_type: 'ping_test', avg_duration: 450, count: 210, max_duration: 3000 },
    { atom_type: 'send_alert', avg_duration: 320, count: 88, max_duration: 1500 },
  ]
}

export function getMockSuccessRateTrend() {
  const items: any[] = []
  for (let i = 29; i >= 0; i--) {
    const total = Math.floor(Math.random() * 8) + 2
    const completed = Math.floor(total * (0.75 + Math.random() * 0.2))
    const failed = total - completed
    items.push({ date: daysAgo(i), total, completed, failed, rate: +(completed / total * 100).toFixed(1) })
  }
  return items
}

export function getMockTemplateStats() {
  return [
    { template_id: 1, name: '日常巡检流程', total: 68, avg_duration: 145, success_rate: 97.1 },
    { template_id: 2, name: '故障自愈 - Web 服务', total: 42, avg_duration: 230, success_rate: 88.1 },
    { template_id: 3, name: '数据库备份验证', total: 35, avg_duration: 310, success_rate: 94.3 },
    { template_id: 4, name: '应用发布 - 金丝雀部署', total: 28, avg_duration: 420, success_rate: 85.7 },
    { template_id: 5, name: '网络设备配置备份', total: 22, avg_duration: 180, success_rate: 100.0 },
    { template_id: 6, name: '安全漏洞扫描流程', total: 18, avg_duration: 560, success_rate: 94.4 },
    { template_id: 7, name: 'ESXi 虚拟机部署', total: 15, avg_duration: 890, success_rate: 80.0 },
    { template_id: 8, name: 'ServiceNow 变更审批', total: 10, avg_duration: 7200, success_rate: 90.0 },
  ]
}

/* ---------- Scheduler mock data ---------- */

export function getMockScheduleStats() {
  return {
    type_distribution: { one_time: 3, cron: 7 },
    top_schedules: [
      { id: 1, name: '日常巡检', template_name: '日常巡检流程', schedule_type: 'cron', total_run_count: 68, last_run_at: daysAgo(0), next_run_at: daysAgo(-1), is_active: true },
      { id: 2, name: '数据库备份验证', template_name: '数据库备份验证', schedule_type: 'cron', total_run_count: 35, last_run_at: daysAgo(0), next_run_at: daysAgo(-1), is_active: true },
      { id: 3, name: '网络设备备份', template_name: '网络设备配置备份', schedule_type: 'cron', total_run_count: 22, last_run_at: daysAgo(1), next_run_at: daysAgo(0), is_active: true },
      { id: 4, name: '安全漏洞扫描', template_name: '安全漏洞扫描流程', schedule_type: 'cron', total_run_count: 18, last_run_at: daysAgo(0), next_run_at: daysAgo(0), is_active: false },
      { id: 5, name: 'ESXi 快照备份', template_name: 'ESXi 虚拟机部署', schedule_type: 'one_time', total_run_count: 1, last_run_at: daysAgo(5), next_run_at: null, is_active: false },
    ],
    trend: Array.from({ length: 30 }, (_, i) => {
      const total = Math.floor(Math.random() * 5) + 1
      const completed = Math.floor(total * (0.7 + Math.random() * 0.25))
      const failed = total - completed
      return { date: daysAgo(29 - i), total, completed, failed }
    }),
  }
}
