<template>
  <div class="personal-page layout-pd">
    <!-- ===== 顶部问候横幅 ===== -->
    <div class="of-fade-in-up personal-hero">
      <div class="personal-hero-content">
        <div class="personal-hero-avatar">
          <avatarSelector
            v-model="selectImgVisible"
            ref="avatarSelectorRef"
            @uploadImg="onUploadAvatar"
          />
        </div>
        <div class="personal-hero-info">
          <h2 class="personal-hero-greeting">{{ greeting }}，{{ form.username }}</h2>
          <p class="personal-hero-quote">生活变的再糟糕，也不妨碍我变得更好！</p>
          <div class="personal-hero-tags">
            <el-tag size="small" type="info" effect="plain" round>
              <el-icon style="margin-right:3px;vertical-align:-2px"><User /></el-icon>
              {{ form.name }}
            </el-tag>
            <el-tag size="small" type="primary" effect="plain" round>
              <el-icon style="margin-right:3px;vertical-align:-2px"><OfficeBuilding /></el-icon>
              {{ form.dept?.dept_name || form.dept_name || '未分配' }}
            </el-tag>
            <el-tag
              v-for="(r, i) in form.roles"
              :key="i"
              size="small"
              type="success"
              effect="plain"
              round
            >
              <el-icon style="margin-right:3px;vertical-align:-2px"><Suitcase /></el-icon>
              {{ r.name }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- ===== 左侧: 更新信息 ===== -->
      <el-col :xs="24" :sm="16">
        <!-- 基本信息 -->
        <div class="of-card personal-section of-fade-in-up" style="animation-delay:0.1s">
          <div class="personal-section-header">
            <span class="personal-section-icon" :style="{ background: 'linear-gradient(135deg, #409eff, #337ecc)' }">
              <el-icon :size="16"><EditPen /></el-icon>
            </span>
            <span>基本信息</span>
          </div>

          <el-form
            ref="infoFormRef"
            :model="form"
            :rules="infoRules"
            label-width="50px"
            size="default"
            class="personal-form"
          >
            <el-row :gutter="24">
              <el-col :xs="24" :sm="12" :md="8" class="mb18">
                <el-form-item label="昵称" prop="name">
                  <el-input v-model="form.name" placeholder="请输入昵称" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" class="mb18">
                <el-form-item label="邮箱">
                  <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" class="mb18">
                <el-form-item label="手机" prop="mobile">
                  <el-input v-model="form.mobile" placeholder="请输入手机" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12" :md="8" class="mb18">
                <el-form-item label="性别">
                  <el-select v-model="form.gender" placeholder="请选择性别" clearable class="w100">
                    <el-option
                      v-for="(g, i) in genderOptions"
                      :key="i"
                      :label="g.label"
                      :value="g.value"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item>
                  <el-button type="primary" size="default" @click="onUpdateInfo" round>
                    <el-icon><Position /></el-icon>
                    更新个人信息
                  </el-button>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <!-- 账号安全 -->
        <div class="of-card personal-section of-fade-in-up" style="animation-delay:0.2s">
          <div class="personal-section-header">
            <span class="personal-section-icon" :style="{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }">
              <el-icon :size="16"><Lock /></el-icon>
            </span>
            <span>账号安全</span>
          </div>

          <div class="personal-safe-item of-hover-shift" @click="passwordDialogVisible = true">
            <div class="personal-safe-item-left">
              <span class="personal-safe-item-icon" :style="{ background: 'linear-gradient(135deg, #f56c6c, #e6a23c)' }">
                <el-icon :size="16"><Lock /></el-icon>
              </span>
              <div class="personal-safe-item-info">
                <div class="personal-safe-item-label">账户密码</div>
                <div class="personal-safe-item-desc">当前密码强度：<span class="text-strong">强</span></div>
              </div>
            </div>
            <el-tag size="small" effect="plain" type="danger" round>立即修改</el-tag>
          </div>

          <div class="personal-safe-item">
            <div class="personal-safe-item-left">
              <span class="personal-safe-item-icon" :style="{ background: 'linear-gradient(135deg, #67c23a, #409eff)' }">
                <el-icon :size="16"><Iphone /></el-icon>
              </span>
              <div class="personal-safe-item-info">
                <div class="personal-safe-item-label">密保手机</div>
                <div class="personal-safe-item-desc">已绑定手机：{{ form.mobile || '未绑定' }}</div>
              </div>
            </div>
            <el-tag v-if="form.mobile" size="small" effect="dark" type="success" round>已绑定</el-tag>
            <el-tag v-else size="small" effect="plain" type="warning" round>未绑定</el-tag>
          </div>

          <div class="personal-safe-item">
            <div class="personal-safe-item-left">
              <span class="personal-safe-item-icon" :style="{ background: 'linear-gradient(135deg, #409eff, #67c23a)' }">
                <el-icon :size="16"><Message /></el-icon>
              </span>
              <div class="personal-safe-item-info">
                <div class="personal-safe-item-label">绑定邮箱</div>
                <div class="personal-safe-item-desc">已绑定邮箱：{{ form.email || '未绑定' }}</div>
              </div>
            </div>
            <el-tag v-if="form.email" size="small" effect="dark" type="success" round>已绑定</el-tag>
            <el-tag v-else size="small" effect="plain" type="warning" round>未绑定</el-tag>
          </div>
        </div>
      </el-col>

      <!-- ===== 右侧: 消息通知 ===== -->
      <el-col :xs="24" :sm="8">
        <div class="of-card personal-section personal-msg-section of-fade-in-up" style="animation-delay:0.15s">
          <div class="personal-section-header">
            <span class="personal-section-icon" :style="{ background: 'linear-gradient(135deg, #e6a23c, #f56c6c)' }">
              <el-icon :size="16"><Bell /></el-icon>
            </span>
            <span>消息通知</span>
            <el-button text type="primary" size="small" class="personal-msg-more" @click="goMessageCenter">
              更多
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div class="personal-msg-list">
            <div
              v-for="(item, i) in newsList"
              :key="i"
              class="personal-msg-item of-stagger-item"
              :style="{ animationDelay: `${i * 0.06}s` }"
              @click="goMessageCenter"
            >
              <span class="personal-msg-dot" />
              <div class="personal-msg-content">
                <div class="personal-msg-title">{{ item.title }}</div>
                <div class="personal-msg-meta">
                  {{ item.creator_name }} · {{ formatShortTime(item.create_datetime) }}
                </div>
              </div>
            </div>

            <el-empty
              v-if="newsList.length === 0"
              :image-size="48"
              description="暂无消息"
              style="padding:20px 0"
            />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== 密码修改 Dialog ===== -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="密码修改"
      width="460px"
      :close-on-click-modal="false"
      destroy-on-close
      class="opsflow-dialog"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="90px"
        label-position="left"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            placeholder="请输入原始密码"
            clearable
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            placeholder="请输入新密码（8-30位，含字母+数字）"
            clearable
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="newPassword2">
          <el-input
            v-model="passwordForm.newPassword2"
            placeholder="请再次输入新密码"
            clearable
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="onChangePassword" round>
          <el-icon><Check /></el-icon> 确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted, defineAsyncComponent } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Position, Check, User, OfficeBuilding, Suitcase,
  EditPen, Lock, Iphone, Message,
  Bell, ArrowRight,
} from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';
import { useUserInfo } from '/@/stores/userInfo';
import { getBaseURL } from '/@/utils/baseUrl';
import { formatAxis } from '/@/utils/formatTime';
import { dictionary } from '/@/utils/dictionary';
import { successMessage } from '/@/utils/message';
import * as api from './api';

