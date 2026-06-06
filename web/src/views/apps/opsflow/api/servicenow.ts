/**
 * ServiceNow 模拟数据 API
 *
 * 所有模拟数据端点统一在 mock_service 中维护。
 * 路径前缀为 /api/mock/（参考 backend/mock_service/urls.py）。
 */
import { service } from '/@/utils/service'

const prefix = '/api/mock_service/'

export function GetServicenowInstances(params?: any) {
  return service.get(prefix + 'servicenow-instances/', { params })
}

export function GetServicenowChangeRequests(params?: any) {
  return service.get(prefix + 'servicenow-change-requests/', { params })
}
