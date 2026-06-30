<template>
	<div
		class="layout-header-wrap"
		:class="{ 'layout-header-hidden': autoHide }"
		v-show="!isTagsViewCurrenFull"
		@mouseenter="onHeaderEnter"
		@mouseleave="onHeaderLeave"
	>
		<!-- 触发区域：顶部边缘，隐藏时可见 -->
		<div v-if="autoHide" class="layout-header-trigger" @mouseenter="onTriggerEnter" @mouseleave="onTriggerLeave" />
		<div class="layout-header-inner">
			<NavBarsIndex />
		</div>
	</div>
</template>

<script setup lang="ts" name="layoutHeader">
import { defineAsyncComponent, ref, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { useTagsViewRoutes } from '/@/stores/tagsViewRoutes';

// 引入组件
const NavBarsIndex = defineAsyncComponent(() => import('/@/layout/navBars/index.vue'));

// 定义变量内容
const storesTagsViewRoutes = useTagsViewRoutes();
const { isTagsViewCurrenFull } = storeToRefs(storesTagsViewRoutes);

// ── Auto-hide 状态 ──
const autoHide = ref(true);
let leaveTimer: ReturnType<typeof setTimeout> | null = null;
let hoverTimer: ReturnType<typeof setTimeout> | null = null;

const onHeaderEnter = () => {
	if (leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null; }
	if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
	autoHide.value = false;
};
const onHeaderLeave = () => {
	leaveTimer = setTimeout(() => {
		autoHide.value = true;
		leaveTimer = null;
	}, 3000);
};
const onTriggerEnter = () => {
	if (hoverTimer) clearTimeout(hoverTimer);
	hoverTimer = setTimeout(() => {
		autoHide.value = false;
		hoverTimer = null;
	}, 1000);
};
const onTriggerLeave = () => {
	if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
};
onBeforeUnmount(() => {
	if (leaveTimer) clearTimeout(leaveTimer);
	if (hoverTimer) clearTimeout(hoverTimer);
});
</script>

<style scoped lang="scss">
.layout-header-wrap {
	flex-shrink: 0;
	overflow: hidden;
	transition: height 0.3s ease;
	height: 50px;
}
.layout-header-hidden {
	height: 0 !important;
	min-height: 0 !important;
	border: none !important;
	padding: 0 !important;
	margin: 0 !important;
}
.layout-header-trigger {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	height: 12px;
	z-index: 99999;
	cursor: default;
}
.layout-header-inner {
	height: 50px;
}
</style>
