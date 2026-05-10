import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/signal-stats/'

export function GetSignalStats(params: {
  date_from?: string
  date_to?: string
  account?: number
}) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
