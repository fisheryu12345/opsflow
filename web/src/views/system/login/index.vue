<template>
	<div class="login-container flex">
		<div class="login-left of-fade-in-up">
			<div class="login-left-logo">
				<img :src="logoMini" />
			</div>
			<div class="login-left-img">
				<img :src="loginMain" />
			</div>
			<img :src="loginBg" class="login-left-waves" />
		</div>
		<div class="login-right flex">
			<div class="login-right-warp flex-margin of-fade-in-up" style="animation-delay: 0.15s;">
				<span class="login-right-warp-one"></span>
				<span class="login-right-warp-two"></span>
				<div class="login-right-warp-mian">
					<div class="login-right-warp-main-title">TRADE SYSTEM</div>
					<div class="login-right-warp-main-form">
						<div v-if="!state.isScan">
							<el-tabs v-model="state.tabsActiveName">
								<Account />
							</el-tabs>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="login-authorization of-fade-in-up" style="animation-delay: 0.3s;">
			<p>
				<a href="http://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
					湘ICP备2026014297号
				</a>
			</p>
		</div>
	</div>
</template>

<script setup lang="ts" name="loginIndex">
import { defineAsyncComponent, onMounted, reactive, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { NextLoading } from '/@/utils/loading';
import logoMini from '/@/assets/hsbc.svg';
import loginMain from '/@/assets/main2.svg';
import loginBg from '/@/assets/login-bg.svg';
import {SystemConfigStore} from '/@/stores/systemConfig'
// 引入组件
const Account = defineAsyncComponent(() => import('/@/views/system/login/component/account.vue'));
const Mobile = defineAsyncComponent(() => import('/@/views/system/login/component/mobile.vue'));
const Scan = defineAsyncComponent(() => import('/@/views/system/login/component/scan.vue'));

// 定义变量内容
const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);
const state = reactive({
	tabsActiveName: 'account',
	isScan: false,
});

// 获取布局配置信息
const getThemeConfig = computed(() => {
	return themeConfig.value;
});

const systemConfigStore = SystemConfigStore()
const {systemConfig} = storeToRefs(systemConfigStore)
const getSystemConfig = computed(()=>{
  return systemConfig.value
})

// 页面加载时
onMounted(() => {
	NextLoading.done();
});
</script>

<style scoped lang="scss">
@use '../../../styles/opsflow-global' as *;

.login-container {
	height: 100%;
	background: $of-gradient-hero;

	.login-left {
		flex: 1;
		position: relative;
		background: $of-gradient-accent;
		margin-right: 80px;

		.login-left-logo {
			display: flex;
			align-items: center;
			position: absolute;
			top: 5px;
			left: 80px;
			z-index: 1;

			img {
				width: 250px;
				height: 250px;
			}
		}

		.login-left-img {
			position: absolute;
			top: 50%;
			left: 50%;
			transform: translate(-50%, -50%);
			width: 100%;
			height: 52%;

			img {
				width: 100%;
				height: 100%;
			}
		}

		.login-left-waves {
			position: absolute;
			top: 0;
			right: -100px;
		}
	}

	.login-right {
		width: 700px;

		.login-right-warp {
			@extend .of-card;
			width: 500px;
			height: 500px;
			position: relative;
			overflow: hidden;
			border: 1px solid $of-border-blue;
			box-shadow: $of-shadow-primary;

			.login-right-warp-one,
			.login-right-warp-two {
				position: absolute;
				display: block;
				width: inherit;
				height: inherit;

				&::before,
				&::after {
					content: '';
					position: absolute;
					z-index: 1;
				}
			}

			.login-right-warp-one {
				&::before {
					filter: hue-rotate(0deg);
					top: 0px;
					left: 0;
					width: 100%;
					height: 3px;
					background: linear-gradient(90deg, transparent, $of-color-primary);
					animation: loginLeft 3s linear infinite;
				}

				&::after {
					filter: hue-rotate(60deg);
					top: -100%;
					right: 2px;
					width: 3px;
					height: 100%;
					background: linear-gradient(180deg, transparent, $of-color-primary);
					animation: loginTop 3s linear infinite;
					animation-delay: 0.7s;
				}
			}

			.login-right-warp-two {
				&::before {
					filter: hue-rotate(120deg);
					bottom: 2px;
					right: -100%;
					width: 100%;
					height: 3px;
					background: linear-gradient(270deg, transparent, $of-color-primary);
					animation: loginRight 3s linear infinite;
					animation-delay: 1.4s;
				}

				&::after {
					filter: hue-rotate(300deg);
					bottom: -100%;
					left: 0px;
					width: 3px;
					height: 100%;
					background: linear-gradient(360deg, transparent, $of-color-primary);
					animation: loginBottom 3s linear infinite;
					animation-delay: 2.1s;
				}
			}

			.login-right-warp-mian {
				display: flex;
				flex-direction: column;
				height: 100%;

				.login-right-warp-main-title {
					height: 130px;
					line-height: 130px;
					font-size: 36px;
					text-align: center;
					letter-spacing: 3px;
					font-weight: 700;
					animation: ofFadeInUp 0.5s ease both;
					animation-delay: 0.3s;
					background: $of-gradient-accent;
					-webkit-background-clip: text;
					-webkit-text-fill-color: transparent;
					background-clip: text;
				}

				.login-right-warp-main-form {
					flex: 1;
					padding: 0 50px 50px;
				}
			}
		}
	}

	.login-authorization {
		position: fixed;
		bottom: 30px;
		left: 0;
		right: 0;
		text-align: center;

		p {
			font-size: 14px;
			color: $of-text-muted;
		}

		a {
			color: $of-color-primary;
			margin: 0 5px;
		}
	}
}
</style>
