import * as api from './api';
import { ref, h } from 'vue';
import {
	dict,
	UserPageQuery,
	AddReq,
	DelReq,
	EditReq,
	CrudExpose,
	CrudOptions,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet
} from '@fast-crud/fast-crud';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const pageRequest = async (query: UserPageQuery) => {
		console.log('📤 Closed Position API Query params:', query);
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
			pagination: {
				show: true,
				defaultPageSize: 20,
			},
			actionbar: {
				buttons: {
					add: {
						show: false, // 平仓记录由系统自动生成，不允许手动添加
					},
				},
			},
			rowHandle: {
				fixed: 'center',
				width: 0,
				show: false,
				buttons: {
					view: {
						show: false, // 平仓记录为只读，列表已展示完整信息，无需查看详情
					},
					edit: {
						show: false, // 平仓记录为只读，不允许编辑
					},
					remove: {
						type: 'text',
						show: false, // 平仓记录不建议手动删除
					},
				},
			},
			columns: {
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						align: 'center',
						width: '60px',
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
							placeholder: '请输入合约代码、品种代码或账户名称',
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
				account_name: {
					title: '所属账户',
					type: 'input',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入账户名称',
						},
					},
					column: {
						align: 'center',
						Width: 80,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
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
							placeholder: '例如: rb2405, MA2409',
						},
					},
					column: {
						align: 'center',
						Width: 60,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
					},
				},
				product_code: {
					title: '品种代码',
					type: 'input',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '例如: rb, MA, IF',
						},
					},
					column: {
						align: 'center',
						minWidth: 50,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
					},
				},
				direction: {
					title: '平仓方向',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: 1, label: '多头平仓', color: 'success' },
							{ value: -1, label: '空头平仓', color: 'danger' },
						],
					}),
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
						},
					},
					column: {
						width: 100,
						align: 'center',
					},
					form: {
						show: false,
					},
				},
				volume: {
					title: '平仓手数',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 100,
						align: 'center',
					},
					form: {
						show: false,
					},
				},
				exit_price: {
					title: '平仓价',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 100,
						align: 'center',
						formatter: (context) => {
							return context.value ? Number(context.value).toFixed(2) : '-';
						},
					},
					form: {
						show: false,
					},
				},
				cost_price: {
					title: '成本价',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 100,
						align: 'center',
						formatter: (context) => {
							return context.value ? Number(context.value).toFixed(2) : '-';
						},
					},
					form: {
						show: false,
					},
				},
				pnl: {
					title: '平仓盈亏',
					type: 'number',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '盈亏金额',
						},
					},
					column: {
						width: 120,
						align: 'center',
						cellRender: (scope) => {
							const value = scope.row?.pnl;
							if (value === null || value === undefined) return '-';
							const formatted = Number(Math.abs(value)).toFixed(2);
							const color = value >= 0 ? '#67C23A' : '#F56C6C';
							const sign = value >= 0 ? '+' : '-';
							return h('span', { style: { color } }, `${sign}${formatted}`);
						},
					},
					form: {
						show: false,
					},
				},
				trade_date: {
					title: '交易日期',
					type: 'date',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
								type: 'daterange',
							},
							placeholder: '选择日期范围',
						},
					},
					column: {
						width: 120,
						align: 'center',
						formatter: (context) => {
							return context.value || '-';
						},
					},
					form: {
						show: false,
					},
				},
				executed_at: {
					title: '执行时间',
					type: 'datetime',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
								type: 'datetimerange',
							},
							placeholder: '选择时间范围',
						},
					},
					column: {
						width: 160,
						align: 'center',
						formatter: (context) => {
							return context.value || '-';
						},
					},
					form: {
						show: false,
					},
				},
				holding_days: {
					title: '持仓天数',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 120,
						align: 'center',
						formatter: (context) => {
							return context.value ? `${Number(context.value).toFixed(1)}天` : '-';
						},
					},
					form: {
						show: false,
					},
				},
			},
		},
	};
};