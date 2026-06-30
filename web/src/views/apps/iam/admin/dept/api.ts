import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/dept/';

export interface QueryParams {
  page?: number;
  limit?: number;
  parent?: string | number;
  [key: string]: any;
}

export function GetList(query: QueryParams = {}) {
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
  return request({ url: apiPrefix + id + '/', method: 'delete' });
}

export function lazyLoadDept(query: QueryParams) {
  return request({ url: apiPrefix, method: 'get', params: query });
}

export function deptMoveUp(obj: Record<string, any>) {
  return request({ url: apiPrefix + 'move_up/', method: 'post', data: obj });
}

export function deptMoveDown(obj: Record<string, any>) {
  return request({ url: apiPrefix + 'move_down/', method: 'post', data: obj });
}

export function getDeptUserList(query: QueryParams) {
  return request({ url: '/api/system/user/', method: 'get', params: query });
}

export function getAllDeptList() {
  return request({ url: apiPrefix + 'all_dept/', method: 'get' });
}
