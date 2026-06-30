import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/operation_log/';

export function GetList(query: any = {}) {
    return request({
        url: apiPrefix,
        method: 'get',
        params: query,
    });
}
