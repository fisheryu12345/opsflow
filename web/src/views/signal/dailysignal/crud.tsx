import * as api from './api';
import { UserPageQuery, AddReq, DelReq, EditReq, CrudExpose, CrudOptions, CreateCrudOptionsProps, CreateCrudOptionsRet, dict } from '@fast-crud/fast-crud';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};
	const editRequest = async ({ form, row }: EditReq) => {
		form.id = row.id;
		return await api.UpdateObj(form);
	};
	const delRequest = async ({ row }: DelReq) => {
		return await api.DelObj(row.id);
	};
	const addRequest = async ({ form }: AddReq) => {
		return await api.AddObj(form);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				addRequest,
				editRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 策略信号为系统自动生成，不允许手动添加
					},
				},
			},
			rowHandle: {
				fixed: 'right',
				width: 80,
				buttons: {
					view: {
						type: 'text',
					},
					edit: {
						show: false, // 策略信号为只读，不允许编辑
					},
					remove: {
						type: 'text',
						show: true, // 允许清理旧信号记录
					},
				},
			},
			columns: {
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						align: 'center',
						width: '70px',
						columnSetDisabled: true,
						formatter: (context) => {
							let index = context.index ?? 1;
							let pagination = crudExpose!.crudBinding.value.pagination;
							return ((pagination!.currentPage ?? 1) - 1) * pagination!.pageSize + index + 1;
						},
					},
				},
				search: {
					title: '关键词搜索',
					column: {
						show: false,
					},
					search: {
						show: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入合约代码或备注信息',
						},
					},
					form: {
						show: false,
						component: {
							props: {
								clearable: true,
							},
						},
					},
				},
				trade_date: {
					title: '交易日期',
					type: 'date',
					search: {
						disabled: false,
						component: {
							type: 'daterange',
						},
					},
					column: {
						minWidth: 120,
						sorter: {
							enabled: true,
						},
					},
					form: {
						show: false,
					},
				},
				symbol: {
					title: '合约代码',
					type: 'input',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '例如: SHFE.rb2410',
						},
					},
					column: {
						minWidth: 150,
					},
					form: {
						show: false,
					},
				},
				trend_factor: {
					title: '趋势因子',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 100,
					},
					form: {
						show: false,
						component: {
							precision: 4,
						},
					},
				},
				trend_label: {
					title: '趋势标签',
					type: 'input',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 120,
						formatter: (context) => {
							const map: Record<string, string> = {
								'strong_bull': '强多',
								'weak_bull': '弱多',
								'neutral': '中性',
								'choppy': '震荡',
								'weak_bear': '弱空',
								'strong_bear': '强空',
							};
							return map[context.value as string] || context.value;
						},
					},
					form: {
						show: false,
					},
				},
				donchian_upper: {
					title: '唐奇安上轨',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						show: false,
						component: {
							precision: 2,
						},
					},
				},
				donchian_lower: {
					title: '唐奇安下轨',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						show: false,
						component: {
							precision: 2,
						},
					},
				},
				is_breakout: {
					title: '是否突破',
					type: 'switch',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 100,
						formatter: (context) => {
							return context.value ? '✅ 是' : '❌ 否';
						},
					},
					form: {
						show: false,
					},
				},
				signal_direction: {
					title: '信号方向',
					type: 'input',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 100,
						formatter: (context) => {
							const map: Record<number, string> = { 1: '📈 多', [-1]: '📉 空', 0: '➖ 无' };
							return map[context.value as number] || context.value;
						},
					},
					form: {
						show: false,
					},
				},
				trade_type: {
					title: '交易类型',
					type: 'input',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 100,
						formatter: (context) => {
							const map: Record<string, string> = {
								'ENTRY': '开仓',
								'ADD_ON': '加仓',
								'STOP_LOSS': '止损',
								'ROLLOVER': '移仓换月',
							};
							return map[context.value as string] || context.value;
						},
					},
					form: {
						show: false,
					},
				},
				executed_status: {
					title: '执行状态',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: 'PENDING', label: '待执行' },
							{ value: 'SUCCESS', label: '成功' },
							{ value: 'FAILED', label: '失败' },
							{ value: 'CANCELLED', label: '已取消' }
						]
					}),
					search: {
						show: true,
						disabled: false,
						component: {
							props: {
								clearable: true,
								placeholder: '请选择执行状态'
							}
						}
					},
					column: {
						minWidth: 100,
						align: 'center',
						formatter: (context) => {
							const map: Record<string, string> = {
								'PENDING': '待执行',
								'SUCCESS': '成功',
								'FAILED': '失败',
								'CANCELLED': '已取消',
							};
							return map[context.value as string] || context.value;
						},
					},
					form: {
						show: false,
					},
				},
				remark: {
					title: '备注说明',
					type: 'textarea',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入备注关键词',
						},
					},
					column: {
						minWidth: 300,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
						component: {
							props: {
								rows: 4,
								placeholder: '记录过滤原因、决策依据等详细信息',
							},
						},
					},
				},
			},
		},
	};
};
