import { request } from '/@/utils/service'

const apiPrefix = '/api/ops/'

export function RunTask(input: string, environment_id?: number) {
  return request({
    url: apiPrefix + 'run/',
    method: 'post',
    data: { input, environment_id },
    timeout: 120000,
  })
}

export function GetTaskResult(session_id: string) {
  return request({
    url: apiPrefix + `run/${session_id}/`,
    method: 'get',
  })
}

export function GetSessions(params: any) {
  return request({
    url: apiPrefix + 'session/',
    method: 'get',
    params,
  })
}

export function GetSessionDetail(id: number) {
  return request({
    url: apiPrefix + `session/${id}/`,
    method: 'get',
  })
}
