<template>
	<div
		class="layout-header-wrap"
	>
		<div class="layout-header-inner">
			<NavBarsIndex />
		</div>
	</div>
</template>

<script setup lang="ts" name="layoutHeader">
import { defineAsyncComponent } from 'vue';

// 引入组件
const NavBarsIndex = defineAsyncComponent(() => import('/@/layout/navBars/index.vue'));

</script>

<style scoped lang="scss">
.layout-header-wrap {
	flex-shrink: 0;
	overflow: hidden;
	transition: height 0.3s ease;
	height: 35px;
}
.layout-header-inner {
	height: 35px;
}
</style>
