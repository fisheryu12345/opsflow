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
						component: {
							placeholder: '默认值: 1',
							min: 1,
							max: 5,
						},
					},
				},
				risk_per_unit: {
					title: '每单位风险金额',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 140,
					},
					form: {
						component: {
							placeholder: '默认值: 4000',
							min: 0,
							precision: 2,
						},
					},
				},
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
						component: {
							placeholder: '默认值: 20',
							min: 5,
							max: 100,
						},
					},
				},
				exit_period: {
					title: '离场突破周期',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 130,
					},
					form: {
						component: {
							placeholder: '默认值: 10',
							min: 5,
							max: 100,
						},
					},
				},
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
						component: {
							placeholder: '逗号分隔，如: 10,20,40',
						},
					},
				},
				gap_threshold: {
					title: '跳空放弃阈值(%)',
					type: 'number',
					search: {
						disabled: true,
					},
					column:{
						minWidth: 140,
					},
					form: {
						component: {
							placeholder: '默认值: 1.5',
							min: 0,
							max: 10,
							precision: 2,
						},
					},
				},
				// pause_open_task_job: {
				// 	title: '开仓时段任务',
				// 	type: 'switch',
				// 	search: {
				// 		disabled: true,
				// 	},
				// 	column:{
				// 		minWidth: 140,
				// 		formatter: (context) => {
				// 			return context.value ? '已暂停' : '运行中';
				// 		},
				// 	},
				// 	form: {
				// 		value: false,
				// 		component: {
				// 			props: {
				// 				activeText: '已暂停',
				// 				inactiveText: '运行中',
				// 			},
				// 		},
				// 		helper: '节假日开启后将暂停开仓任务，用于临时关闭策略',
				// 	},
				// },
			},
		},
	};
};
