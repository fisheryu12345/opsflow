import * as api from './api';
import { ref } from 'vue';
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
	// 筛选状态：是否只显示有持仓的记录
	const showHoldingsOnly = ref(false);

	const pageRequest = async (query: UserPageQuery) => {
		// 如果启用了持仓筛选，添加筛选条件
		if (showHoldingsOnly.value) {
			query.contract_total_position__gt = 0;
			console.log('🔍 Filtering positions with holdings > 0');
		}
		console.log('📤 API Query params:', query);
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

	// 自定义按钮：查看有持仓的列表
	const showPositionsWithHoldings = () => {
		console.log('✅ Filter activated: showing only positions with holdings');
		showHoldingsOnly.value = true;
		crudExpose!.doRefresh();
	};

	// 自定义按钮：查看全部列表（清除筛选）
	const showAllPositions = () => {
		console.log('🔄 Filter cleared: showing all positions');
		showHoldingsOnly.value = false;
		crudExpose!.doRefresh();
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
						show: false, // 持仓状态由系统自动管理，不允许手动添加
					},
					showHoldings: {
						text: '查看持仓',
						type: 'primary',
						icon: 'Filter',
						click: showPositionsWithHoldings,
					},
					showAll: {
						text: '查看全部',
						type: 'default',
						icon: 'Refresh',
						click: showAllPositions,
					},
				},
			},
			rowHandle: {
				fixed:'center',
				width: 0,
				show: false,
				buttons: {
					view: {
						show: false, // 持仓状态为只读，列表已展示完整信息，无需查看详情
					},
					edit: {
						show: false, // 持仓状态为只读，不允许编辑
					},
					remove: {
						type: 'text',
						show: false, // 持仓状态不建议手动删除
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
							placeholder: '请输入合约代码或品种代码',
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
				account: {
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
						minWidth: 80,
						showOverflowTooltip: true,
						formatter: (context) => {
							// 处理嵌套对象或ID
							const account = context.row?.account;
							if (typeof account === 'object' && account !== null) {
								return account.name || account.id || '-';
							}
							return account || '-';
						},
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
							placeholder: '例如: CFFEX.IC2606',
						},
					},
					column: {
						align: 'center',
						minWidth: 120,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
						rules: [{ required: true, message: '合约代码不能为空' }],
						component: {
							placeholder: '合约代码，如：CFFEX.IC2606',
						},
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
							placeholder: '例如: IC, rb, MA',
						},
					},
					column: {
						align: 'center',
						minWidth: 80,
						showOverflowTooltip: true,
					},
					form: {
						show: false,
						component: {
							placeholder: '品种代码（不带年份），如：IC, rb, MA',
						},
					},
				},
				units: {
					title: '单位数',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 80,
						align: 'center',
					},
					form: {
						show: false,
						component: {
							props: {
								min: 0,
								max: 3,
								disabled: true,
							},
						},
					},
				},
				direction: {
					title: '持仓方向',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: 1, label: '多头', color: 'success' },
							{ value: -1, label: '空头', color: 'danger' },
							{ value: 0, label: '空仓', color: 'info' },
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
						component: {
							props: {
								disabled: true,
							},
						},
					},
				},
				contract_total_position: {
					title: '总持仓手数',
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
						component: {
							props: {
								disabled: true,
							},
						},
					},
				},
				last_add_price: {
					title: '上次加仓价',
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
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				highest_close: {
					title: '持仓期最高价',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 120,
						align: 'center',
					},
					form: {
						show: false,
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				lowest_close: {
					title: '持仓期最低价',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 120,
						align: 'center',
					},
					form: {
						show: false,
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				stop_loss_price: {
					title: '止损价',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 80,
						align: 'center',
					},
					form: {
						show: false,
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				trend_info: {
					title: '趋势信息(ATR-Factor)',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						width: 160,
						align: 'center',
					},
					form: {
						show: false,
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				latest_close_price: {
					title: '最新收盘价',
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
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				// indicators: {
				// 	title: '技术指标',
				// 	type: 'textarea',
				// 	search: {
				// 		disabled: true,
				// 	},
				// 	column: {
				// 		minWidth: 200,
				// 		showOverflowTooltip: true,
				// 		formatter: (context) => {
				// 			const indicators = context.row?.indicators;
				// 			if (!indicators) return '-';
				// 			// 如果是对象，转换为JSON字符串显示
				// 			if (typeof indicators === 'object') {
				// 				return JSON.stringify(indicators, null, 2);
				// 			}
				// 			return indicators;
				// 		},
				// 	},
				// 	form: {
				// 		show: false,
				// 		component: {
				// 			props: {
				// 				rows: 4,
				// 				disabled: true,
				// 			},
				// 		},
				// 	},
				// },
				last_update_time: {
					title: '最后更新时间',
					type: 'datetime',
					search: {
						disabled: false,
						component: {
							type: 'daterange',
						},
					},
					column: {
						minWidth: 180,
						align: 'center',
						sorter: {
							enabled: true,
						},
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
				is_rollover_needed: {
					title: '需移仓换月',
					type: 'dict-select',
					dict: dict({
						data: [
							{ value: true, label: '是', color: 'warning' },
							{ value: false, label: '否', color: 'success' },
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
						width: 110,
						align: 'center',
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
				h20_price: {
					title: '20日最高价',
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
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
				l20_price: {
					title: '20日最低价',
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
						component: {
							props: {
								precision: 2,
								disabled: true,
							},
						},
					},
				},
			},
		},
	};
};
