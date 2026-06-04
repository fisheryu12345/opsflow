import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/dictionary/';

export interface DictQuery {
  page?: number;
  limit?: number;
  search?: string;
  parent?: number | null;
  label?: string;
  value?: string;
}

export interface DictItem {
  id: number;
  label: string;
  value: string;
  status: boolean;
  sort: number;
  parent: number | null;
  type?: number;
  color?: string;
  create_datetime?: string;
  update_datetime?: string;
}

export function GetList(query: DictQuery) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

export function GetObj(id: number) {
  return request({
    url: apiPrefix + id,
    method: 'get',
  });
}

export function AddObj(obj: Partial<DictItem>) {
  return request({
    url: apiPrefix,
    method: 'post',
    data: obj,
  });
}

export function UpdateObj(obj: Partial<DictItem>) {
  return request({
    url: apiPrefix + obj.id + '/',
    method: 'put',
    data: obj,
  });
}

export function DelObj(id: number) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
  });
}
