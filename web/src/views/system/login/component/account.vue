<template>
	<el-form ref="formRef" size="large" class="login-content-form" :model="state.ruleForm" :rules="rules">
		<el-form-item class="login-animation1" prop="username">
			<el-input type="text" :placeholder="$t('message.account.accountPlaceholder1')" v-model="ruleForm.username"
				clearable autocomplete="off">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-User /></el-icon>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation2" prop="password">
			<el-input :type="isShowPassword ? 'text' : 'password'" :placeholder="$t('message.account.accountPlaceholder2')"
				v-model="ruleForm.password">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-Unlock /></el-icon>
				</template>
				<template #suffix>
					<i class="iconfont el-input__icon login-content-password"
						:class="isShowPassword ? 'icon-yincangmima' : 'icon-xianshimima'"
						@click="isShowPassword = !isShowPassword">
					</i>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation3" v-if="isShowCaptcha" prop="captcha">
			<el-col :span="15">
				<el-input type="text" maxlength="4" :placeholder="$t('message.account.accountPlaceholder3')"
					v-model="ruleForm.captcha" clearable autocomplete="off">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Position /></el-icon>
					</template>
				</el-input>
			</el-col>
			<el-col :span="1"></el-col>
			<el-col :span="8">
				<el-button class="login-content-captcha">
					<el-image :src="ruleForm.captchaImgBase" @click="refreshCaptcha" />
				</el-button>
			</el-col>
		</el-form-item>
		<el-form-item class="login-animation4">
			<el-button type="primary" class="login-content-submit" round @keyup.enter="loginClick" @click="loginClick"
				:loading="loading.signIn">
				<span>{{ $t('message.account.accountBtnText') }}</span>
			</el-button>
		</el-form-item>
		<!-- SSO/OAuth2 login buttons -->
		<el-form-item class="login-animation4">
			<el-divider><span style="font-size:12px;color:#909399;">第三方登录</span></el-divider>
			<div style="display:flex;gap:12px;width:100%;justify-content:center;">
				<el-button size="small" round @click="oauthLogin('oidc')" title="OIDC">
					<el-icon><ele-Promotion /></el-icon> OIDC
				</el-button>
				<el-button size="small" round @click="oauthLogin('wecom')" title="企业微信">
					<el-icon><ele-Message /></el-icon> 企业微信
				</el-button>
				<el-button size="small" round @click="oauthLogin('dingtalk')" title="钉钉">
					<el-icon><ele-Bell /></el-icon> 钉钉
				</el-button>
			</div>
		</el-form-item>
	</el-form>
</template>

<script lang="ts">
import { toRefs, reactive, defineComponent, computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, FormInstance, FormRules } from 'element-plus';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { initFrontEndControlRoutes } from '/@/router/frontEnd';
import { initBackEndControlRoutes } from '/@/router/backEnd';
import { Session } from '/@/utils/storage';
import { formatAxis } from '/@/utils/formatTime';
import { NextLoading } from '/@/utils/loading';
import * as loginApi from '/@/views/system/login/api';
import { useUserInfo } from '/@/stores/userInfo';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { Md5 } from 'ts-md5';
import { errorMessage } from '/@/utils/message';

