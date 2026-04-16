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
						show: false, // 错误日志为系统自动生成，不允许手动添加
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
						show: false, // 错误日志为只读，不允许编辑
					},
					remove: {
						type: 'text',
						show: true, // 允许清理旧错误日志
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
							placeholder: '请输入函数名称或错误信息',
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
				timestamp: {
					title: '错误时间',
					type: 'datetime',
					search: {
						disabled: false,
						component: {
							type: 'daterange',
						},
					},
					column: {
						minWidth: 180,
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
				function_name: {
					title: '函数名称',
					type: 'input',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '例如: execute_addon_order',
						},
					},
					column: {
						minWidth: 280,
						showOverflowTooltip: true,
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						rules: [{ required: true, message: '函数名称不能为空' }],
						component: {
							placeholder: '发生错误的函数完整路径',
						},
					},
				},
				error_message: {
					title: '错误详情',
					type: 'textarea',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入错误信息关键词',
						},
					},
					column: {
						minWidth: 450,
						showOverflowTooltip: true,
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						component: {
							props: {
								rows: 8,
								placeholder: '完整的错误堆栈信息和上下文，可能包含Traceback',
							},
						},
					},
				},
			},
		},
	};
};
