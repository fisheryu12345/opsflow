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
						show: true,
					},
				},
			},
			rowHandle: {
				fixed:'right',
				width: 100,
				buttons: {
					view: {
						type: 'text',
					},
					edit: {
						type: 'text',
					},
					remove: {
						type: 'text',
						show: false,
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
					title: '关键词',
					column: {
						show: false,
					},
					search: {
						show: true,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入配置名称',
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
				name: {
					title: '配置名称',
					search: {
						disabled: false,
					},
					type: 'input',
					column:{
						minWidth: 150,
					},
					form: {
						rules: [{ required: true, message: '请输入配置名称' }],
						component: {
							placeholder: '例如: 海龟策略_标准版',
						},
					},
				},
				// ==================== 资金管理参数 ====================
				max_units: {
					title: '最大持仓单位',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 120,
					},
					form: {
						helper: '单个品种最多持有N个Unit，固定上限防过度集中。默认: 3',
						component: {
							placeholder: '默认值: 3',
							min: 1,
							max: 10,
						},
					},
				},
				entry_units: {
					title: '初始建仓单位',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 120,
					},
					form: {
						helper: '首次开仓固定1 Unit，后续通过加仓增加。默认: 1',
						component: {
							placeholder: '默认值: 1',
							min: 1,
							max: 5,
						},
					},
				},
				risk_per_unit: {
					title: '每单位风险金额(元)',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 160,
					},
					form: {
						helper: '决定开仓手数：unit_lots = 风险金额 / (ATR × 2 × 合约乘数)。默认: 4000',
						component: {
							placeholder: '默认值: 4000',
							min: 0,
							precision: 2,
						},
					},
				},
				position_risk_multiplier: {
					title: 'ATR风险倍数',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						helper: '止损距离基准倍数 = N × ATR，同时用于Unit手数计算的分数线分母。默认: 2',
						component: {
							placeholder: '默认值: 2',
							min: 1,
							max: 5,
						},
					},
				},
				protect_cost_enabled_ratio: {
					title: '保本启用比例',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 150,
					},
					form: {
						helper: '盈利超过 N×ATR 时自动启用保本价保护。值越小越早启动保本。默认: 2.5',
						component: {
							placeholder: '默认值: 2.5 (ATR倍数)',
							min: 0.5,
							max: 10,
							precision: 2,
						},
					},
				},
				timeout_seconds: {
					title: '订单超时(秒)',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 130,
					},
					form: {
						helper: 'TargetPosTask等待成交的超时时间，超时后取消订单释放资源。默认: 60',
						component: {
							placeholder: '默认值: 60',
							min: 10,
							max: 300,
						},
					},
				},
				// ==================== 技术指标参数 ====================
				atr_period: {
					title: 'ATR周期',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 100,
					},
					form: {
						helper: '平均真实波幅的计算周期。周期越大ATR越平滑，对价格变化反应越慢。默认: 20',
						component: {
							placeholder: '默认值: 20',
							min: 5,
							max: 100,
						},
					},
				},
				entry_period: {
					title: '入场突破周期',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 130,
					},
					form: {
						helper: '唐奇安通道突破周期。收盘价突破前N日最高/最低点时触发开仓信号。默认: 20',
						component: {
							placeholder: '默认值: 20',
							min: 5,
							max: 100,
						},
					},
				},
				// exit_period: {
				// 	title: '离场突破周期',
				// 	type: 'number',
				// 	search: {
				// 		disabled: true,
				// 	},
				// 	column:{
				// 		minWidth: 130,
				// 	},
				// 	form: {
				// 		helper: '唐奇安通道离场周期。当前未使用，保留备用。默认: 10',
				// 		component: {
				// 			placeholder: '默认值: 10',
				// 			min: 5,
				// 			max: 100,
				// 		},
				// 	},
				// },
				ma_periods: {
					title: '均线周期',
					type: 'input',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 120,
					},
					form: {
						helper: '用于计算趋势因子，逗号分隔三组均线。例: 10,20,40 表示MA10/MA20/MA40',
						component: {
							placeholder: '逗号分隔，如: 10,20,40',
						},
					},
				},
				// ==================== 趋势因子参数 ====================
				trend_gap_limit: {
					title: '封顶上限',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						helper: '均线间距达此比例时trend_factor封顶。调小→趋势因子更快达最大值。默认: 0.03 (3%)',
						component: {
							placeholder: '默认值: 0.03',
							min: 0.001,
							max: 0.1,
							precision: 4,
						},
					},
				},
				trend_factor_max: {
					title: '趋势因子最大值',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 140,
					},
					form: {
						helper: 'trend_factor上限。值越大强趋势时止损放宽越多。止损倍数范围=[2.0, 2×(1+此值)]。默认: 0.5',
						component: {
							placeholder: '默认值: 0.5',
							min: 0,
							max: 1,
							precision: 3,
						},
					},
				},
				trend_label_strong_ratio: {
					title: '强趋势阈值',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						helper: 'trend_strength≥此值时标签显示strong。调小→更容易被判定为强趋势。默认: 0.80',
						component: {
							placeholder: '默认值: 0.80',
							min: 0,
							max: 1,
							precision: 3,
						},
					},
				},
				trend_label_weak_ratio: {
					title: '弱趋势阈值',
					type: 'number',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
					},
					form: {
						helper: 'trend_strength≥此值时标签显示weak。调小→更容易被判定为有趋势。默认: 0.30',
						component: {
							placeholder: '默认值: 0.30',
							min: 0,
							max: 1,
							precision: 3,
						},
					},
				},
				// ==================== 过滤参数 ====================
				gap_threshold: {
					title: '跳空放弃阈值(%)',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 150,
					},
					form: {
						helper: '跳空幅度=abs(最新价-昨收)/ATR，超过此值跳过开仓。调小→跳空保护更敏感。默认: 1.5',
						component: {
							placeholder: '默认值: 1.5',
							min: 0,
							max: 10,
							precision: 2,
						},
					},
				},
				product_codes: {
					title: '交易品种列表',
					type: 'input',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 300,
						show: true,
						formatter: (context: any) => {
							const val = context.value || '';
							const codes = val.split(',').filter(Boolean);
							return codes.join(', ');
						},
					},
					form: {
						component: {
							type: 'textarea',
							placeholder: '逗号分隔，如: rb,hc,MA,TA',
							autosize: { minRows: 3, maxRows: 6 },
						},
						helper: '仅列表中的品种会同步合约和生成交易信号。逗号分隔，不要含空格',
					},
				},
				// ==================== TqSDK 账户配置 ====================
				tqapi_account: {
					title: 'TqSDK账号',
					type: 'input',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 150,
					},
					form: {
						rules: [{ required: true, message: '请输入TqSDK账号' }],
						helper: '天勤量化交易平台的登录账号',
						component: {
							placeholder: '请输入TqSDK账号',
						},
					},
				},
				tqapi_password: {
					title: 'TqSDK密码',
					type: 'input',
					search: {
						disabled: true,
					},
					column: {
						minWidth: 120,
						formatter: () => '••••••••',
					},
					form: {
						rules: [{ required: true, message: '请输入TqSDK密码' }],
						helper: '天勤量化交易平台的登录密码',
						component: {
							placeholder: '请输入TqSDK密码',
							props: {
								type: 'password',
								showPassword: true,
							},
						},
					},
				},
			},
		},
	};
};
