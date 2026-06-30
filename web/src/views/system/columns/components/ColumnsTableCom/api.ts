import { request } from '/@/utils/service';
import { CurrentInfoType, AddColumnsDataType } from '../../types'

export function getColumnsData(query: any) {
	return request({
		url: '/api/iam/column/',
		method: 'get',
		params: query,
	});
}

export function automatchColumnsData(data: CurrentInfoType) {
	return request({
		url: '/api/iam/column/auto_match_fields/',
		method: 'post',
		data,
	});
}

export function addColumnsData(data: AddColumnsDataType) {
	return request({
		url: '/api/iam/column/',
		method: 'post',
		data
	});
}

export function deleteColumnsData(id: number) {
	return request({
		url: `/api/iam/column/${id}/`,
		method: 'delete',
	});
}

export function updateColumnsData(data: AddColumnsDataType) {
	return request({
		url: `/api/iam/column/${data.id}/`,
		method: 'put',
		data
	});
}
