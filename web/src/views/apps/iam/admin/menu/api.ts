import { request } from '/@/utils/service';

export const apiPrefix = '/api/iam/menu/';

export function GetList(query: Record<string, any>) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

export function GetObj(id: number | string) {
  return request({
    url: apiPrefix + id + '/',
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

export function DelObj(id: string | number) {
  return request({
    url: apiPrefix + id + '/',
    method: 'delete',
  });
}

export function GetAllMenu(query: Record<string, any>) {
  return request({
    url: apiPrefix + 'get_all_menu/',
    method: 'get',
    params: query,
  });
}

export function lazyLoadMenu(query: Record<string, any>) {
  return request({
    url: apiPrefix,
    method: 'get',
    params: query,
  });
}

export function dragMenu(obj: Record<string, any>) {
  return request({
    url: apiPrefix + 'drag_menu/',
    method: 'post',
    data: obj,
  });
}

export function menuMoveUp(obj: Record<string, any>) {
  return request({
    url: apiPrefix + 'move_up/',
    method: 'post',
    data: obj,
  });
}

export function menuMoveDown(obj: Record<string, any>) {
  return request({
    url: apiPrefix + 'move_down/',
    method: 'post',
    data: obj,
  });
}