export default defineComponent({
	name: 'loginAccount',
	setup() {
		const { t } = useI18n();
		const storesThemeConfig = useThemeConfig();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { userInfos } = storeToRefs(useUserInfo());
		const route = useRoute();
		const router = useRouter();
		const state = reactive({
			isShowPassword: false,
			ruleForm: {
				username: '',
				password: '',
				captcha: '',
				captchaKey: '',
				captchaImgBase: '',
			},
			loading: {
				signIn: false,
			},
		});
		const rules = reactive<FormRules>({
			username: [
				{ required: true, message: '请填写账号', trigger: 'blur' },
			],
			password: [
				{
					required: true,
					message: '请填写密码',
					trigger: 'blur',
				},
			],
			captcha: [
				{
					required: true,
					message: '请填写验证码',
					trigger: 'blur',
				},
			],
		})
		const formRef = ref();
		// 时间获取
		const currentTime = computed(() => {
			return formatAxis(new Date());
		});
		// 是否关闭验证码
		const isShowCaptcha = computed(() => {
			return SystemConfigStore().systemConfig['base.captcha_state'];
		});

		const getCaptcha = async () => {
			loginApi.getCaptcha().then((ret: any) => {
				state.ruleForm.captchaImgBase = ret.data.image_base;
				state.ruleForm.captchaKey = ret.data.key;
			});
		};
		const refreshCaptcha = async () => {
			state.ruleForm.captcha=''
			loginApi.getCaptcha().then((ret: any) => {
				state.ruleForm.captchaImgBase = ret.data.image_base;
				state.ruleForm.captchaKey = ret.data.key;
			});
		};
		const loginClick = async () => {
			if (!formRef.value) return
			await formRef.value.validate((valid: any) => {
				if (valid) {
					loginApi.login({ ...state.ruleForm, password: Md5.hashStr(state.ruleForm.password) }).then((res: any) => {
						if (res.code === 2000) {
							Session.set('token', res.data.access);
							Cookies.set('username', res.data.name);
							if (!themeConfig.value.isRequestRoutes) {
								// 前端控制路由，2、请注意执行顺序
								initFrontEndControlRoutes();
								loginSuccess();
							} else {
								// 模拟后端控制路由，isRequestRoutes 为 true，则开启后端控制路由
								initBackEndControlRoutes();
								loginSuccess();
							}
						}
					}).catch((err: any) => {
						refreshCaptcha();
					});
				} else {
					errorMessage("请填写登录信息")
				}
			})

		};
		const getUserInfo = () => {
			useUserInfo().setUserInfos();
		};

		// OAuth2/SSO login redirect
		const oauthLogin = (provider: string) => {
			window.location.href = loginApi.getOAuthLoginUrl(provider);
		};

		// 登录成功后的跳转
		const loginSuccess = async () => {
			//登录成功获取用户信息,获取系统字典数据
			getUserInfo();
			//获取所有字典
			
			// 初始化登录成功时间问候语
			let currentTimeInfo = currentTime.value;
			// 登录成功，跳到转首页
			if (route.query?.redirect) {
				router.push({
					path: <string>route.query?.redirect,
					query: Object.keys(<string>route.query?.params).length > 0 ? JSON.parse(<string>route.query?.params) : '',
				});
			} else {
				router.push('/');
			}
			// 登录成功提示
			state.loading.signIn = true;
			const signInText = t('message.signInText');
			ElMessage.success(`${currentTimeInfo}，${signInText}`);
			// 添加 loading，防止第一次进入界面时出现短暂空白
			NextLoading.start();
		};
		onMounted(() => {
			getCaptcha();
			//获取系统配置
			SystemConfigStore().getSystemConfigs();
		});


		return {
			refreshCaptcha,
			loginClick,
			loginSuccess,
			oauthLogin,
			isShowCaptcha,
			state,
			formRef,
			rules,
			...toRefs(state),
		};
	},
});
</script>

<style scoped lang="scss">
.login-content-form {
	margin-top: 20px;

	@for $i from 1 through 4 {
		.login-animation#{$i} {
			opacity: 0;
			animation-name: error-num;
			animation-duration: 0.5s;
			animation-fill-mode: forwards;
			animation-delay: calc($i/10) + s;
		}
	}

	.login-content-password {
		display: inline-block;
		width: 20px;
		cursor: pointer;

		&:hover {
			color: #909399;
		}
	}

	.login-content-captcha {
		width: 100%;
		padding: 0;
		font-weight: bold;
		letter-spacing: 5px;
	}

	.login-content-submit {
		width: 100%;
		letter-spacing: 2px;
		font-weight: 300;
		margin-top: 15px;
	}
}
</style>
