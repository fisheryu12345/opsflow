/**
 * 作业平台 API — 新版（匹配后端 17 个 ViewSet）
 */
import { request } from '/@/utils/service'

const prefix = '/api/job-platform'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

// ─── 基础资源 ───
export const accountsApi = createCrudApi('accounts')
export const fileSourcesApi = createCrudApi('file-sources')

// ─── 脚本管理 ───
export const scriptsApi = createCrudApi('scripts')

export function ScriptVersions(id: string) {
  return request({ url: `${prefix}/scripts/${id}/versions/`, method: 'get' })
}
export function PublishScript(id: string, data: { content?: string; changelog?: string }) {
  return request({ url: `${prefix}/scripts/${id}/publish/`, method: 'post', data })
}
export function ScriptReferences(id: string) {
  return request({ url: `${prefix}/scripts/${id}/references/`, method: 'get' })
}

// ─── 模板 / 方案 ───
export const templatesApi = createCrudApi('templates')
export const plansApi = createCrudApi('plans')
export const variablesApi = createCrudApi('variables')
export const stepsApi = createCrudApi('steps')

export function PublishTemplate(id: string) {
  return request({ url: `${prefix}/templates/${id}/publish/`, method: 'post' })
}
export function TemplatePlans(id: string) {
  return request({ url: `${prefix}/templates/${id}/plans/`, method: 'get' })
}
export function ExecutePlan(id: string, data?: { variables?: any; target_override?: any }) {
  return request({ url: `${prefix}/plans/${id}/execute/`, method: 'post', data })
}
export function MoveStep(id: string, data: { previous_step_id?: number; next_step_id?: number }) {
  return request({ url: `${prefix}/steps/${id}/move/`, method: 'post', data })
}

// ─── 执行管理 ───
export const executionsApi = createCrudApi('executions')
export const stepExecutionsApi = createCrudApi('step-executions')

export function StopExecution(id: string) {
  return request({ url: `${prefix}/executions/${id}/stop/`, method: 'post' })
}
export function RetryExecution(id: string) {
  return request({ url: `${prefix}/executions/${id}/retry/`, method: 'post' })
}
export function ExecutionSteps(id: string) {
  return request({ url: `${prefix}/executions/${id}/steps/`, method: 'get' })
}
export function ExecutionLog(id: string) {
  return request({ url: `${prefix}/executions/${id}/log/`, method: 'get' })
}

// ─── 快速执行 ───
export const quickExecApi = {
  script: (data: { content?: string; script_id?: string; target_hosts: string[]; params?: any; executor?: string }) =>
    request({ url: `${prefix}/quick-exec/`, method: 'post', data }),
  file: (data: any) =>
    request({ url: `${prefix}/quick-exec/file/`, method: 'post', data }),
}

// ─── 高危命令 ───
export const dangerousRulesApi = createCrudApi('dangerous-rules')
export const dangerousLogsApi = createCrudApi('dangerous-logs')

export function CheckDangerousCommand(data: { command: string; script_type?: string }) {
  return request({ url: `${prefix}/dangerous-rules/check/`, method: 'post', data })
}

// ─── 定时作业 ───
export const cronJobsApi = createCrudApi('cron-jobs')

export function ToggleCronJob(id: string) {
  return request({ url: `${prefix}/cron-jobs/${id}/toggle/`, method: 'post' })
}
export function ExecuteCronNow(id: string) {
  return request({ url: `${prefix}/cron-jobs/${id}/execute-now/`, method: 'post' })
}
export function CronJobHistory(id: string) {
  return request({ url: `${prefix}/cron-jobs/${id}/history/`, method: 'get' })
}

// ─── 仪表盘 ───
export function GetJobDashboard() {
  return request({ url: `${prefix}/dashboard/`, method: 'get' })
}
