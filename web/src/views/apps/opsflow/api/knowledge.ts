import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

export function GetKnowledgeList(params?: any) {
  return opsflowRequest({ url: prefix + 'knowledge/', method: 'get', params })
}

export function CreateKnowledge(data: any) {
  return opsflowRequest({ url: prefix + 'knowledge/', method: 'post', data })
}

export function UpdateKnowledge(id: number, data: any) {
  return opsflowRequest({ url: prefix + `knowledge/${id}/`, method: 'patch', data })
}

export function DeleteKnowledge(id: number) {
  return opsflowRequest({ url: prefix + `knowledge/${id}/`, method: 'delete' })
}

export function SearchKnowledge(query: string) {
  return opsflowRequest({ url: prefix + 'knowledge/search/', method: 'post', data: { query } })
}
