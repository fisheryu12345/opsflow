<template>
	<div class="layout-navbars-container">
		<template v-if="['classic','transverse'].includes(themeConfig.layout)">
			<Logo />
			<div class="navbars-tags-area" v-if="setShowTagsView">
				<TagsView />
			</div>
			<Horizontal v-if="isLayoutTransverse" :menu-list="horizontalMenuList" />
			<div class="navbars-right-area">
				<User />
			</div>
		</template>
		<template v-else>
			<!-- Default layout: Collapse btn + TagsView + User -->
			<SvgIcon
				class="navbars-collapse-icon"
				:name="themeConfig.isCollapse ? 'ele-Expand' : 'ele-Fold'"
				:size="16"
				@click="onToggleCollapse"
			/>
			<div class="navbars-tags-area" v-if="setShowTagsView">
				<TagsView />
			</div>
			<div class="navbars-right-area">
				<User />
			</div>
		</template>
	</div>
</template>

<script setup lang="ts" name="layoutNavBars">
import { defineAsyncComponent, computed, reactive, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { useRoutesList } from '/@/stores/routesList';
import mittBus from '/@/utils/mitt';
import { Local } from '/@/utils/storage';

// 引入组件
const User = defineAsyncComponent(() => import('/@/layout/navBars/breadcrumb/user.vue'));
const Logo = defineAsyncComponent(() => import('/@/layout/logo/index.vue'));
const Horizontal = defineAsyncComponent(() => import('/@/layout/navMenu/horizontal.vue'));
const TagsView = defineAsyncComponent(() => import('/@/layout/navBars/tagsView/tagsView.vue'));

// 定义变量内容
const storesThemeConfig = useThemeConfig();
const storesRoutesList = useRoutesList();
const { themeConfig } = storeToRefs(storesThemeConfig);
const { routesList } = storeToRefs(storesRoutesList);
const route = useRoute();

// 折叠/展开侧边栏
const onToggleCollapse = () => {
	themeConfig.value.isCollapse = !themeConfig.value.isCollapse;
	Local.remove('themeConfig');
	Local.set('themeConfig', themeConfig.value);
};

// 是否显示 tagsView
const setShowTagsView = computed(() => {
	let { layout, isTagsview } = themeConfig.value;
	return layout !== 'classic' && isTagsview;
});

// 横向菜单显示
const isLayoutTransverse = computed(() => {
	let { layout, isClassicSplitMenu } = themeConfig.value;
	return layout === 'transverse' || (isClassicSplitMenu && layout === 'classic');
});

const state = reactive({
	menuList: [] as RouteItems,
});

const horizontalMenuList = computed(() => state.menuList);

// 设置/过滤路由
const setFilterRoutes = () => {
	let { layout, isClassicSplitMenu } = themeConfig.value;
	if (layout === 'classic' && isClassicSplitMenu) {
		state.menuList = delClassicChildren(filterRoutesFun(routesList.value));
		const resData = setSendClassicChildren(route.path);
		mittBus.emit('setSendClassicChildren', resData);
	} else {
		state.menuList = filterRoutesFun(routesList.value);
	}
};

const delClassicChildren = <T extends ChilType>(arr: T[]): T[] => {
	arr.map((v: T) => {
		if (v.children) delete v.children;
	});
	return arr;
};

const filterRoutesFun = <T extends RouteItem>(arr: T[]): T[] => {
	return arr
		.filter((item: T) => !item.meta?.isHide)
		.map((item: T) => {
			item = Object.assign({}, item);
			if (item.children) item.children = filterRoutesFun(item.children);
			return item;
		});
};

const setSendClassicChildren = (path: string) => {
	const currentPathSplit = path.split('/');
	let currentData: MittMenu = { children: [] };
	filterRoutesFun(routesList.value).map((v: RouteItem, k: number) => {
		if (v.path === `/${currentPathSplit[1]}`) {
			v['k'] = k;
			currentData['item'] = { ...v };
			currentData['children'] = [{ ...v }];
			if (v.children) currentData['children'] = v.children;
		}
	});
	return currentData;
};

onMounted(() => {
	setFilterRoutes();
	mittBus.on('setSendClassicChildren', () => {
		setFilterRoutes();
	});
});

onUnmounted(() => {
	mittBus.off('setSendClassicChildren', () => {});
});
</script>

<style scoped lang="scss">
.layout-navbars-container {
	display: flex;
	align-items: center;
	width: 100%;
	height: 100%;
	background: var(--next-bg-topBar);
	border-bottom: 1px solid var(--next-border-color-light);
}

.navbars-tags-area {
	flex: 1;
	min-width: 120px;
	height: 100%;
	display: flex;
	align-items: center;
	overflow: hidden;
	padding-left: 4px;
	:deep(.layout-navbars-tagsview) {
		height: 100%;
		display: flex;
		align-items: center;
		background: transparent;
		border-bottom: none;
	}
	:deep(.el-scrollbar) {
		height: 100%;
	}
	:deep(.el-scrollbar__wrap) {
		overflow-x: auto !important;
	}
	:deep(.layout-navbars-tagsview-ul) {
		height: 32px;
		padding: 0 4px;
	}
	:deep(.layout-navbars-tagsview-ul-li) {
		height: 24px;
		line-height: 24px;
		padding: 0 10px;
		font-size: 11px;
		margin-right: 4px;
	}
	:deep(.layout-navbars-tagsview-ul-li-iconfont) {
		font-size: 11px;
	}
}

.navbars-collapse-icon {
	flex-shrink: 0;
	cursor: pointer;
	font-size: 18px;
	color: var(--next-bg-topBarColor);
	height: 100%;
	width: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	opacity: 0.8;
	&:hover { opacity: 1; }
}

.navbars-right-area {
	margin-left: auto;
	flex-shrink: 0;
	display: flex;
	align-items: center;
	height: 100%;
}
</style>
