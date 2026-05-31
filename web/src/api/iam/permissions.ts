import { request } from '/@/utils/service'

const prefix = '/api/iam/'

export function GetAvailableRoles() {
  return request({ url: prefix + 'requests/available_roles/', method: 'get' })
}

export function GetAvailableMenus() {
  return request({ url: prefix + 'requests/available_menus/', method: 'get' })
}

export function GetDirectPermissions(params?: any) {
  return request({ url: prefix + 'direct-permissions/', method: 'get', params })
}

export function DeleteDirectPermission(id: number) {
  return request({ url: prefix + `direct-permissions/${id}/`, method: 'delete' })
}
