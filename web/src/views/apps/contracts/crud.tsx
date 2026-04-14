import * as api from './api';
import {
	dict,
	UserPageQuery,
	AddReq,
	DelReq,
	EditReq,
	compute,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet
} from '@fast-crud/fast-crud';
import { dictionary } from '/@/utils/dictionary';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox } from 'element-plus';
import { ref } from 'vue';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	// 使用 ref 存储动态加载的字典数据
	const exchangeOptions = ref<any[]>([]);
	const sectorOptions = ref<any[]>([]);

	/**
	 * 加载交易所列表
	 */
	const loadExchanges = async () => {
		try {
			const res = await api.GetExchanges();
			exchangeOptions.value = res.map((item: any) => ({
				label: `${item.label} (${item.count})`,
				value: item.value
			}));
		} catch (error) {
			console.error('加载交易所列表失败:', error);
		}
	};

	/**
	 * 加载板块列表
	 */
	const loadSectors = async () => {
		try {
			const res = await api.GetSectors();
			sectorOptions.value = res.map((item: any) => ({
				label: `${item.value} (${item.count})`,
				value: item.value
			}));
		} catch (error) {
			console.error('加载板块列表失败:', error);
		}
	};

	// 立即加载字典数据
	loadExchanges();
	loadSectors();

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

	/**
	 * 切换单个合约状态
	 */
	const handleToggleActive = async (row: any) => {
		try {
			const res = await api.ToggleActive(row.id);
			successMessage(res.message || '操作成功');
			crudExpose.doRefresh();
		} catch (error: any) {
			errorMessage(error.message || '操作失败');
		}
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				editRequest,
				delRequest,
			},
			actionbar: {
				buttons: {
					add: {
						show: false,  // 隐藏新增按钮
					},
				}
			},
			rowHandle: {
				fixed: 'right',
				width: 200,  // 调整宽度，只保留切换状态按钮
				buttons: {
					view: {
						show: false,
					},
					edit: {
						show: true  // 隐藏编辑按钮
					},
					remove: {
						show: false  // 隐藏删除按钮
					},
					toggleActive: {
						text: compute((context) => {
							return context.row.is_active ? '停用' : '激活';
						}),
						type: 'info',
						iconRight: compute((context) => {
							return context.row.is_active ? 'Close' : 'Check';
						}),
						show: true,  // 始终显示
						click: compute((context) => {
							return () => handleToggleActive(context.row);
						})
					},
				},
			},
			pagination: {
				show: true,
				defaultPageSize: 20,
			},
			search: {
				show: true,  // 确保搜索区域显示
				// 移除折叠功能，直接显示搜索表单
				buttons: {
					search: {
						text: '搜索',
					},
					reset: {
						text: '重置',
					}
				}
			},
			table: {
				rowKey: 'id',
				border: true,
				stripe: true,
				// 禁用多选功能
				selection: {
					show: false,  // 不显示复选框列
				},
			},
			columns: {
				_index: {
					title: '序号',
					form: { show: false },
					column: {
						type: 'index',
						align: 'center',
						width: '70px',
						columnSetDisabled: true,
					},
				},
				exchange: {
					title: '交易所',
					search: {
						show: true,
						component: {
							name: 'el-select',
							props: {
								clearable: true,
								placeholder: '请选择交易所',
							},
							options: exchangeOptions,  // 直接使用 ref
						}
					},
					type: 'dict-select',
					column: {
						width: 100,
						align: 'center',
						sorter: true,  // 启用排序
					},
					dict: dict({
						data: [
							{ value: 'SHFE', label: '上期所' },
							{ value: 'DCE', label: '大商所' },
							{ value: 'CZCE', label: '郑商所' },
							{ value: 'CFFEX', label: '中金所' },
							{ value: 'GFEX', label: '广期所' },
						]
					}),
					form: {
						rules: [{ required: true, message: '交易所必填' }],
						component: {
							name: 'el-select',
							props: {
								placeholder: '请选择交易所',
							},
							options: exchangeOptions,  // 直接使用 ref
						}
					},
				},
				product_code: {
					title: '品种代码',
					search: {
						show: true,
					},
					type: 'input',
					column: {
						width: 100,
						align: 'center',
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '品种代码必填' }],
						component: {
							placeholder: '如：rb, MA, IF',
						},
					},
				},
				symbol: {
					title: '主力合约',
					search: {
						show: true,
					},
					type: 'input',
					column: {
						minWidth: 130,
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '主力合约代码必填' }],
						component: {
							placeholder: '如：SHFE.rb2410',
						},
					},
				},
				name: {
					title: '合约名称',
					search: {
						show: true,
					},
					type: 'input',
					column: {
						minWidth: 120,
					},
					form: {
						component: {
							placeholder: '请输入合约名称',
						},
					},
				},
				sector: {
					title: '所属板块',
					search: {
						show: true,
						component: {
							name: 'el-select',
							props: {
								clearable: true,
								placeholder: '请选择板块',
							},
							options: sectorOptions,  // 直接使用 ref
						}
					},
					type: 'dict-select',
					column: {
						width: 100,
						sorter: true,  // 启用排序
					},
					dict: dict({
						data: [
							{ value: '黑色金属', label: '黑色金属' },
							{ value: '有色金属', label: '有色金属' },
							{ value: '贵金属', label: '贵金属' },
							{ value: '能源化工', label: '能源化工' },
							{ value: '农产品', label: '农产品' },
							{ value: '软商品', label: '软商品' },
							{ value: '金融期货', label: '金融期货' },
						]
					}),
					form: {
						component: {
							name: 'el-select',
							props: {
								placeholder: '请选择板块',
							},
							options: sectorOptions,  // 直接使用 ref
						},
					},
				},
				category: {
					title: '详细分类',
					search: {
						show: false,
					},
					type: 'input',
					column: {
						width: 100,
						sorter: true,  // 启用排序
					},
					form: {
						component: {
							placeholder: '如：螺纹类、PTA类',
						},
					},
				},
				volume_multiple: {
					title: '合约乘数',
					type: 'number',
					column: {
						width: 100,
						align: 'right',
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '合约乘数必填' }],
						value: 10,
						component: {
							min: 1,
						},
					},
				},
				price_tick: {
					title: '最小变动',
					type: 'number',
					column: {
						width: 100,
						align: 'right',
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '最小变动价位必填' }],
						value: 1.0,
						component: {
							precision: 4,
							min: 0,
						},
					},
				},
				margin_ratio: {
					title: '保证金比例',
					type: 'number',
					column: {
						width: 110,
						align: 'right',
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '保证金比例必填' }],
						value: 0.1,
						component: {
							precision: 4,
							min: 0,
							max: 1,
						},
					},
				},
				is_active: {
					title: '交易状态',
					search: {
						show: true,
						component: {
							name: 'el-select',
							props: {
								clearable: true,
								placeholder: '请选择状态',
							},
							options: [  // 静态数据，不需要动态加载
								{ label: '启用', value: true },
								{ label: '停用', value: false },
							]
						}
					},
					type: 'dict-switch',
					column: {
						width: 100,
						align: 'center',
						sorter: true,  // 启用排序
						component: {
							name: 'el-switch',
							activeText: '',
							inactiveText: '',
							style: '--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6',
						},
					},
					dict: dict({
						data: [
							{ value: true, label: '启用', color: 'success' },
							{ value: false, label: '停用', color: 'info' },
						]
					}),
					form: {
						value: false,
						component: {
							activeText: '启用',
							inactiveText: '停用',
						},
					},
				},
				night_trading: {
					title: '夜盘交易',
					search: {
						show: true,
						component: {
							name: 'el-select',
							props: {
								clearable: true,
								placeholder: '请选择状态',
							},
							options: [  // 静态数据，不需要动态加载
								{ label: '是', value: true },
								{ label: '否', value: false },
							]
						}
					},
					type: 'dict-switch',
					column: {
						width: 100,
						align: 'center',
						sorter: true,  // 启用排序
						component: {
							name: 'el-switch',
							activeText: '',
							inactiveText: '',
							style: '--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6',
						},
					},
					dict: dict({
						data: [
							{ value: true, label: '是', color: 'success' },
							{ value: false, label: '否', color: 'info' },
						]
					}),
					form: {
						value: false,
						component: {
							activeText: '是',
							inactiveText: '否',
						},
					},
				},
			min_position: {
					title: '交易所限制最小开仓手数',
					type: 'number',
					column: {
						width: 100,
						align: 'right',
						sorter: true,  // 启用排序
					},
					form: {
						rules: [{ required: true, message: '交易所限制最小开仓手数' }],
						value: 1,
						component: {
							min: 1,
						},
					},
				},
				allow_open: {
					title: '允许开仓',
					type: 'dict-switch',
					column: {
						width: 100,
						align: 'center',
					},
					dict: dict({
						data: [
							{ value: true, label: '是', color: 'success' },
							{ value: false, label: '否', color: 'warning' },
						]
					}),
					form: {
						value: true,
						component: {
							activeText: '允许',
							inactiveText: '禁止',
						},
					},
				},
				created_at: {
					title: '创建时间',
					type: 'datetime',
					column: {
						width: 160,
						sorter: true,  // 启用排序
					},
					form: {
						show: false,
					},
				},
				updated_at: {
					title: '更新时间',
					type: 'datetime',
					column: {
						width: 160,
						sorter: true,  // 启用排序
					},
					form: {
						show: false,
					},
				},
			},
		},
	};
};
