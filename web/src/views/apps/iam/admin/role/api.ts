import { request } from '/@/utils/service';

export const apiPrefix = '/api/iam/role/';

/** 角色列表查询参数 */
export interface RoleListQuery {
  page?: number;
  limit?: number;
  name?: string;
  status?: boolean | string;
  ordering?: string;
  [key: string]: any;
}

/** 获取角色列表（分页） */
export function GetList(query: RoleListQuery) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

/** 获取单个角色 */
export function GetObj(id: number | string) {
  return request({
    url: apiPrefix + id + '/',
    method: 'get',
  });
}

/** 新增角色 */
export function AddObj(obj: Record<string, any>) {
  return request({
    url: apiPrefix,
    method: 'post',
    data: obj,
  });
}

/** 更新角色 */
export function UpdateObj(obj: Record<string, any>) {
  return request({
    url: apiPrefix + obj.id + '/',
    method: 'put',
    data: obj,
  });
}

/** 删除角色 */
export function DelObj(id: number | string) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
    data: { id },
  });
}
