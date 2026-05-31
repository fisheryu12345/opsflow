import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

export function GetSchedulePlans(params?: any) {
  return request({ url: prefix + 'schedule-plans/', method: 'get', params })
}

export function GetSchedulePlanDetail(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/`, method: 'get' })
}

export function CreateSchedulePlan(data: any) {
  return request({ url: prefix + 'schedule-plans/', method: 'post', data })
}

export function UpdateSchedulePlan(id: number, data: any) {
  return request({ url: prefix + `schedule-plans/${id}/`, method: 'patch', data })
}

export function DeleteSchedulePlan(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/`, method: 'delete' })
}

export function PauseSchedulePlan(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/pause/`, method: 'post' })
}

export function ResumeSchedulePlan(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/resume/`, method: 'post' })
}

export function TriggerSchedulePlan(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/trigger/`, method: 'post' })
}

export function GetSchedulePlanHistory(id: number) {
  return request({ url: prefix + `schedule-plans/${id}/history/`, method: 'get' })
}
