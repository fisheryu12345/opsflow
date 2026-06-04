<template>
  <div class="msg-page">
    <!-- ===== Stats Cards ===== -->
    <div class="msg-stats-row">
      <div
        v-for="card in statCards"
        :key="card.label"
        class="msg-stat-card"
      >
        <div class="msg-stat-icon" :style="{ background: card.bg }">
          <el-icon :size="22">
            <component :is="card.icon" />
          </el-icon>
        </div>
        <div class="msg-stat-body">
          <div class="msg-stat-value">{{ card.value }}</div>
          <div class="msg-stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- ===== Main Card ===== -->
    <div class="msg-main-card">
      <!-- Tab Bar -->
      <div class="msg-tab-bar">
        <el-tabs v-model="tabActive" @tab-click="onTabClick">
          <el-tab-pane name="send">
            <template #label>
              <span class="tab-label">
                <el-icon><Promotion /></el-icon>
                <span class="tab-text">我的发布</span>
                <el-tag
                  v-if="sendCount > 0"
                  size="small"
                  round
                  type="info"
                  class="tab-count"
                >{{ sendCount > 99 ? '99+' : sendCount }}</el-tag>
              </span>
            </template>
          </el-tab-pane>
          <el-tab-pane name="receive">
            <template #label>
              <span class="tab-label">
                <el-icon><Message /></el-icon>
                <span class="tab-text">我的接收</span>
                <el-badge
                  v-if="unreadCount > 0"
                  :value="unreadCount > 99 ? '99+' : unreadCount"
                  :max="99"
                  class="tab-badge"
                />
                <el-tag
                  v-else-if="receiveCount > 0"
                  size="small"
                  round
                  type="info"
                  class="tab-count"
                >{{ receiveCount > 99 ? '99+' : receiveCount }}</el-tag>
              </span>
            </template>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Toolbar: Search + Actions -->
      <div class="msg-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchText"
            placeholder="搜索消息标题..."
            clearable
            style="width:260px"
            size="default"
            @keyup.enter="onSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button @click="onSearch" type="primary">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-button
            v-if="tabActive === 'send' && auth('messageCenter:Create')"
            type="primary"
            @click="openAddDialog"
          >
            <el-icon><Plus /></el-icon> 发布消息
          </el-button>
        </div>
      </div>

      <!-- Loading -->
      <div v-loading="loading" class="msg-table-wrap">
        <!-- Table -->
        <el-table
          :data="tableData"
          style="width:100%"
          border
          :header-cell-style="{ background: '#fafbfc', color: '#606266', fontWeight: 600 }"
          row-key="id"
          :row-class-name="tableRowClassName"
          @row-click="onRowClick"
        >
          <el-table-column label="消息" min-width="360">
            <template #default="{ row }">
              <div class="msg-cell-main">
                <div class="msg-cell-top">
                  <span v-if="isReceiveTab && !row.is_read" class="msg-unread-dot" />
                  <span v-else-if="isReceiveTab && row.is_read" class="msg-read-dot" />
                  <span
                    class="msg-cell-title"
                    :class="{ 'is-unread': isReceiveTab && !row.is_read }"
                    @click.stop="openDetailDrawer(row)"
                  >{{ row.title || '无标题' }}</span>
                  <span class="msg-cell-time">{{ formatTime(row.create_datetime) }}</span>
                </div>
                <div class="msg-cell-preview">
                  {{ stripHtml(row.content).substring(0, 100) }}{{ (row.content || '').length > 100 ? '...' : '' }}
                </div>
                <div class="msg-cell-meta">
                  <template v-if="isReceiveTab">
                    <span v-if="row.creator_name || row.creator?.name" class="msg-cell-sender">
                      <el-icon><User /></el-icon> {{ row.creator_name || row.creator?.name }}
                    </span>
                  </template>
                  <span class="msg-target-tag" :class="`msg-target-tag--${targetTypeMap[row.target_type]?.type || 'info'}`">
                    {{ targetTypeMap[row.target_type]?.label || '未知' }}
                  </span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="类型" width="100" align="center">
            <template #default="{ row }">
              <span class="msg-target-tag" :class="`msg-target-tag--${targetTypeMap[row.target_type]?.type || 'info'}`">
                {{ targetTypeMap[row.target_type]?.label || '未知' }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center" v-if="isReceiveTab">
            <template #default="{ row }">
              <span class="msg-status-badge" :class="row.is_read ? 'is-read' : 'is-unread'">
                <span class="msg-status-dot" />
                {{ row.is_read ? '已读' : '未读' }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="时间" width="170" align="center">
            <template #default="{ row }">
              <span class="msg-cell-datetime">{{ formatTime(row.create_datetime) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="130" fixed="right" align="center">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click.stop="openDetailDrawer(row)">
                <el-icon><View /></el-icon> 查看
              </el-button>
              <el-button
                v-if="auth('messageCenter:Delete')"
                text
                type="danger"
                size="small"
                @click.stop="onDelete(row)"
              >
                <el-icon><Delete /></el-icon> 删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="msg-pagination">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @current-change="fetchData"
            @size-change="onSizeChange"
          />
        </div>
      </div>
    </div>

    <!-- ===== Detail Drawer ===== -->
    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="520px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
      class="msg-detail-drawer"
    >
      <template #header>
        <div class="msg-drawer-header">
          <div class="msg-drawer-title">{{ currentMsg.title || '消息详情' }}</div>
          <div class="msg-drawer-meta">
            <span v-if="currentMsg.creator_name || currentMsg.creator?.name" class="meta-item">
              <el-icon><User /></el-icon>
              {{ currentMsg.creator_name || currentMsg.creator?.name }}
            </span>
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ formatTime(currentMsg.create_datetime) }}
            </span>
            <el-tag :type="targetTypeTag(currentMsg.target_type)" size="small" effect="plain" round>
              {{ targetTypeMap[currentMsg.target_type]?.label || '未知' }}
            </el-tag>
          </div>
          <div v-if="isReceiveTab" class="msg-drawer-status">
            <span v-if="currentMsg.is_read" class="status-read">
              <el-icon><Select /></el-icon> 已读
            </span>
            <span v-else class="status-unread">
              <el-icon><CloseBold /></el-icon> 未读
            </span>
          </div>
        </div>
      </template>
      <div class="msg-drawer-body">
        <div v-if="currentMsg.content" class="msg-content-html" v-html="currentMsg.content" />
        <el-empty v-else :image-size="60" description="暂无内容" />
      </div>
    </el-drawer>

    <!-- ===== Add / Edit Dialog ===== -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑消息' : '发布消息'"
      width="720px"
      :close-on-click-modal="false"
      destroy-on-close
      class="opsflow-dialog"
      @closed="onDialogClosed"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="80px"
        label-position="left"
        size="default"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="formData.title" placeholder="请输入消息标题" maxlength="100" />
        </el-form-item>

        <el-form-item label="目标类型" prop="target_type">
          <el-radio-group v-model="formData.target_type">
            <el-radio-button :value="0">按用户</el-radio-button>
            <el-radio-button :value="1">按角色</el-radio-button>
            <el-radio-button :value="2">按部门</el-radio-button>
            <el-radio-button :value="3">通知公告</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 按用户 -->
        <el-form-item v-if="formData.target_type === 0" label="目标用户" prop="target_user">
          <TableSelector
            v-model="formData.target_user"
            :table-config="tableSelectorConfig.user"
            :display-label="displayUserLabel"
          />
        </el-form-item>

        <!-- 按角色 -->
        <el-form-item v-if="formData.target_type === 1" label="目标角色" prop="target_role">
          <TableSelector
            v-model="formData.target_role"
            :table-config="tableSelectorConfig.role"
            :display-label="displayRoleLabel"
          />
        </el-form-item>

        <!-- 按部门 -->
        <el-form-item v-if="formData.target_type === 2" label="目标部门" prop="target_dept">
          <TableSelector
            v-model="formData.target_dept"
            :table-config="tableSelectorConfig.dept"
            :display-label="displayDeptLabel"
          />
        </el-form-item>

        <el-form-item label="内容" prop="content">
          <EditorWang5 v-model="formData.content" style="width:100%" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="onSubmit">
          {{ isEdit ? '保存' : '发布' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup name="messageCenter">
import { ref, computed, onMounted, shallowRef } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Promotion, Message, User, Clock, Select, CloseBold,
  DataBoard, Tickets, View, Plus, Search, Delete,
} from '@element-plus/icons-vue';
import { auth } from '/@/utils/authFunction';
import * as api from './api';

/* ===================== Types ===================== */
interface MessageItem {
  id: number;
  title: string;
  content: string;
  target_type: number;
  is_read: boolean;
  create_datetime: string;
  creator_name?: string;
  creator?: { name: string };
  user_info?: any[];
  role_info?: any[];
  dept_info?: any[];
}

/* ===================== Tab ===================== */
const tabActive = ref('send');
const isReceiveTab = computed(() => tabActive.value === 'receive');

/* ===================== Table Data ===================== */
const tableData = ref<MessageItem[]>([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const searchText = ref('');

/* ===================== Stats ===================== */
const sendCount = ref(0);
const receiveCount = ref(0);
const unreadCount = ref(0);

const statCards = computed(() => {
  if (isReceiveTab.value) {
    return [
      { label: '接收总数', value: receiveCount.value, icon: Tickets, bg: '#409eff' },
      { label: '未读消息', value: unreadCount.value, icon: Message, bg: '#f56c6c' },
      { label: '已读消息', value: Math.max(0, receiveCount.value - unreadCount.value), icon: Select, bg: '#67c23a' },
      { label: '当前查询', value: '---', icon: DataBoard, bg: '#909399' },
    ];
  }
  return [
    { label: '发布总数', value: sendCount.value, icon: Promotion, bg: '#409eff' },
    { label: '消息类型', value: '3 种', icon: Tickets, bg: '#e6a23c' },
    { label: '通知公告', value: '---', icon: View, bg: '#67c23a' },
    { label: '当前查询', value: '---', icon: DataBoard, bg: '#909399' },
  ];
});

/* ===================== Fetch Data ===================== */
async function fetchData() {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      limit: pageSize.value,
      title: searchText.value || undefined,
    };

    let res: any;
    if (isReceiveTab.value) {
      res = await api.GetSelfReceive(params);
    } else {
      res = await api.GetList(params);
    }

    if (res?.code === 2000) {
      const d = res.data;
      // fast-crud paginated format: { records, total } or { rows, total }
      const records = d.records ?? d.rows ?? d ?? [];
      tableData.value = Array.isArray(records) ? records : [];
      total.value = d.total ?? tableData.value.length;

      // Update stat counts
      if (isReceiveTab.value) {
        receiveCount.value = total.value;
        unreadCount.value = tableData.value.filter(r => !r.is_read).length;
      } else {
        sendCount.value = total.value;
      }
    } else {
      tableData.value = [];
      total.value = 0;
    }
  } catch (e: any) {
    console.error('Failed to fetch messages', e);
    ElMessage.error(e?.msg || '获取消息列表失败');
    tableData.value = [];
  } finally {
    loading.value = false;
  }
}

/* ===================== Search ===================== */
function onSearch() {
  page.value = 1;
  fetchData();
}

/* ===================== Tab Switch ===================== */
function onTabClick() {
  page.value = 1;
  searchText.value = '';
  fetchData();
}

/* ===================== Pagination ===================== */
function onSizeChange(size: number) {
  pageSize.value = size;
  page.value = 1;
  fetchData();
}

/* ===================== Row Click / Mark Read ===================== */
function tableRowClassName({ row }: { row: MessageItem }) {
  if (isReceiveTab.value && !row.is_read) {
    return 'msg-row-unread';
  }
  return '';
}

function onRowClick(row: MessageItem) {
  // Clicking anywhere opens the detail drawer
  openDetailDrawer(row);
}

/* ===================== Detail Drawer ===================== */
const drawerVisible = ref(false);
const currentMsg = ref<any>({});

function openDetailDrawer(row: MessageItem) {
  currentMsg.value = { ...row };
  drawerVisible.value = true;

  // Mark as read (receive tab only)
  if (isReceiveTab.value && !row.is_read) {
    api.GetObj(row.id).then(() => {
      row.is_read = true;
      fetchData();
    }).catch(() => {});
  }
}

/* ===================== Delete ===================== */
function onDelete(row: MessageItem) {
  ElMessageBox.confirm(`确定删除消息「${row.title || '无标题'}」？`, '确认删除', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  }).then(async () => {
    try {
      const res = await api.DelObj(row.id);
      if (res?.code === 2000) {
        ElMessage.success('删除成功');
        fetchData();
      } else {
        ElMessage.error(res?.msg || '删除失败');
      }
    } catch (e: any) {
      ElMessage.error(e?.msg || '删除失败');
    }
  }).catch(() => {});
}

/* ===================== Add Dialog ===================== */
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const formRef = ref<any>(null);

// Lazy-load async components for dialog form
const TableSelector = shallowRef(null);
const EditorWang5 = shallowRef(null);

const displayUserLabel = ref('');
const displayRoleLabel = ref('');
const displayDeptLabel = ref('');

const tableSelectorConfig = {
  user: {
    url: '/api/system/user/',
    label: 'name',
    value: 'id',
    isMultiple: true,
    columns: [
      { prop: 'name', label: '用户名称', width: 120 },
      { prop: 'phone', label: '用户电话', width: 120 },
    ],
  },
  role: {
    url: '/api/system/role/',
    label: 'name',
    value: 'id',
    isMultiple: true,
    columns: [
      { prop: 'name', label: '角色名称' },
      { prop: 'key', label: '权限标识' },
    ],
  },
  dept: {
    url: '/api/system/dept/all_dept/',
    label: 'name',
    value: 'id',
    isTree: true,
    isMultiple: true,
    columns: [
      { prop: 'name', label: '部门名称' },
      { prop: 'status_label', label: '状态' },
      { prop: 'parent_name', label: '父级部门' },
    ],
  },
};

const formData = ref<any>({
  title: '',
  target_type: 0,
  target_user: [],
  target_role: [],
  target_dept: [],
  content: '',
});

const formRules = {
  title: [{ required: true, message: '请输入消息标题', trigger: 'blur' }],
  target_type: [{ required: true, message: '请选择目标类型', trigger: 'change' }],
};

async function openAddDialog() {
  // Lazy load components on first open
  if (!TableSelector.value) {
    const ts = await import('/@/components/tableSelector/index.vue');
    TableSelector.value = ts.default;
  }
  if (!EditorWang5.value) {
    const ew = await import('/@/components/editorWang5/index.vue');
    EditorWang5.value = ew.default;
  }

  isEdit.value = false;
  formData.value = { title: '', target_type: 0, target_user: [], target_role: [], target_dept: [], content: '' };
  dialogVisible.value = true;
}

/* async function openEditDialog(row: MessageItem) {
  isEdit.value = true;
  formData.value = {
    id: row.id,
    title: row.title,
    target_type: row.target_type,
    target_user: row.target_user ?? [],
    target_role: row.target_role ?? [],
    target_dept: row.target_dept ?? [],
    content: row.content,
  };
  dialogVisible.value = true;
} */

function onDialogClosed() {
  formRef.value?.resetFields();
}

async function onSubmit() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  submitLoading.value = true;
  try {
    const payload = { ...formData.value };
    let res: any;
    if (isEdit.value) {
      res = await api.UpdateObj(payload);
    } else {
      res = await api.AddObj(payload);
    }
    if (res?.code === 2000) {
      ElMessage.success(isEdit.value ? '保存成功' : '发布成功');
      dialogVisible.value = false;
      fetchData();
    } else {
      ElMessage.error(res?.msg || '操作失败');
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败');
  } finally {
    submitLoading.value = false;
  }
}

/* ===================== Helpers ===================== */
const targetTypeMap: Record<number, { label: string; type: string }> = {
  0: { label: '按用户', type: 'primary' },
  1: { label: '按角色', type: 'success' },
  2: { label: '按部门', type: 'warning' },
  3: { label: '通知公告', type: 'danger' },
};

function targetTypeTag(val: number): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  return (targetTypeMap[val]?.type as any) || 'info';
}

function formatTime(dateStr: string | undefined | null): string {
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
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}天前`;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${m}-${day}`;
  } catch {
    return dateStr;
  }
}

