<template>
	<div class="columns-table-com">
		<div class="ctc-header">
			<div class="ctc-header-left">
				<div class="ctc-header-bar" />
				<span class="ctc-title">字段权限</span>
			</div>
			<div class="ctc-actions">
				<el-button type="primary" size="small" @click="handleUpdateColumn('create')">
					<el-icon><Plus /></el-icon> 新增
				</el-button>
				<el-button size="small" @click="handleAutomatch">
					自动匹配
				</el-button>
			</div>
		</div>

		<el-table :data="state.data" stripe v-loading="state.loading" class="ctc-table" size="small">
			<el-table-column prop="field_name" label="字段名" min-width="120" show-overflow-tooltip />
			<el-table-column prop="title" label="列名" min-width="120" show-overflow-tooltip />
			<el-table-column label="操作" width="200" align="center">
				<template #default="scope">
					<el-button size="small" text type="primary" @click="handleUpdateColumn('update', scope.row)">
						<el-icon><Edit /></el-icon> 编辑
					</el-button>
					<el-popconfirm title="确定删除该字段吗？" @confirm="handleDelete(scope.row)">
						<template #reference>
							<el-button size="small" text type="danger">
								<el-icon><Delete /></el-icon> 删除
							</el-button>
						</template>
					</el-popconfirm>
				</template>
			</el-table-column>
		</el-table>

		<div class="ctc-pagination">
			<el-pagination
				v-model:current-page="searchParams.page"
				v-model:page-size="searchParams.limit"
				:page-sizes="[5, 10, 20, 50]"
				:total="state.total"
				background
				small
				layout="total, sizes, prev, pager, next, jumper"
				@size-change="handleSizeChange"
				@current-change="handleCurrentChange"
			/>
		</div>

		<el-drawer v-model="drawerVisible" title="字段权限" direction="rtl" size="500px"
			:close-on-click-modal="false" :before-close="handleDrawerClose" class="ctc-drawer">
			<ColumnsFormCom v-if="drawerVisible" :currentInfo="props.currentInfo" :initFormData="drawerFormData"
				@drawerClose="handleDrawerClose" />
		</el-drawer>
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { Plus, Edit, Delete } from '@element-plus/icons-vue';
import ColumnsFormCom from '../ColumnsFormCom/index.vue';
import { getColumnsData, automatchColumnsData, deleteColumnsData, updateColumnsData } from './api';
import { successNotification, warningNotification } from '/@/utils/message';
import { APIResponseData, CurrentInfoType, ColumnsFormDataType, AddColumnsDataType } from '../../types';

const props = defineProps({
	currentInfo: {
		type: Object as () => CurrentInfoType,
		required: true,
		default: () => ({}),
	},
});

const searchParams = reactive({
	page: 1,
	limit: 20,
});
const state = reactive({
	loading: false,
	data: [] as any[],
	total: 0,
});
const drawerVisible = ref(false);
const drawerFormData = ref<Partial<ColumnsFormDataType>>({});

const fetchData = async (query: CurrentInfoType = props.currentInfo) => {
	try {
		state.loading = true;
		const res = await getColumnsData({ ...searchParams, ...query });
		if (res?.code === 2000) {
			state.data = res.data;
			state.total = res.total;
		}
	} finally {
		state.loading = false;
	}
};

/**
 * 自动匹配列
 */
const handleAutomatch = async () => {
	if (props.currentInfo?.role && props.currentInfo?.model && props.currentInfo?.app) {
		const res = await automatchColumnsData(props.currentInfo);
		if (res?.code === 2000) {
			successNotification('匹配成功');
			fetchData();
		}
		return;
	}
	warningNotification('请选择角色和模型表！');
};

/**
 * 新增 or 编辑
 */
const handleUpdateColumn = (type: string, record?: ColumnsFormDataType) => {
	if (props.currentInfo?.role && props.currentInfo?.model && props.currentInfo?.app) {
		if (type === 'update' && record) {
			drawerFormData.value = record;
		}
		drawerVisible.value = true;
		return;
	}
	warningNotification('请选择角色和模型表！');
};

const handleDrawerClose = (type?: string) => {
	if (type === 'submit') {
		fetchData();
	}
	drawerVisible.value = false;
	drawerFormData.value = {};
};

/**
 * 删除
 */
const handleDelete = async ({ id }: { id: number }) => {
	const res = await deleteColumnsData(id);
	if (res?.code === 2000) {
		successNotification('删除成功');
		fetchData();
	}
};

const handleChange = (record: AddColumnsDataType) => {
	updateColumnsData(record).then((res: APIResponseData) => {
		successNotification(res.msg || '更新成功');
	});
};

/**
 * 分页
 */
const handleSizeChange = (limit: number) => {
	searchParams.limit = limit;
	fetchData();
};
const handleCurrentChange = (page: number) => {
	searchParams.page = page;
	fetchData();
};

defineExpose({ fetchData });
</script>

<style lang="scss" scoped>
@use '../../../../apps/opsflow/styles/opsflow-global' as *;

.columns-table-com {
	height: 100%;
	display: flex;
	flex-direction: column;

	.ctc-header {
		flex-shrink: 0;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 10px;
		margin-bottom: 12px;
		border-bottom: 1px solid $of-border-light;

		.ctc-header-left {
			display: flex;
			align-items: center;
			gap: 8px;

			.ctc-header-bar {
				width: 3px;
				height: 16px;
				border-radius: 2px;
				background: $of-gradient-blue;
				flex-shrink: 0;
			}

			.ctc-title {
				font-size: 14px;
				font-weight: 600;
				color: $of-text-primary;
			}
		}

		.ctc-actions {
			display: flex;
			gap: 8px;
		}
	}

	.ctc-table {
		flex: 1;
		width: 100%;
		min-height: 0;
	}
	.ctc-table :deep(.el-table th.el-table__cell) {
		background: $of-bg-header;
		color: $of-text-secondary;
		font-weight: 600;
		font-size: 12px;
	}
	.ctc-table :deep(.el-table__body tr:hover td) {
		background: $of-bg-card-hover;
	}

	.ctc-pagination {
		flex-shrink: 0;
		display: flex;
		justify-content: flex-end;
		padding-top: 10px;
	}

	/* Drawer — OPSflow-style header */
	.ctc-drawer :deep(.el-drawer__header) {
		@include of-dialog-header;
	}
}
</style>