/* ===================== Types ===================== */
interface PersonalForm {
  avatar: string;
  username: string;
  name: string;
  email: string;
  mobile: string;
  gender: number | null;
  dept: { dept_name: string; dept_id: number } | null;
  dept_name: string;
  roles: { id: number; name: string }[];
}

/* ===================== Greeting ===================== */
const greeting = computed(() => formatAxis(new Date()));

/* ===================== Form State ===================== */
const form = reactive<PersonalForm>({
  avatar: '',
  username: '',
  name: '',
  email: '',
  mobile: '',
  gender: null,
  dept: null,
  dept_name: '',
  roles: [],
});

/* ===================== Gender Options ===================== */
const genderOptions = ref<{ label: string; value: number }[]>([]);

/* ===================== Form Validation ===================== */
const infoFormRef = ref<any>(null);
const infoRules = {
  name: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  mobile: [{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确手机号', trigger: 'blur' }],
};

/* ===================== Avatar ===================== */
const avatarSelectorRef = ref<any>(null);
const selectImgVisible = ref(false);
const avatarSelector = defineAsyncComponent(() => import('/@/components/avatarSelector/index.vue'));

/* ===================== Message Notifications ===================== */
const newsList = ref<any[]>([]);

/* ===================== Password Dialog ===================== */
const passwordDialogVisible = ref(false);
const passwordLoading = ref(false);
const passwordFormRef = ref<any>(null);
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  newPassword2: '',
});

