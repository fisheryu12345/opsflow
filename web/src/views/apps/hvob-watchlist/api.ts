import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/hvob-watchlist/'

export function GetWatchlist(params: any) {
  return request({
    url: apiPrefix,
    method: 'get',
    params,
  })
}
