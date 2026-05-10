import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/kline-data/'

export function GetKlineData(params: any) {
  return request({ url: apiPrefix, method: 'get', params })
}

export function GetTradeMarkers(params: any) {
  return request({ url: apiPrefix + 'trade-markers/', method: 'get', params })
}

export function GetAvailableContracts(params: any) {
  return request({ url: apiPrefix + 'available-contracts/', method: 'get', params })
}