const validateNewPass = (_rule: any, value: string, callback: Function) => {
  const pwdRegex = /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/;
  if (!value) {
    callback(new Error('请输入密码'));
  } else if (value === passwordForm.oldPassword) {
    callback(new Error('原密码与新密码一致'));
  } else if (!pwdRegex.test(value)) {
    callback(new Error('密码复杂度太低（需包含字母和数字）'));
  } else {
    if (passwordForm.newPassword2) {
      passwordFormRef.value?.validateField('newPassword2');
    }
    callback();
  }
};

const validateConfirm = (_rule: any, value: string, callback: Function) => {
  if (!value) {
    callback(new Error('请再次输入密码'));
  } else if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入密码不一致'));
  } else {
    callback();
  }
};

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ validator: validateNewPass, trigger: 'blur' }],
  newPassword2: [{ validator: validateConfirm, trigger: 'blur' }],
};

/* ===================== Router ===================== */
const router = useRouter();
function goMessageCenter() {
  router.push({ path: '/messageCenter' });
}

/* ===================== API ===================== */
async function fetchUserInfo() {
  try {
    const res = await api.GetUserInfo();
    const data = res?.data || {};
    form.avatar = data.avatar || '';
    form.username = data.username || '';
    form.name = data.name || '';
    form.email = data.email || '';
    form.mobile = data.mobile || '';
    form.gender = data.gender ?? null;
    form.dept = data.dept_info || null;
    form.dept_name = data.dept_info?.dept_name || '';
    form.roles = data.role_info || [];
  } catch (e) {
    console.warn('Failed to fetch user info', e);
  }
}

async function onUpdateInfo() {
  if (!infoFormRef.value) return;
  try {
    await infoFormRef.value.validate();
  } catch {
    return;
  }
  try {
    const res = await api.updateUserInfo({
      avatar: form.avatar, name: form.name,
      email: form.email, mobile: form.mobile, gender: form.gender,
    });
    if (res?.code === 2000) {
      ElMessage.success('更新成功');
      fetchUserInfo();
    } else {
      ElMessage.error(res?.msg || '更新失败');
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '更新失败');
  }
}

async function fetchMessages() {
  try {
    const res = await api.GetSelfReceive({ limit: 5 });
    const data = res?.data;
    newsList.value = Array.isArray(data) ? data : data?.records ?? data?.rows ?? [];
  } catch (e) {
    console.warn('Failed to fetch messages', e);
  }
}

async function onChangePassword() {
  if (!passwordFormRef.value) return;
  try {
    await passwordFormRef.value.validate();
  } catch {
    return;
  }
  passwordLoading.value = true;
  try {
    const res = await api.UpdatePassword({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword,
      newPassword2: passwordForm.newPassword2,
    });
    if (res?.code === 2000) {
      ElMessage.success('密码修改成功');
      passwordDialogVisible.value = false;
      passwordForm.oldPassword = '';
      passwordForm.newPassword = '';
      passwordForm.newPassword2 = '';
    } else {
      ElMessage.error(res?.msg || '密码修改失败');
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '密码修改失败');
  } finally {
    passwordLoading.value = false;
  }
}

