import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/api_white_list/';

export interface WhiteListRecord {
  id?: number;
  method: number;
  url: string;
  enable_datasource: boolean;
}

export interface WhiteListQuery {
  page: number;
  limit: number;
  method?: number | string;
  [key: string]: any;
}

export function GetList(query: WhiteListQuery) {
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

export function AddObj(obj: Record<string, any>) {
  return request({
    url: apiPrefix,
    method: 'post',
    data: obj,
  });
}

export function UpdateObj(obj: Record<string, any>) {
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
    data: { id },
  });
}
