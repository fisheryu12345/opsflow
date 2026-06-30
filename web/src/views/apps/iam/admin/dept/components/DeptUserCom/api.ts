import { request, downloadFile } from '/@/utils/service';

export const apiPrefix = '/api/system/user/';

export interface UserQuery {
  page?: number;
  limit?: number;
  show_all?: string;
  dept?: string;
  search?: string;
  [key: string]: any;
}

export function GetDept(query: Record<string, any> = {}) {
  return request({ url: '/api/system/dept/dept_lazy_tree/', method: 'get', params: query });
}

export function GetList(query: UserQuery) {
  return request({ url: apiPrefix, method: 'get', params: query });
}

export function GetObj(id: string | number) {
  return request({ url: apiPrefix + id, method: 'get' });
}

export function AddObj(obj: Record<string, any>) {
  return request({ url: apiPrefix, method: 'post', data: obj });
}

export function UpdateObj(obj: Record<string, any>) {
  return request({ url: apiPrefix + obj.id + '/', method: 'put', data: obj });
}

export function DelObj(id: string | number) {
  return request({ url: apiPrefix + id + '/', method: 'delete', data: { id } });
}

export function exportData(params: any) {
  return downloadFile({ url: apiPrefix + 'export_data/', params, method: 'get' });
}

export function getDeptInfoById(id: string, type: string) {
  return request({ url: `/api/system/dept/dept_info/?dept_id=${id}&show_all=${type}`, method: 'get' });
}

export function resetPwd(id: number, data: Record<string, string>) {
  return request({ url: `/api/system/user/${id}/reset_password/`, method: 'put', data });
}
