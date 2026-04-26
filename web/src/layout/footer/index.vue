<template>
	<div class="layout-footer pb5 pt2">
		<div class="layout-footer-warp">
			<div>Fisher Trade Support</div>
		</div>
	</div>
</template>

<script setup lang="ts" name="layoutFooter">
// 此处需有内容（注释也得），否则缓存将失败
</script>

<style scoped lang="scss">
.layout-footer {
	width: 100%;
	display: flex;
	&-warp {
    color: var(--el-text-color-secondary);
		text-align: center;
    margin: 10px auto auto;
    animation: error-num 0.3s ease;
	}
}
</style>
