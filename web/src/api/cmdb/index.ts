/// <reference types="vite/client" />
/**
 * CMDB API — 重构版（匹配新版纯 Cypher 后端 API）
 */
import { request } from '/@/utils/service'

const prefix = '/api/cmdb'

export function createCrudApi(resource: string) {
  return {
    list: (params?: any) => request({ url: `${prefix}/${resource}/`, method: 'get', params }),
    detail: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'get' }),
    create: (data: any) => request({ url: `${prefix}/${resource}/`, method: 'post', data }),
    update: (id: string, data: any) => request({ url: `${prefix}/${resource}/${id}/`, method: 'patch', data }),
    delete: (id: string) => request({ url: `${prefix}/${resource}/${id}/`, method: 'delete' }),
  }
}

// ─── Schema API（MySQL） ───
export const classificationsApi = createCrudApi('classifications')
export const modelDefinitionsApi = createCrudApi('model-definitions')
export const modelFieldsApi = createCrudApi('model-fields')
export const attributeGroupsApi = createCrudApi('attribute-groups')
export const associationTypesApi = createCrudApi('association-types')
export const modelAssociationsApi = createCrudApi('model-associations')
export const instanceAssociationsApi = createCrudApi('instance-associations')
export const objectUniquesApi = createCrudApi('object-uniques')
export const mainlineToposApi = createCrudApi('mainline-topos')

// ─── 动态实例 API（Neo4j） ───
export function getInstances(modelCode: string, params?: any) {
  return request({ url: `${prefix}/instances/${modelCode}/`, method: 'get', params })
}

export function createInstance(modelCode: string, data: any) {
  return request({ url: `${prefix}/instances/${modelCode}/`, method: 'post', data })
}

export function updateInstance(modelCode: string, id: string, data: any) {
  return request({ url: `${prefix}/instances/${modelCode}/${id}/`, method: 'patch', data })
}

export function deleteInstance(modelCode: string, id: string) {
  return request({ url: `${prefix}/instances/${modelCode}/${id}/`, method: 'delete' })
}

export function getInstanceDetail(modelCode: string, id: string) {
  return request({ url: `${prefix}/instances/${modelCode}/${id}/`, method: 'get' })
}

// ─── 实例关联 API ───
export function createRelation(data: { src_id: string; dst_id: string; asst_type: string }) {
  return request({ url: `${prefix}/instance-associations/`, method: 'post', data })
}

export function deleteRelation(relId: string) {
  return request({ url: `${prefix}/instance-associations/${relId}/`, method: 'delete' })
}

export function listRelations(params?: any) {
  return request({ url: `${prefix}/instance-associations/`, method: 'get', params })
}

export function getNeighbors(instanceId: string, params?: { direction?: string; max_depth?: number }) {
  return request({
    url: `${prefix}/instance-associations/neighbors/`,
    method: 'get',
    params: { instance_id: instanceId, ...params },
  })
}

// ─── 拓扑 API ───
export function getTopology() {
  return request({ url: `${prefix}/topology/`, method: 'get' })
}

export function getTopologyTree(rootId: string, params?: { depth?: number }) {
  return request({ url: `${prefix}/topology/tree/`, method: 'get', params: { root_id: rootId, ...params } })
}

export function getImpact(nodeId: string, params?: { direction?: string; depth?: number }) {
  return request({ url: `${prefix}/topology/impact/`, method: 'get', params: { node_id: nodeId, ...params } })
}

export function globalSearch(q: string, params?: { model_codes?: string[]; limit?: number }) {
  return request({ url: `${prefix}/topology/search/`, method: 'get', params: { q, ...params } })
}

// ─── 变更历史 API ───
export function getChangeHistory(modelCode: string, instanceId: string, params?: {
  action?: string; start_date?: string; end_date?: string;
  operator?: string; page?: number; page_size?: number;
}) {
  return request({
    url: `${prefix}/instances/${modelCode}/${instanceId}/change_history/`,
    method: 'get', params,
  })
}

// ─── 导入导出 API ───
export function exportInstances(modelCode: string, filters?: any) {
  return request({
    url: `${prefix}/instances/${modelCode}/export/`,
    method: 'post', data: { filters },
    responseType: 'blob',
  })
}

export function importInstances(modelCode: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: `${prefix}/instances/${modelCode}/import/`,
    method: 'post', data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ─── 事件订阅 API ───
export const eventSubscriptionsApi = createCrudApi('event-subscriptions')