function stripHtml(html: string | undefined | null): string {
  if (!html) return '';
  const div = document.createElement('div');
  div.innerHTML = html;
  return div.textContent || div.innerText || '';
}

/* ===================== Init ===================== */
onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
@import '/@/theme/mixins/index.scss';

// ============================================================
// Stats Row
// ============================================================
.msg-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.msg-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  }
}

.msg-stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.msg-stat-body {
  flex: 1;
  min-width: 0;
}

.msg-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.msg-stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

// ============================================================
// Main Card
// ============================================================
.msg-main-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

// ============================================================
// Tab Bar
// ============================================================
.msg-tab-bar {
  padding: 0 20px;
  border-bottom: 1px solid var(--el-border-color-light, #ebeef5);
  background: #fafbfc;

  :deep(.el-tabs__header) {
    margin: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__item) {
    height: 48px;
    line-height: 48px;
    font-size: 14px;
    padding: 0 16px;
  }

  .tab-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .tab-text {
    margin: 0 2px;
  }

  .tab-count {
    margin-left: 2px;
  }

  :deep(.tab-badge .el-badge__content) {
    font-size: 11px;
    border-width: 1px;
  }
}

// ============================================================
// Toolbar
// ============================================================
.msg-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  gap: 12px;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

// ============================================================
// Table
// ============================================================
.msg-table-wrap {
  min-height: 200px;
}

// ============================================================
// Message Cell Styles
// ============================================================
.msg-cell-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 4px 0;
  cursor: default;
}

