import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

export function GetSchedulePlans(params?: any) {
  return opsflowRequest({ url: prefix + 'schedule-plans/', method: 'get', params })
}

export function GetSchedulePlanDetail(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/`, method: 'get' })
}

export function CreateSchedulePlan(data: any) {
  return opsflowRequest({ url: prefix + 'schedule-plans/', method: 'post', data })
}

export function UpdateSchedulePlan(id: number, data: any) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/`, method: 'patch', data })
}

export function DeleteSchedulePlan(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/`, method: 'delete' })
}

export function PauseSchedulePlan(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/pause/`, method: 'post' })
}

export function ResumeSchedulePlan(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/resume/`, method: 'post' })
}

export function TriggerSchedulePlan(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/trigger/`, method: 'post' })
}

export function GetSchedulePlanHistory(id: number) {
  return opsflowRequest({ url: prefix + `schedule-plans/${id}/history/`, method: 'get' })
}
