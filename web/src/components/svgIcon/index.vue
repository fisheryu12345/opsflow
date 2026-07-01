<template>
	<i v-if="showEleIcon" class="el-icon" :style="setIconSvgStyle">
		<component :is="eleIconComponent" />
	</i>
	<i v-else-if="isShowIconSvg" class="el-icon" :style="setIconSvgStyle">
		<component :is="getIconName" />
	</i>
	<div v-else-if="isShowIconImg" :style="setIconImgOutStyle">
		<img :src="getIconName" :style="setIconSvgInsStyle" />
	</div>
	<i v-else :class="getIconName" :style="setIconSvgStyle" />
</template>

<script setup lang="ts" name="svgIcon">
import { computed, shallowRef } from 'vue';
import * as ElementPlusIcons from '@element-plus/icons-vue';

const props = defineProps({
	name: { type: String },
	size: { type: Number, default: () => 14 },
	color: { type: String },
});

const eleIconComponent = shallowRef<any>(null);

// Convert iconfont name to Element Plus icon name
// e.g. "iconfont icon-lock" → "Lock", "iconfont icon-bell" → "Bell"
function toEleIconName(name: string): string | null {
	if (!name) return null;
	// Extract the icon-xxx part
	const match = name.match(/icon-([a-zA-Z0-9_-]+)/);
	if (!match) return null;
	const iconName = match[1];
	// Map common names to Element Plus icon names
	const ICON_MAP: Record<string, string> = {
		'lock': 'Lock',
		'bell': 'Bell',
		'xiaoxizhongxin': 'Bell',
		'system': 'Setting',
		'xitongshezhi': 'Setting',
		'configure': 'Tools',
		'file': 'FolderOpened',
		'gongju': 'Grid',
		'diannao1': 'Operation',
		'fuwenbenkuang': 'Folder',
		'shoujidiannao': 'Monitor',
		'dianhua': 'Headset',
		'barcode-qr': 'Ticket',
		'LoggedinPC': 'Message',
		'zhongduancanshuchaxun': 'DataBoard',
		'step': 'Connection',
		'siweidaotu': 'List',
		'caozuorizhi': 'List',
		'shouye_dongtaihui': 'HomeFilled',
		'Area': 'Grid',
		'dict': 'Notebook',
		'guanlidenglurizhi': 'Document',
		'rizhi': 'Document',
	};
	return ICON_MAP[iconName] || null;
}

const showEleIcon = computed(() => {
	const iconName = toEleIconName(props.name || '');
	const icons = ElementPlusIcons as Record<string, any>;
	if (iconName && icons[iconName]) {
		eleIconComponent.value = icons[iconName];
		return true;
	}
	return false;
});

// 在线链接、本地引入地址前缀
const linesString = ['https', 'http', '/src', '/assets', 'data:image', import.meta.env.VITE_PUBLIC_PATH];

const getIconName = computed(() => props?.name);
const isShowIconSvg = computed(() => props?.name?.startsWith('ele-'));
const isShowIconImg = computed(() => linesString.find((str) => props.name?.startsWith(str)));
const setIconSvgStyle = computed(() => `font-size: ${props.size}px;color: ${props.color};`);
const setIconImgOutStyle = computed(() => `width: ${props.size}px;height: ${props.size}px;display: inline-block;overflow: hidden;`);
const setIconSvgInsStyle = computed(() => {
	const filterStyle: string[] = [];
	const compatibles: string[] = ['-webkit', '-ms', '-o', '-moz'];
	compatibles.forEach((j) => filterStyle.push(`${j}-filter: drop-shadow(${props.color} 30px 0);`));
	return `width: ${props.size}px;height: ${props.size}px;position: relative;left: -${props.size}px;${filterStyle.join('')}`;
});
</script>
