/** Agent API client */
import request from '/@/utils/request'

/** Standard OpsFlow detail response wrapper */
export interface DetailResponse<T> {
  code: number
  data: T
  msg: string
}

/** Standard OpsFlow paginated list response */
export interface PaginatedResponse<T> {
  code: number
  data: {
    results: T[]
    count: number
  }
  msg: string
}

export interface AgentInstance {
  id: number
  agent_id: string
  hostname: string
  ip: string
  os_type: string
  os_version: string
  arch: string
  agent_version: string
  status: 'online' | 'offline' | 'unknown'
  last_heartbeat: string
  enable_collect: boolean
  enable_file: boolean
  upgrade_status: string
  tags: Record<string, string>
}

export interface AgentTask {
  id: number
  exec_id: string
  task_source: string
  script_type: string
  status: string
  exit_code: number | null
  target_host: string
  start_time: string
  finish_time: string
}

export interface AgentStats {
  total: number
  online: number
  offline: number
  upgrading: number
}

/** Get agent list */
export function getAgentList(params?: any) {
  return request({ url: '/api/agent/agents/', method: 'get', params })
}

/** Get agent detail */
export function getAgentDetail(id: number) {
  return request({ url: `/api/agent/agents/${id}/`, method: 'get' })
}

/** Update agent */
export function updateAgent(id: number, data: Partial<AgentInstance>) {
  return request({ url: `/api/agent/agents/${id}/`, method: 'patch', data })
}

/** Get dashboard stats */
export function getAgentStats() {
  return request({ url: '/api/agent/agents/stats/', method: 'get' })
}

/** Refresh agent token */
export function refreshAgentToken(id: number) {
  return request({ url: `/api/agent/agents/${id}/refresh_token/`, method: 'post' })
}

/** Execute command on agent */
export function execCommand(data: any) {
  return request({ url: '/api/agent/tasks/exec/', method: 'post', data })
}

/** Get task detail */
export function getTaskDetail(execId: string) {
  return request({ url: `/api/agent/tasks/${execId}/`, method: 'get' })
}

/** Get task results */
export function getTaskResults(execId: string) {
  return request({ url: `/api/agent/tasks/${execId}/result/`, method: 'get' })
}

/** Get task list */
export function getTaskList(params?: any) {
  return request({ url: '/api/agent/tasks/', method: 'get', params })
}

/** Push file (multipart upload) */
export function pushFile(formData: FormData) {
  return request({ url: '/api/agent/files/push/', method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}

/** Pull file */
export function pullFile(data: any) {
  return request({ url: '/api/agent/files/pull/', method: 'post', data })
}

/** Get file task list */
export function getFileTaskList(params?: any) {
  return request({ url: '/api/agent/files/', method: 'get', params })
}

/** Get upgrade list */
export function getUpgradeList(params?: any) {
  return request({ url: '/api/agent/upgrades/', method: 'get', params })
}

/** Trigger upgrade */
export function triggerUpgrade(data: any) {
  return request({ url: '/api/agent/agents/upgrade/', method: 'post', data })
}

/** SSH push install agent on target hosts */
export function pushInstall(data: {
  hosts: string[]
  username: string
  password?: string
  ssh_key?: string
  port?: number
  agent_version?: string
  server_host?: string
}) {
  return request({ url: '/api/agent/agents/push_install/', method: 'post', data })
}

/** Get processes from Neo4j by host IP */
export function getAgentProcesses(hostIp: string) {
  return request({ url: '/api/agent/processes/', method: 'get', params: { host_ip: hostIp } })
}

/** Register app on agent */
export function registerAgentApp(agentId: string, data: {
  name: string
  command: string
  user?: string
  stop_command?: string
  pid_file?: string
  auto_restart?: boolean
}) {
  return request({ url: '/api/agent/internal/apps/', method: 'post', data: { ...data, action: 'register', agent_id: agentId } })
}

/** Get registered apps */
export function getAgentApps(agentId: string) {
  return request({ url: '/api/agent/internal/apps/', method: 'get', params: { agent_id: agentId } })
}

/** Set agent config (app_users whitelist etc.) */
export function setAgentConfig(agentId: number, data: { app_users: string[] }) {
  return request({ url: `/api/agent/agents/${agentId}/set_config/`, method: 'post', data })
}

/** Unregister app on agent */
export function unregisterAgentApp(agentId: string, name: string) {
  return request({ url: '/api/agent/internal/apps/', method: 'post', data: { action: 'unregister', agent_id: agentId, name } })
}
