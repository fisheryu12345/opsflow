import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/dictionary/';

/* 字典项查询参数 */
export interface DictQuery {
  page?: number;
  limit?: number;
  label?: string;
  parent?: number;
}

/* 字典项数据模型 */
export interface DictItem {
  id?: number;
  label: string;
  value: string;
  type: number;
  status: boolean;
  sort: number;
  color?: string;
  parent?: number;
}

/* 获取字典项列表（分页） */
export function GetList(query: DictQuery) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

/* 获取单个字典项 */
export function GetObj(id: number) {
  return request({
    url: apiPrefix + id + '/',
    method: 'get',
  });
}

/* 新增字典项 */
export function AddObj(obj: Partial<DictItem>) {
  return request({
    url: apiPrefix,
    method: 'post',
    data: obj,
  });
}

/* 更新字典项 */
export function UpdateObj(obj: Partial<DictItem>) {
  return request({
    url: apiPrefix + obj.id + '/',
    method: 'put',
    data: obj,
  });
}

/* 删除字典项 */
export function DelObj(id: number) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
    data: {},
  });
}