async function onUploadAvatar(data: any) {
  const fd = new FormData();
  fd.append('file', data);
  try {
    const res = await api.uploadAvatar(fd);
    if (res?.code === 2000) {
      selectImgVisible.value = false;
      form.avatar = getBaseURL() + res.data.url;
      await api.updateUserInfo({ avatar: form.avatar });
      successMessage('更新成功');
      fetchUserInfo();
      useUserInfo().updateUserInfos();
      avatarSelectorRef.value?.updateAvatar(form.avatar);
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '头像上传失败');
  }
}

/* ===================== Helpers ===================== */
function formatShortTime(dateStr: string | undefined | null): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins}分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}小时前`;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${m}-${day}`;
  } catch {
    return dateStr;
  }
}

/* ===================== Init ===================== */
onMounted(() => {
  genderOptions.value = dictionary('gender');
  fetchUserInfo();
  fetchMessages();
});
</script>

<style scoped lang="scss">
@import '/@/theme/mixins/index.scss';

// ============================================================
// OPSflow design tokens (inline for independence)
// ============================================================
$of-radius-card: 10px;
$of-shadow-card: 0 1px 4px rgba(0, 0, 0, 0.06);
$of-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.06);

// ============================================================
// Animations (inline so no external import needed)
// ============================================================
.of-fade-in-up {
  animation: ofFadeInUp 0.5s ease both;
}
.of-stagger-item {
  animation: ofFadeInUp 0.4s ease both;
}
@keyframes ofFadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes logoAnimation {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

// ============================================================
// Page
// ============================================================
.personal-page {
  width: 100%;
}

// ============================================================
// Hero Banner
// ============================================================
.personal-hero {
  background: linear-gradient(135deg, #ecf5ff 0%, #f8f9fb 100%);
  border: 1px solid #f0f0f0;
  border-radius: $of-radius-card;
  padding: 24px;
  margin-bottom: 18px;
  box-shadow: $of-shadow-card;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: $of-shadow-hover;
  }
}

.personal-hero-content {
  display: flex;
  align-items: center;
  gap: 24px;
}

.personal-hero-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  :deep(.el-upload) {
    height: 100%;
  }
}

.personal-hero-info {
  flex: 1;
  min-width: 0;
}

.personal-hero-greeting {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 4px;
}

.personal-hero-quote {
  font-size: 13px;
  color: #909399;
  margin: 0 0 10px;
}

.personal-hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

// ============================================================
// Section Card
// ============================================================
.personal-section {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }
}

.personal-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 12px;
}

.personal-section-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.personal-msg-more {
  margin-left: auto;
}

// ============================================================
// Form
// ============================================================
.personal-form {
  margin-top: 4px;
}

// ============================================================
// Security Items
// ============================================================
.personal-safe-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  &:hover {
    transform: translateX(3px);
  }

  &.of-hover-shift {
    cursor: pointer;

    &:hover {
      transform: translateX(3px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
  }
}

.personal-safe-item-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.personal-safe-item-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.personal-safe-item-info {
  flex: 1;
  min-width: 0;
}

.personal-safe-item-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.personal-safe-item-desc {
  font-size: 12px;
  color: #909399;

  .text-strong {
    color: #67c23a;
    font-weight: 600;
  }
}

// ============================================================
// Messages Section
// ============================================================
.personal-msg-section {
  height: fit-content;
}

.personal-msg-list {
  max-height: 360px;
  overflow-y: auto;
}

.personal-msg-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    .personal-msg-title { color: #409eff; }
  }
}

.personal-msg-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
  margin-top: 6px;
}

.personal-msg-content {
  flex: 1;
  min-width: 0;
}

.personal-msg-title {
  font-size: 13px;
  color: #303133;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}

.personal-msg-meta {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 3px;
}

// ============================================================
// Responsive
// ============================================================
@media screen and (max-width: 768px) {
  .personal-hero-content {
    flex-direction: column;
    text-align: center;
  }
  .personal-hero-tags {
    justify-content: center;
  }
}
</style>
