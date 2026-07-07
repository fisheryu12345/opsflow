<template>
  <div class="service-market">
    <!-- Search -->
    <div class="sm-search-bar">
      <Teleport v-if="active && searchEl" :to="searchEl">
        <el-input v-model="searchQuery" :placeholder="$t('message.serviceMarket.searchPlaceholder')" clearable size="default" class="sm-search-input" @input="onSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </Teleport>
      <div class="sm-filter-tags" v-if="activeMode">
        <el-tag closable size="small" @close="activeMode = ''">
          {{ activeMode === 'flow' ? $t('message.serviceMarket.flowMode') : $t('message.serviceMarket.lightweightMode') }}
        </el-tag>
      </div>
    </div>

    <div class="sm-layout">
      <!-- Left: Category Tree -->
      <div class="sm-sidebar">
        <div class="sm-sidebar-title">{{ $t('message.serviceMarket.categories') }}</div>
        <div class="sm-category-list">
          <div class="sm-cat-item" :class="{ active: activeCategory === '' }" @click="activeCategory = ''; loadItems()">
            <el-icon><FolderOpened /></el-icon> {{ $t('message.serviceMarket.allServices') }}
          </div>
          <template v-for="cat in categories" :key="cat.id">
            <div class="sm-cat-item" :class="{ active: activeCategory === cat.id }" @click="onCategoryClick(cat)">
              <el-icon><Folder /></el-icon> {{ cat.name }}
            </div>
            <div v-for="child in (cat.children || [])" :key="child.id"
              class="sm-cat-child" :class="{ active: activeCategory === child.id }"
              @click="activeCategory = child.id; loadItems()">
              {{ child.name }}
            </div>
          </template>
        </div>
      </div>

      <!-- Right: Service Cards -->
      <div class="sm-content">
        <div class="sm-content-header">
          <span class="sm-count">{{ $t('message.serviceMarket.serviceCount', { count: items.length }) }}</span>
          <div class="sm-mode-filter">
            <el-radio-group v-model="activeMode" size="small" @change="loadItems">
              <el-radio-button value="">{{ $t('message.serviceMarket.all') }}</el-radio-button>
              <el-radio-button value="flow">{{ $t('message.serviceMarket.flowMode') }}</el-radio-button>
              <el-radio-button value="lightweight">{{ $t('message.serviceMarket.lightweightMode') }}</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <el-row :gutter="16" v-loading="loading">
          <el-col v-for="item in items" :key="item.id" :xs="24" :sm="12" :md="8" :lg="6" class="sm-card-col">
            <div class="sm-card" @click="onViewDetail(item)">
              <div class="sm-card-icon">{{ item.icon || '📋' }}</div>
              <div class="sm-card-body">
                <div class="sm-card-name">{{ item.name }}</div>
                <div class="sm-card-desc" v-if="item.description">{{ item.description }}</div>
              </div>
              <div class="sm-card-footer">
                <el-tag :type="item.mode === 'flow' ? 'primary' : 'success'" size="small">
                  {{ item.mode === 'flow' ? $t('message.serviceMarket.flowMode') : $t('message.serviceMarket.lightweightMode') }}
                </el-tag>
                <span v-if="item.expected_duration" class="sm-duration">⏱ {{ item.expected_duration }}</span>
              </div>
            </div>
          </el-col>
          <el-col v-if="!items.length && !loading" :span="24">
            <el-empty :description="$t('message.serviceMarket.noServices')" :image-size="60" />
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- Loading overlay for detail navigation -->
    <div v-if="showDetail" class="sm-detail-overlay">
      <ServiceDetail :service-id="detailId" @back="showDetail = false" @submitted="onSubmitted" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, FolderOpened, Folder } from '@element-plus/icons-vue'
import { serviceItemApi, serviceCategoryApi } from '/@/api/itsm/index'
import ServiceDetail from './ServiceDetail.vue'

