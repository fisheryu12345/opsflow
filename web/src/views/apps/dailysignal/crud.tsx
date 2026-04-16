import * as api from './api';
import { UserPageQuery, AddReq, DelReq, EditReq, CrudExpose, CrudOptions, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';

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
				fixed:'right',
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
						show: true,
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
						show: false, // 自动记录，不允许手动设置
						component: {
							props: {
								disabled: true,
							},
						},
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
						show: false, // 自动记录
						rules: [{ required: true, message: '合约代码不能为空' }],
						component: {
							placeholder: '完整合约代码，如：SHFE.rb2410',
						},
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
					type: 'dict-select',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 120,
					},
					form: {
						show: false,
					},
					valueEnum: {
						strong_bull: { text: '强多', status: 'success' },
						weak_bull: { text: '弱多', status: 'processing' },
						neutral: { text: '中性', status: 'default' },
						choppy: { text: '震荡', status: 'warning' },
						weak_bear: { text: '弱空', status: 'warning' },
						strong_bear: { text: '强空', status: 'error' },
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
						value: false,
						component: {
							props: {
								activeText: '是',
								inactiveText: '否',
							},
						},
					},
				},
				signal_direction: {
					title: '信号方向',
					type: 'dict-select',
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
					valueEnum: {
						1: { text: '多头信号' },
						[-1]: { text: '空头信号' },
						0: { text: '无信号' },
					},
				},
				trade_type: {
					title: '交易类型',
					type: 'dict-select',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 100,
					},
					form: {
						show: false,
					},
					valueEnum: {
						ENTRY: { text: '开仓', status: 'success' },
						ADD_ON: { text: '加仓', status: 'processing' },
						STOP_LOSS: { text: '止损', status: 'error' },
						ROLLOVER: { text: '移仓换月', status: 'warning' },
					},
				},
				executed_status: {
					title: '执行状态',
					type: 'dict-select',
					search: {
						disabled: false,
					},
					column: {
						minWidth: 100,
					},
					form: {
						show: false,
					},
					valueEnum: {
						PENDING: { text: '待执行', status: 'default' },
						SUCCESS: { text: '成功', status: 'success' },
						FAILED: { text: '失败', status: 'error' },
						CANCELLED: { text: '已取消', status: 'warning' },
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