import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

/** Get all projects */
export function GetProjects(params?: any) {
  return request({ url: prefix + 'projects/', method: 'get', params })
}

/** Get single project */
export function GetProjectDetail(id: number) {
  return request({ url: prefix + `projects/${id}/`, method: 'get' })
}

/** Create project */
export function CreateProject(data: { name: string; description?: string }) {
  return request({ url: prefix + 'projects/', method: 'post', data })
}

/** Update project */
export function UpdateProject(id: number, data: any) {
  return request({ url: prefix + `projects/${id}/`, method: 'patch', data })
}

/** Delete project */
export function DeleteProject(id: number) {
  return request({ url: prefix + `projects/${id}/`, method: 'delete' })
}
