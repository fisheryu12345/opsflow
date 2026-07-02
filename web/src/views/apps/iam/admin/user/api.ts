import { request, downloadFile } from '/@/utils/service';

export const apiPrefix = '/api/system/user/';

export function GetDept(params?: Record<string, any>) {
    return request({
        url: '/api/system/dept/dept_lazy_tree/',
        method: 'get',
        params,
    });
}

export function GetList(params?: Record<string, any>) {
    return request({
        url: apiPrefix,
        method: 'get',
        params,
    });
}

export function GetObj(id: number | string) {
    return request({
        url: apiPrefix + id,
        method: 'get',
    });
}

export function AddObj(data: Record<string, any>) {
    return request({
        url: apiPrefix,
        method: 'post',
        data,
    });
}

export function UpdateObj(data: Record<string, any>) {
    return request({
        url: apiPrefix + data.id + '/',
        method: 'put',
        data,
    });
}

export function DelObj(id: number | string) {
    return request({
        url: apiPrefix + id + '/',
        method: 'delete',
        data: { id },
    });
}

export function exportData(params?: Record<string, any>) {
    return downloadFile({
        url: apiPrefix + 'export_data/',
        params,
        method: 'get',
    });
}

export function resetPwd(id: number | string, data: { new_password: string; new_password2?: string }) {
    return request({
        url: `/api/system/user/${id}/reset_password/`,
        method: 'put',
        data,
    });
}
