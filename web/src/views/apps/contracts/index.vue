<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #actionbar-right>
				<el-button type="info" @click="handleShowStatistics">
					<el-icon><DataAnalysis /></el-icon>
					统计信息
				</el-button>
			</template>
		</fs-crud>
		
		<!-- 统计信息对话框 -->
		<el-dialog
			v-model="statisticsVisible"
			title="合约统计信息"
			width="600px"
			:close-on-click-modal="false"
		>
			<div v-if="statisticsData" class="statistics-content">
				<el-descriptions :column="2" border>
					<el-descriptions-item label="合约总数">
						<el-tag type="primary" size="large">{{ statisticsData.total }}</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="已激活">
						<el-tag type="success" size="large">{{ statisticsData.active }}</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="已停用">
						<el-tag type="info" size="large">{{ statisticsData.inactive }}</el-tag>
					</el-descriptions-item>
				</el-descriptions>
				
				<el-divider content-position="left">按交易所统计</el-divider>
				<el-table :data="statisticsData.by_exchange" border stripe max-height="200">
					<el-table-column prop="exchange" label="交易所" width="120" />
					<el-table-column prop="count" label="数量" align="right" />
				</el-table>
				
				<el-divider content-position="left">按板块统计</el-divider>
				<el-table :data="statisticsData.by_sector" border stripe max-height="300">
					<el-table-column prop="sector" label="板块" />
					<el-table-column prop="count" label="数量" align="right" width="100" />
				</el-table>
			</div>
			
			<template #footer>
				<el-button @click="statisticsVisible = false">关闭</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contractList">
import { onMounted, ref } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';
import { DataAnalysis } from '@element-plus/icons-vue';
import { errorMessage } from '/@/utils/message';

const statisticsVisible = ref(false);
const statisticsData = ref<any>(null);

const { crudBinding, crudRef, crudExpose } = useFs({ 
	createCrudOptions,
	onExpose: (expose) => {
		// 可以在这里做一些额外的初始化
	}
});

/**
 * 显示统计信息
 */
const handleShowStatistics = async () => {
	try {
		const res = await api.GetStatistics();
		statisticsData.value = res;
		statisticsVisible.value = true;
	} catch (error: any) {
		errorMessage(error.message || '获取统计信息失败');
	}
};

onMounted(() => {
	// 页面加载时自动获取数据
	crudExpose.doRefresh();
});
</script>

<style scoped lang="scss">
.statistics-content {
	.el-descriptions {
		margin-bottom: 20px;
	}
	
	.el-divider {
		margin: 20px 0 10px;
	}
}
</style>
