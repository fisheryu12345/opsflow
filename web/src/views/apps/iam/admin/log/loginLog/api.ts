import { request } from '/@/utils/service';

export const apiPrefix = '/api/system/login_log/';

export function GetList(params: Record<string, any>) {
    return request({
        url: apiPrefix,
        method: 'get',
        params,
    });
}

export function GetObj(id: number) {
    return request({
        url: apiPrefix + id,
        method: 'get',
    });
}

export function GetStats() {
    return request({
        url: apiPrefix + 'stats/',
        method: 'get',
    });
}
