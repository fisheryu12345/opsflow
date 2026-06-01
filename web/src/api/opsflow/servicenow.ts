import { opsflowRequest } from './request'

const prefix = '/api/opsflow/'

export function GetServicenowInstances(params?: any) {
  return opsflowRequest({ url: prefix + 'cmdb/servicenow-instances/', method: 'get', params })
}

export function GetServicenowChangeRequests(params?: any) {
  return opsflowRequest({ url: prefix + 'cmdb/servicenow-change-requests/', method: 'get', params })
}