.msg-cell-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.msg-unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
  display: inline-block;
}

.msg-read-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: transparent;
  flex-shrink: 0;
  display: inline-block;
  border: 1px solid #dcdfe6;
}

.msg-cell-title {
  flex: 1;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.2s;

  &.is-unread {
    font-weight: 600;
    color: #1a1a1a;
  }

  &:hover {
    color: #409eff;
  }
}

.msg-cell-time {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
  flex-shrink: 0;
}

.msg-cell-preview {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 16px;
}

.msg-cell-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 16px;
}

.msg-cell-sender {
  font-size: 12px;
  color: #909399;
  display: inline-flex;
  align-items: center;
  gap: 3px;

  .el-icon {
    font-size: 12px;
  }
}

.msg-cell-datetime {
  font-size: 13px;
  color: #909399;
}

// ===== Target Type Tags =====
.msg-target-tag {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  padding: 0 8px;
  height: 20px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;

  &--primary {
    background: #ecf5ff;
    color: #409eff;
  }
  &--success {
    background: #f0f9eb;
    color: #67c23a;
  }
  &--warning {
    background: #fdf6ec;
    color: #e6a23c;
  }
  &--danger {
    background: #fef0f0;
    color: #f56c6c;
  }
  &--info {
    background: #f4f4f5;
    color: #909399;
  }
}

