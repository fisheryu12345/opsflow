import { request } from '/@/utils/service';
import { UserPageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/stock/contracts/';

/**
 * 获取合约列表（支持分页、筛选、搜索、排序）
 */
export function GetList(query: UserPageQuery) {
	return request({
		url: apiPrefix,
		method: 'get',
		params: query,
	});
}

/**
 * 获取单个合约详情
 */
export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'get',
	});
}

/**
 * 创建新合约
 */
export function AddObj(obj: AddReq) {
	return request({
		url: apiPrefix,
		method: 'post',
		data: obj,
	});
}

/**
 * 更新合约（完整更新）
 */
export function UpdateObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

/**
 * 部分更新合约
 */
export function PatchObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'patch',
		data: obj,
	});
}

/**
 * 删除合约
 */
export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
	});
}

/**
 * 批量激活合约
 */
export function ActivateContracts(ids: number[]) {
	return request({
		url: apiPrefix + 'activate/',
		method: 'post',
		data: { ids },
	});
}

/**
 * 批量停用合约
 */
export function DeactivateContracts(ids: number[]) {
	return request({
		url: apiPrefix + 'deactivate/',
		method: 'post',
		data: { ids },
	});
}

/**
 * 切换单个合约的激活状态
 */
export function ToggleActive(id: number) {
	return request({
		url: apiPrefix + id + '/toggle_active/',
		method: 'post',
	});
}

/**
 * 获取合约统计信息
 */
export function GetStatistics() {
	return request({
		url: apiPrefix + 'statistics/',
		method: 'get',
	});
}

/**
 * 获取简化版合约列表（用于下拉选择）
 */
export function GetSimpleList(params?: any) {
	return request({
		url: apiPrefix + 'simple/',
		method: 'get',
		params,
	});
}

/**
 * 获取所有交易所列表（去重）
 * Returns: [{value: "SHFE", label: "上期所", count: 17}, ...]
 */
export function GetExchanges() {
	return request({
		url: apiPrefix + 'exchanges/',
		method: 'get',
	});
}

/**
 * 获取所有板块列表（去重）
 * Query params: exchange (可选，按交易所过滤)
 * Returns: [{value: "黑色金属", count: 5}, ...]
 */
