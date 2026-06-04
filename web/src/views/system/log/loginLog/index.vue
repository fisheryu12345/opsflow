<template>
  <div class="login-log-page">
    <!-- Stats cards / 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">总日志数 / Total Logs</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.unique_ips }}</div>
        <div class="stat-label">独立IP数 / Unique IPs</div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ stats.today_count }}</div>
        <div class="stat-label">今日日志数 / Today's Logs</div>
      </el-card>
    </div>

    <!-- Search bar / 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="queryParams" inline>
        <el-form-item label="用户名 / Username">
          <el-input v-model="queryParams.username" placeholder="请输入用户名" clearable size="default" />
        </el-form-item>
        <el-form-item label="登录IP / IP">
          <el-input v-model="queryParams.ip" placeholder="请输入登录IP" clearable size="default" />
        </el-form-item>
        <el-form-item label="登录类型 / Login Type">
          <el-select v-model="queryParams.login_type" placeholder="请选择登录类型" clearable size="default">
            <el-option label="普通登录" :value="1" />
            <el-option label="微信扫码登录" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索 / Search</el-button>
          <el-button @click="handleReset">重置 / Reset</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table / 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column type="index" label="序号 / #" width="70" align="center" />
        <el-table-column prop="username" label="登录用户名 / Username" min-width="120" show-overflow-tooltip />
        <el-table-column prop="ip" label="登录IP / IP" min-width="130" show-overflow-tooltip />
        <el-table-column prop="login_type" label="登录类型 / Type" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.login_type === 1 ? 'primary' : 'success'" size="small" effect="plain">
              {{ row.login_type === 1 ? '普通登录' : '微信扫码' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os" label="操作系统 / OS" min-width="120" show-overflow-tooltip />
        <el-table-column prop="browser" label="浏览器 / Browser" min-width="120" show-overflow-tooltip />
        <el-table-column prop="create_datetime" label="登录时间 / Time" min-width="170" show-overflow-tooltip />
        <el-table-column label="操作 / Actions" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">查看 / View</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.limit"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- Detail drawer / 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="登录日志详情 / Login Log Detail"
      size="500px"
      class="opsflow-dialog"
    >
      <template v-if="currentRow">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名 / Username">{{ currentRow.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登录IP / IP">{{ currentRow.ip || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登录类型 / Login Type">
            <el-tag :type="currentRow.login_type === 1 ? 'primary' : 'success'" size="small" effect="plain">
              {{ currentRow.login_type === 1 ? '普通登录' : '微信扫码' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="操作系统 / OS">{{ currentRow.os || '-' }}</el-descriptions-item>
          <el-descriptions-item label="浏览器 / Browser">{{ currentRow.browser || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运营商 / ISP">{{ currentRow.isp || '-' }}</el-descriptions-item>
          <el-descriptions-item label="大洲 / Continent">{{ currentRow.continent || '-' }}</el-descriptions-item>
          <el-descriptions-item label="国家 / Country">{{ currentRow.country || '-' }}</el-descriptions-item>
          <el-descriptions-item label="省份 / Province">{{ currentRow.province || '-' }}</el-descriptions-item>
          <el-descriptions-item label="城市 / City">{{ currentRow.city || '-' }}</el-descriptions-item>
          <el-descriptions-item label="县区 / District">{{ currentRow.district || '-' }}</el-descriptions-item>
          <el-descriptions-item label="区域代码 / Area Code">{{ currentRow.area_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="英文全称 / Country EN">{{ currentRow.country_english || '-' }}</el-descriptions-item>
          <el-descriptions-item label="简称 / Country Code">{{ currentRow.country_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="经度 / Longitude">{{ currentRow.longitude || '-' }}</el-descriptions-item>
          <el-descriptions-item label="纬度 / Latitude">{{ currentRow.latitude || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Agent信息 / Agent">{{ currentRow.agent || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登录时间 / Login Time">{{ currentRow.create_datetime || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
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
    ElMessage.error(e?.msg || e?.response?.data?.msg || '获取登录日志列表失败');
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