// ===== Read/Unread Status Badge =====
.msg-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 12px;

  &.is-read {
    background: #f0f9eb;
    color: #67c23a;
  }
  &.is-unread {
    background: #fef0f0;
    color: #f56c6c;
  }

  .msg-status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }

  &.is-read .msg-status-dot {
    background: #67c23a;
  }
  &.is-unread .msg-status-dot {
    background: #f56c6c;
  }
}

// ===== Table Row Unread Highlight =====
:deep(.msg-row-unread td.el-table__cell) {
  box-shadow: inset 3px 0 0 #409eff;
}

// ============================================================
// Pagination
// ============================================================
.msg-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--el-border-color-light, #ebeef5);
}

// ============================================================
// Detail Drawer
// ============================================================
.msg-detail-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 20px 24px 16px;
    border-bottom: 1px solid var(--el-border-color-light, #ebeef5);
  }

  :deep(.el-drawer__body) {
    padding: 24px;
  }
}

.msg-drawer-header {
  width: 100%;
}

.msg-drawer-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
  margin-bottom: 12px;
  word-break: break-word;
}

.msg-drawer-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #909399;

  .meta-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;

    .el-icon {
      font-size: 14px;
    }
  }
}

.msg-drawer-status {
  margin-top: 10px;
  font-size: 13px;

  .status-read {
    color: #67c23a;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .status-unread {
    color: #f56c6c;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
}

.msg-drawer-body {
  min-height: 200px;
}

.msg-content-html {
  line-height: 1.8;
  font-size: 14px;
  color: #303133;
  word-break: break-word;

  :deep(img) {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    margin: 8px 0;
  }

  :deep(table) {
    max-width: 100%;
    border-collapse: collapse;
    margin: 8px 0;

    td, th {
      border: 1px solid #e4e7ed;
      padding: 6px 10px;
    }
  }

  :deep(pre) {
    background: #f5f7fa;
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
  }

  :deep(blockquote) {
    border-left: 3px solid #409eff;
    margin: 8px 0;
    padding: 6px 12px;
    background: #f5f9ff;
    border-radius: 0 4px 4px 0;
  }
}

// ============================================================
// Responsive
// ============================================================
@media screen and (max-width: 768px) {
  .msg-stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .msg-stat-card {
    padding: 14px;
  }

  .msg-stat-value {
    font-size: 20px;
  }

  .msg-toolbar {
    flex-direction: column;
    align-items: stretch;

    .toolbar-left {
      flex-wrap: wrap;
    }
  }

  :deep(.msg-detail-drawer .el-drawer) {
    width: 100% !important;
  }
}
</style>
