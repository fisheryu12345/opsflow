import { request } from '/@/utils/service';
import XEUtils from 'xe-utils';

type UserPageQuery = Record<string, any>;
type AddReq = Record<string, any>;
type DelReq = number | string;
type EditReq = Record<string, any> & {id: number | string};
type InfoReq = number | string;

export const apiPrefix = '/api/system/system_config/';
export function GetList(query: UserPageQuery) {
	return request({
		url: apiPrefix,
		method: 'get',
		params: query,
	});
}
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id,
		method: 'get',
	});
}

export function AddObj(obj: AddReq) {
	return request({
		url: apiPrefix,
		method: 'post',
		data: obj,
	});
}

export function UpdateObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

/*
获取所有的model及字段信息
 */
export function GetAssociationTable() {
	return request({
		url: apiPrefix + 'get_association_table/',
		method: 'get',
		params: {},
	});
}

export function saveContent(data: any) {
	return request({
		url: apiPrefix + 'save_content/',
		method: 'put',
		data: data,
	});
}
