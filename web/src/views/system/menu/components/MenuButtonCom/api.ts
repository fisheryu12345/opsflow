import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/menu_button/';

export function GetList(query: Record<string, any>) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

export function GetObj(id: number | string) {
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

export function DelObj(id: number | string | undefined) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
    data: { id },
  });
}
