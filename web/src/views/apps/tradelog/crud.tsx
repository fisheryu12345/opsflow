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
						show: false, // 交易日志为系统自动生成，不允许手动添加
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
						show: false, // 交易日志为只读，不允许编辑
					},
					remove: {
						type: 'text',
						show: false, // 不建议删除日志记录
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
							placeholder: '请输入函数名称或日志内容',
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
					title: '日志时间',
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
						show: true,
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '例如: execute_entry_order',
						},
					},
					column: {
						minWidth: 140,
						showOverflowTooltip: true,
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						rules: [{ required: true, message: '函数名称不能为空' }],
						component: {
							placeholder: '生成日志的函数完整路径',
						},
					},
				},
				log_level: {
					title: '日志级别',
					type: 'dict-select',
					dict: dict({
						data: [
							// { value: 'DEBUG', label: '调试' },
							{ value: 'INFO', label: '信息' },
							{ value: 'SUCCESS', label: '成功' },
							{ value: 'WARNING', label: '警告' },
							// { value: 'ERROR', label: '错误' },
							// { value: 'CRITICAL', label: '严重' }
						]
					}),
					search: {
						show: true,
						disabled: false,
						component: {
							props: {
								clearable: true,
								placeholder: '请选择日志级别'
							}
						}
					},
					column: {
						minWidth: 100,
						align: 'center',
						formatter: ({ row }) => {
							const levelMap: Record<string, string> = {
								DEBUG: '调试',
								INFO: '信息',
								SUCCESS: '成功',
								WARNING: '警告',
								ERROR: '错误',
								CRITICAL: '严重'
							};
							return levelMap[row.log_level] || row.log_level;
						}
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						rules: [{ required: true, message: '日志级别不能为空' }],
						component: {
							placeholder: '日志级别',
						},
					},
				},
				symbol: {
					title: '合约代码',
					type: 'input',
					search: {
						show: true,
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '例如: rb2610',
						},
					},
					column: {
						minWidth: 80,
						showOverflowTooltip: true,
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						rules: [{ required: true, message: '函数名称不能为空' }],
						component: {
							placeholder: '生成日志的函数完整路径',
						},
					},
				},
				log_message: {
					title: '日志内容',
					type: 'textarea',
					search: {
						disabled: false,
						component: {
							props: {
								clearable: true,
							},
							placeholder: '请输入日志内容关键词',
						},
					},
					column: {
						minWidth: 400,
						showOverflowTooltip: true,
					},
					form: {
						show: false, // 自动记录，不允许手动设置
						component: {
							props: {
								rows: 6,
								placeholder: '详细的日志信息，包括关键参数、计算结果、决策原因等',
							},
						},
					},
				},
			},
		},
	};
};
