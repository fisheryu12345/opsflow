<template>
	<div class="item-com">
		<div class="item-com-header">
			<div class="item-com-header-bar" />
			<span class="item-com-title">{{ props.title }}</span>
		</div>
		<ul class="item-com-list">
			<li
				v-for="item in state.data"
				:key="item[props.value]"
				@click="handleClick(item)"
				:class="state.current === item[props.value] ? 'item-com-item active' : 'item-com-item'"
			>
				{{ item[props.label] }}
			</li>
		</ul>
		<div v-if="showPagination" class="item-com-pagination">
			<el-pagination
				background
				small
				hide-on-single-page
				v-model:current-page="state.page"
				v-model:page-size="state.limit"
				layout="prev, pager, next"
				:pager-count="5"
				:total="state.total"
				@current-change="handleCurrentChange"
			/>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { reactive, onMounted } from 'vue';
import { RoleInfoStateType } from './types';

const props = defineProps({
	type: {
		type: String,
		default: 'role',
	},
	title: {
		type: String,
		default: '标题',
	},
	label: {
		type: String,
		default: 'name',
	},
	value: {
		type: String,
		default: 'id',
	},
	showPagination: {
		type: Boolean,
		default: false,
	},
});
const emit = defineEmits(['fetchData', 'itemClick']);

const state = reactive<RoleInfoStateType>({
	current: '',
	page: 1,
	limit: 20,
	data: [],
	total: 10,
});

const fetchData = () => {
	emit(
		'fetchData',
		{
			page: state.page,
			limit: state.limit,
		},
		(res: { code: number; data: any[]; total: number }) => {
			if (res?.code === 2000) {
				state.data = res.data;
				state.total = res?.total || 10;
			}
		}
	);
};

const handleClick = (record: any) => {
	state.current = record[props.value];
	emit('itemClick', props.type, record);
};

const handleCurrentChange = (page: number) => {
	state.page = page;
	fetchData();
};

onMounted(() => {
	fetchData();
});
</script>

<style lang="scss" scoped>
@use '../../../../apps/opsflow/styles/opsflow-global' as *;

.item-com {
	width: 100%;
	height: 100%;
	display: flex;
	flex-direction: column;

	.item-com-header {
		display: flex;
		align-items: center;
		gap: 8px;
		padding-bottom: 10px;
		margin-bottom: 12px;
		border-bottom: 1px solid $of-border-light;
		flex-shrink: 0;

		.item-com-header-bar {
			width: 3px;
			height: 16px;
			border-radius: 2px;
			background: $of-gradient-blue;
			flex-shrink: 0;
		}

		.item-com-title {
			font-size: 14px;
			font-weight: 600;
			color: $of-text-primary;
		}
	}

	.item-com-list {
		flex: 1;
		overflow: auto;
		margin: 0;
		padding: 0;
		list-style: none;
		white-space: nowrap;

		.item-com-item {
			width: fit-content;
			min-width: 100%;
			padding: 9px 14px;
			border-radius: $of-radius-sm;
			cursor: pointer;
			transition: all $of-transition-default;
			color: $of-text-secondary;
			font-size: 13px;
			box-sizing: border-box;
		}

		.item-com-item:hover {
			background: $of-bg-card-hover;
			color: $of-color-primary;
		}

		.active {
			background: $of-bg-light-blue;
			color: $of-color-primary;
			font-weight: 600;
		}
	}

	.item-com-pagination {
		flex-shrink: 0;
		display: flex;
		justify-content: center;
		padding-top: 8px;
	}
}
</style>
