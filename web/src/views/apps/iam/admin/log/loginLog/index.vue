<template>
  <div class="login-log-page">
    <!-- Stats cards / 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">{{ $t('message.loginLogPage.totalLogs') }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.unique_ips }}</div>
        <div class="stat-label">{{ $t('message.loginLogPage.uniqueIps') }}</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.today_count }}</div>
        <div class="stat-label">{{ $t('message.loginLogPage.todayLogs') }}</div>
      </el-card>
    </div>

    <!-- Search bar / 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="queryParams" inline>
        <el-form-item :label="$t('message.loginLogPage.username')">
          <el-input v-model="queryParams.username" :placeholder="$t('message.loginLogPage.usernamePlaceholder')" clearable size="default" />
        </el-form-item>
        <el-form-item :label="$t('message.loginLogPage.ip')">
          <el-input v-model="queryParams.ip" :placeholder="$t('message.loginLogPage.ipPlaceholder')" clearable size="default" />
        </el-form-item>
        <el-form-item :label="$t('message.loginLogPage.loginType')">
          <el-select v-model="queryParams.login_type" :placeholder="$t('message.loginLogPage.loginTypePlaceholder')" clearable size="default">
            <el-option label="普通登录" :value="1" />
            <el-option label="微信扫码登录" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">{{ $t('message.loginLogPage.search') }}</el-button>
          <el-button @click="handleReset">{{ $t('message.loginLogPage.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table / 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column type="index" :label="$t('message.loginLogPage.colIndex')" width="70" align="center" />
        <el-table-column prop="username" label="登录{{ $t('message.loginLogPage.username') }}" min-width="120" show-overflow-tooltip />
        <el-table-column prop="ip" :label="$t('message.loginLogPage.ip')" min-width="130" show-overflow-tooltip />
        <el-table-column prop="login_type" :label="$t('message.loginLogPage.colLoginType')" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.login_type === 1 ? 'primary' : 'success'" size="small" effect="plain">
              {{ row.login_type === 1 ? t('message.loginLogPage.normalLogin') : t('message.loginLogPage.wechatLogin') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os" :label="$t('message.loginLogPage.colOs')" min-width="120" show-overflow-tooltip />
        <el-table-column prop="browser" :label="$t('message.loginLogPage.colBrowser')" min-width="120" show-overflow-tooltip />
        <el-table-column prop="create_datetime" :label="$t('message.loginLogPage.colTime')" min-width="170" show-overflow-tooltip />
        <el-table-column :label="$t('message.loginLogPage.colActions')" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button text size="small" @click="handleView(row)">{{ $t('message.loginLogPage.view') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:currentPage="queryParams.page"
          v-model:pageSize="queryParams.limit"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @update:pageSize="fetchData"
          @update:currentPage="fetchData"
        />
      </div>
    </el-card>

    <!-- Detail drawer / 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="$t('message.loginLogPage.detailTitle')"
      size="500px"
      class="opsflow-dialog"
    >
      <template v-if="currentRow">
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="$t('message.loginLogPage.username')">{{ currentRow.username || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.ip')">{{ currentRow.ip || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.loginType')">
            <el-tag :type="currentRow.login_type === 1 ? 'primary' : 'success'" size="small" effect="plain">
              {{ currentRow.login_type === 1 ? t('message.loginLogPage.normalLogin') : t('message.loginLogPage.wechatLogin') }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.colOs')">{{ currentRow.os || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.colBrowser')">{{ currentRow.browser || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.isp')">{{ currentRow.isp || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.continent')">{{ currentRow.continent || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.country')">{{ currentRow.country || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.province')">{{ currentRow.province || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.city')">{{ currentRow.city || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.district')">{{ currentRow.district || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.areaCode')">{{ currentRow.area_code || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.countryEn')">{{ currentRow.country_english || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.countryCode')">{{ currentRow.country_code || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.longitude')">{{ currentRow.longitude || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.latitude')">{{ currentRow.latitude || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.agent')">{{ currentRow.agent || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('message.loginLogPage.loginTime')">{{ currentRow.create_datetime || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { GetList, GetStats } from './api';

interface LoginLogRecord {
  id: number;
  username: string;
  ip: string;
  login_type: number;
  os: string;
  browser: string;
  isp: string;
  continent: string;
  country: string;
  province: string;
  city: string;
  district: string;
  area_code: string;
  country_english: string;
  country_code: string;
  longitude: string;
  latitude: string;
  agent: string;
  create_datetime: string;
  [key: string]: any;
}

interface StatsData {
  total: number;
  unique_ips: number;
  today_count: number;
}

// State / 状态
const { t } = useI18n();

const loading = ref(false);
const tableData = ref<LoginLogRecord[]>([]);
const total = ref(0);
const drawerVisible = ref(false);
const currentRow = ref<LoginLogRecord | null>(null);

const stats = reactive<StatsData>({
  total: 0,
  unique_ips: 0,
  today_count: 0,
});

const queryParams = reactive({
  page: 1,
  limit: 20,
  username: '',
  ip: '',
  login_type: undefined as number | undefined,
});

// Fetch table data / 获取表格数据
async function fetchData() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: queryParams.page,
      limit: queryParams.limit,
    };
    if (queryParams.username) params.username = queryParams.username;
    if (queryParams.ip) params.ip = queryParams.ip;
    if (queryParams.login_type !== undefined && queryParams.login_type !== null) {
      params.login_type = queryParams.login_type;
    }
    const res = await GetList(params);
    tableData.value = res.data || [];
    total.value = res.total || 0;
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.response?.data?.msg || t('message.loginLogPage.fetchFailed'));
    tableData.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

// Fetch stats / 获取统计数据
async function fetchStats() {
  try {
    const res = await GetStats();
    if (res.data) {
      stats.total = res.data.total ?? 0;
      stats.unique_ips = res.data.unique_ips ?? 0;
      stats.today_count = res.data.today_count ?? 0;
    }
  } catch {
    // Stats are non-critical; keep defaults / 统计数据非关键，保持默认值
  }
}

// Search / 搜索
function handleSearch() {
  queryParams.page = 1;
  fetchData();
}

// Reset / 重置
function handleReset() {
  queryParams.page = 1;
  queryParams.username = '';
  queryParams.ip = '';
  queryParams.login_type = undefined;
  fetchData();
}

// View detail / 查看详情
function handleView(row: LoginLogRecord) {
  currentRow.value = row;
  drawerVisible.value = true;
}

onMounted(() => {
  fetchData();
  fetchStats();
});
</script>

<style lang="scss" scoped>
.login-log-page {
  padding: 16px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  border-radius: 8px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #409EFF;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.search-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.table-card {
  border-radius: 8px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0 0;
}

.opsflow-dialog {
  :deep(.el-descriptions__label) {
    width: 140px;
    font-weight: 500;
    color: #606266;
  }
  :deep(.el-descriptions__content) {
    color: #303133;
  }
}
</style>
