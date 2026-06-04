import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/column/';

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

/**
 * Get all models for column matching / 获取所有model
 */
export function getModelList() {
  return request({
    url: '/api/system/column/get_models/',
    method: 'get',
  });
}

/**
 * Auto-match fields from model / 自动匹配字段
 * @param data - { menu, model, app }
 */
export function automatchColumnsData(data: Record<string, any>) {
  return request({
    url: '/api/system/column/auto_match_fields/',
    method: 'post',
    data,
  });
}
