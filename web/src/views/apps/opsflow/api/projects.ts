import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

/** Get all projects */
export function GetProjects(params?: any) {
  return opsflowRequest({ url: prefix + 'projects/', method: 'get', params })
}

/** Get single project */
export function GetProjectDetail(id: number) {
  return opsflowRequest({ url: prefix + `projects/${id}/`, method: 'get' })
}

/** Create project */
export function CreateProject(data: { name: string; description?: string; max_schedule_plans?: number }) {
  return opsflowRequest({ url: prefix + 'projects/', method: 'post', data })
}

/** Update project */
export function UpdateProject(id: number, data: any) {
  return opsflowRequest({ url: prefix + `projects/${id}/`, method: 'patch', data })
}

/** Delete project */
export function DeleteProject(id: number) {
  return opsflowRequest({ url: prefix + `projects/${id}/`, method: 'delete' })
}

/** Get current user's projects (for project switcher) */
export function GetMyProjects() {
  return opsflowRequest({ url: prefix + 'projects/my_projects/', method: 'get' })
}

/** Get project members */
export function GetProjectMembers(projectId: number) {
  return opsflowRequest({ url: prefix + `projects/${projectId}/members/`, method: 'get' })
}

/** Add project member */
export function AddProjectMember(projectId: number, userId: number, role: string = 'editor') {
  return opsflowRequest({ url: prefix + `projects/${projectId}/members/`, method: 'post', data: { user_id: userId, role } })
}

/** Remove project member */
export function RemoveProjectMember(projectId: number, memberId: number) {
  return opsflowRequest({ url: prefix + `projects/${projectId}/members/${memberId}/`, method: 'delete' })
}

/** Get project environment variables */
export function GetProjectEnvVars(projectId: number) {
  return opsflowRequest({ url: prefix + `projects/${projectId}/env-vars/`, method: 'get' })
}

/** Update project environment variables (full replace) */
export function SetProjectEnvVars(projectId: number, items: any[]) {
  return opsflowRequest({ url: prefix + `projects/${projectId}/env-vars/`, method: 'post', data: { items } })
}

/** Partially update project environment variables */
export function PatchProjectEnvVars(projectId: number, items: any[]) {
  return opsflowRequest({ url: prefix + `projects/${projectId}/env-vars/`, method: 'patch', data: { items } })
}