const emit = defineEmits<{ goTicket: [ticketId: number] }>()
const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { t } = useI18n()
const { searchEl, reportStats: updateHeroStats } = useHeroConsumer()
const loading = ref(false)
const items = ref<any[]>([])
const categories = ref<any[]>([])
const searchQuery = ref('')
const activeCategory = ref<string | number>('')
const activeMode = ref<string>('')
const showDetail = ref(false)
const detailId = ref<number>(0)

async function loadCategories() {
  try {
    const res = await serviceCategoryApi.list({ page_size: 1000 })
    const list = (res as any).results || (res as any).data || []
    // Build tree: parent=null → top level
    const top = list.filter((c: any) => !c.parent)
    categories.value = top.map((t: any) => ({
      ...t,
      children: list.filter((c: any) => c.parent === t.id),
    }))
  } catch { categories.value = [] }
}

async function loadItems() {
  loading.value = true
  try {
    const params: Record<string, any> = { is_active: true }
    if (activeCategory.value) params.category = activeCategory.value
    if (activeMode.value) params.mode = activeMode.value
    if (searchQuery.value) params.search = searchQuery.value
    const res = await serviceItemApi.list(params)
    items.value = (res as any).results || (res as any).data || []
  } catch { items.value = [] }
  finally { loading.value = false }
}

function onSearch() {
  // Debounced via @input
  loadItems()
}

function onCategoryClick(cat: any) {
  activeCategory.value = cat.id
  loadItems()
}

function onViewDetail(item: any) {
  detailId.value = item.id
  showDetail.value = true
}

function onSubmitted(ticketId: number) {
  showDetail.value = false
  emit('goTicket', ticketId)
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '服务总数' },
    { value: items.value.filter((it: any) => it.mode === 'flow').length, label: '流程模式' },
    { value: items.value.filter((it: any) => it.mode === 'lightweight').length, label: '轻量模式' },
  ])
}

onMounted(async () => {
  await loadCategories()
  await loadItems()
  if (props.active) reportStats()
})

// Re-report stats when this tab becomes active
watch(() => props.active, (isActive) => {
  if (isActive && items.value.length > 0) reportStats()
})
</script>

<style lang="scss" scoped>
.service-market {
  position: relative;
  min-height: 400px;
}

.sm-search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.sm-search-input { max-width: 400px; }
.sm-filter-tags { flex: 1; }

.sm-layout {
  display: flex;
  gap: 16px;
  min-height: 380px;
}

.sm-sidebar {
  width: 180px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.sm-sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
  padding-left: 4px;
}
.sm-category-list { display: flex; flex-direction: column; gap: 2px; }
.sm-cat-item, .sm-cat-child {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s;
  .el-icon { font-size: 16px; color: #909399; }
}
.sm-cat-item:hover, .sm-cat-child:hover { background: #f5f7fa; color: #409EFF; }
.sm-cat-item.active, .sm-cat-child.active { background: #ecf5ff; color: #409EFF; font-weight: 500; }
.sm-cat-child { padding-left: 28px; font-size: 12px; }

.sm-content { flex: 1; min-width: 0; }
.sm-content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.sm-count { font-size: 13px; color: #909399; }

.sm-card-col { margin-bottom: 14px; }
.sm-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
  &:hover {
    border-color: #409EFF;
    box-shadow: 0 2px 12px rgba(64,158,255,0.1);
    transform: translateY(-2px);
  }
}
.sm-card-icon { font-size: 28px; margin-bottom: 8px; }
.sm-card-body { flex: 1; }
.sm-card-name { font-weight: 600; font-size: 15px; color: #303133; margin-bottom: 4px; }
.sm-card-desc { font-size: 12px; color: #909399; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.sm-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
.sm-duration { font-size: 11px; color: #c0c4cc; }

.sm-detail-overlay {
  position: fixed;
  inset: 0;
  background: #f5f6fa;
  z-index: 1000;
  overflow-y: auto;
  padding: 16px 20px;
}

</style>
