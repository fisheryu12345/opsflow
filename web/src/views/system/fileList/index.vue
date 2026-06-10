<template>
  <div class="filelist-page">
    <!-- Hero Section -->
    <div class="filelist-hero">
      <div class="filelist-hero-bg" />
      <div class="filelist-hero-inner">
        <div class="filelist-hero-left">
          <h1 class="filelist-hero-title">{{ $t('fileList.name') || '文件列表' }}</h1>
          <p class="filelist-hero-subtitle">File List</p>
        </div>
        <div class="filelist-hero-center">
          <el-input v-model="searchQuery" placeholder="Search file name..." clearable size="default"
            class="filelist-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="filelist-body">
      <div class="filelist-table-card">
        <el-table :data="list" v-loading="loading" stripe style="width:100%" size="small"
          :empty-text="loading ? 'Loading...' : '暂无数据'" row-key="id">
          <el-table-column label="#" width="70" align="center">
            <template #default="{ $index }">
              {{ (page - 1) * pageSize + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="文件名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="url" label="文件地址" min-width="260" show-overflow-tooltip />
          <el-table-column prop="md5sum" label="文件MD5" min-width="180" show-overflow-tooltip />
        </el-table>
        <div class="filelist-pagination" v-if="total > 0">
          <el-pagination v-model:currentPage="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @update:currentPage="onPageChange" size="small" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import type { FileRecord } from './api'
import { GetList } from './api'

const loading = ref(false)
const list = ref<FileRecord[]>([])
const page = ref(1)
const pageSize = ref(15)
const total = ref(0)
const searchQuery = ref('')

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, limit: pageSize.value }
    if (searchQuery.value.trim()) {
      params.name = searchQuery.value.trim()
    }
    const res = await GetList(params)
    // Response: { code: 2000, page: 1, limit: 15, total: N, data: [...], msg: "success" }
    list.value = res.data || []
    total.value = res.total || 0
  } catch (e: any) {
    console.error('Failed to fetch file list:', e)
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  fetchData()
}

function onPageChange(newPage: number) {
  page.value = newPage
  fetchData()
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
@use '../../../styles/opsflow-variables' as *;

.filelist-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: $of-bg-page;
  overflow: hidden;
}

/* ===== Hero ===== */
.filelist-hero {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  background: $of-gradient-hero;
}
.filelist-hero-bg {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  background-image:
    radial-gradient(circle at 20% 50%, $of-color-primary 1px, transparent 1px),
    radial-gradient(circle at 80% 30%, $of-color-accent 1px, transparent 1px);
  background-size: 40px 40px;
}
.filelist-hero-inner {
  position: relative;
  z-index: 1;
  padding: 14px 24px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
}
.filelist-hero-left {
  flex: 0 0 auto;
}
.filelist-hero-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: $of-text-primary;
  white-space: nowrap;
}
.filelist-hero-subtitle {
  margin: 0;
  font-size: 11px;
  color: $of-text-muted;
  white-space: nowrap;
}
.filelist-hero-center {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 360px;
}
.filelist-search-input {
  width: 100%;
}
.filelist-search-input :deep(.el-input__wrapper) {
  background: $of-bg-light-blue;
  border: 1px solid $of-border-blue;
  box-shadow: none;
  border-radius: 10px;
  padding: 2px 12px;
}
.filelist-search-input :deep(.el-input__inner) {
  color: $of-text-primary;
  font-size: 14px;
}
.filelist-search-input :deep(.el-input__inner::placeholder) {
  color: $of-text-placeholder;
}
.filelist-search-input :deep(.el-input__prefix-inner) {
  color: $of-text-muted;
}

/* ===== Body ===== */
.filelist-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 24px;
}

/* ===== Table Card ===== */
.filelist-table-card {
  background: #fff;
  border-radius: $of-radius-card;
  box-shadow: $of-shadow-card;
  overflow: hidden;
}
.filelist-table-card :deep(.el-table th.el-table__cell) {
  background: $of-bg-header;
  color: $of-text-secondary;
  font-weight: 600;
  font-size: 12px;
}
.filelist-table-card :deep(.el-table__body tr:hover td) {
  background: $of-bg-card-hover;
}
.filelist-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
}
</style>
