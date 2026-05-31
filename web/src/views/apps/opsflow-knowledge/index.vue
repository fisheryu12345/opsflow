<template>
  <div class="opsflow-knowledge-page">
    <div class="knowledge-page-body">
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input v-model="searchQuery" placeholder="Search title/content..." clearable style="width: 260px"
                    @keyup.enter="onSearch" @clear="onSearch" />
          <el-select v-model="filterSource" placeholder="Source" clearable filterable style="width: 140px"
                     @change="onSearch">
            <el-option label="Runbook" value="runbook" />
            <el-option label="Incident" value="incident" />
            <el-option label="Doc" value="doc" />
          </el-select>
          <el-button :icon="Search" @click="onSearch">Search</el-button>
          <el-button :icon="Refresh" @click="fetchData" :loading="loading">Refresh</el-button>
        </div>
        <el-button type="primary" :icon="Plus" @click="openCreate">New Entry</el-button>
        <span v-if="useMock" class="mock-badge">Mock Data</span>
      </div>

      <!-- Card list -->
      <div class="card-list" v-loading="loading">
        <el-empty v-if="!loading && list.length === 0" :description="emptyText" />
        <el-card v-for="item in list" :key="item.id" class="knowledge-card" shadow="hover"
                 @click="openView(item)">
          <div class="card-header">
            <span class="card-title">{{ item.title }}</span>
            <el-tag :type="sourceTagType(item.source)" size="small" effect="plain">{{ item.source }}</el-tag>
          </div>
          <div class="card-tags" v-if="item.tags?.length">
            <el-tag v-for="t in item.tags" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
          </div>
          <p class="card-preview">{{ previewText(item.content) }}</p>
          <div class="card-footer">
            <span class="card-time">{{ item.created_at }}</span>
            <span class="card-actions">
              <el-button size="small" type="primary" link @click.stop="openEdit(item)">
                <el-icon style="margin-right: 3px"><Edit /></el-icon>Edit
              </el-button>
              <el-button size="small" type="danger" link @click.stop="handleDelete(item)">
                <el-icon style="margin-right: 3px"><Delete /></el-icon>Delete
              </el-button>
            </span>
          </div>
        </el-card>
      </div>

      <!-- Pagination -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                       layout="prev, pager, next, total" @current-change="onPageChange" />
      </div>
    </div>

    <!-- Create / Edit dialog -->
    <el-dialog v-model="formVisible" :title="isEditing ? 'Edit Entry' : 'New Entry'" width="640px" top="5vh">
      <el-form label-width="80px">
        <el-form-item label="Title" required>
          <el-input v-model="form.title" placeholder="Entry title" />
        </el-form-item>
        <el-form-item label="Content" required>
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="Content..." />
        </el-form-item>
        <el-form-item label="Tags">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option
                     placeholder="Add tags..." style="width: 100%">
            <el-option v-for="t in ['ansible', 'network', 'security', 'backup', 'deploy', 'monitor']"
                       :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="Source">
          <el-select v-model="form.source" placeholder="Source">
            <el-option label="Runbook" value="runbook" />
            <el-option label="Incident" value="incident" />
            <el-option label="Doc" value="doc" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- View dialog -->
    <el-dialog v-model="viewVisible" title="Entry Detail" width="720px" top="5vh">
      <template v-if="viewRow">
        <div class="view-header">
          <h2 class="view-title">{{ viewRow.title }}</h2>
          <el-tag :type="sourceTagType(viewRow.source)" size="small">{{ viewRow.source }}</el-tag>
        </div>
        <div class="view-tags" v-if="viewRow.tags?.length">
          <el-tag v-for="t in viewRow.tags" :key="t" size="small" type="info">{{ t }}</el-tag>
        </div>
        <div class="view-content">{{ viewRow.content }}</div>
        <div class="view-footer">{{ viewRow.created_at }}</div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Refresh, Plus, Search, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetKnowledgeList, CreateKnowledge, UpdateKnowledge, DeleteKnowledge, SearchKnowledge } from '/@/api/opsflow/knowledge'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchQuery = ref('')
const filterSource = ref('')
const useMock = ref(false)

const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', content: '', tags: [] as string[], source: 'doc' })

const viewVisible = ref(false)
const viewRow = ref<any>(null)

const emptyText = computed(() => useMock.value ? 'No data' : 'No entries yet. Create one to get started.')

const mockData = computed<any[]>(() => [
  { id: 1, title: 'Nginx 常见故障排查', content: 'Nginx 启动失败的常见原因：\n1. 端口被占用（netstat -tlnp | grep 80）\n2. 配置文件语法错误（nginx -t）\n3. SELinux 阻止（setenforce 0 测试）\n\n排查步骤：\n- 检查 systemctl status nginx\n- 查看 /var/log/nginx/error.log\n- 验证 upstream 后端是否存活', tags: ['nginx', 'web', 'troubleshooting'], source: 'runbook', created_at: '2026-05-28 14:30:00' },
  { id: 2, title: '磁盘空间告警处理', content: '磁盘使用率超过 90% 时的标准处理流程：\n1. 定位大文件: du -sh /* | sort -rh | head -10\n2. 清理日志: journalctl --vacuum-size=500M\n3. 清理 Docker: docker system prune -af\n4. 扩容云盘（如上述无法解决）', tags: ['disk', 'monitor', 'ops'], source: 'runbook', created_at: '2026-05-27 09:15:00' },
  { id: 3, title: '数据库连接池耗尽', content: 'MySQL 连接数飙高至 max_connections 时的应急方案：\n1. 立即查看连接: SHOW PROCESSLIST;\n2. Kill 空闲连接: SELECT CONCAT(\'KILL \', id, \';\') FROM information_schema.PROCESSLIST WHERE COMMAND=\'Sleep\' AND TIME>300;\n3. 临时调大连接池: SET GLOBAL max_connections=500;\n4. 排查代码层连接泄漏', tags: ['mysql', 'database', 'incident'], source: 'incident', created_at: '2026-05-25 16:42:00' },
  { id: 4, title: 'K8s Node NotReady 处理', content: 'K8s 节点 NotReady 的排查步骤：\nkubectl get nodes\nkubectl describe node <name>\n# 检查 kubelet 状态\nssh <node> systemctl status kubelet\n# 查看 kubelet 日志\njournalctl -u kubelet -n 100 --no-pager\n# 重启 kubelet\nsystemctl restart kubelet', tags: ['k8s', 'container', 'troubleshooting'], source: 'runbook', created_at: '2026-05-24 11:00:00' },
  { id: 5, title: 'Redis 内存使用优化', content: 'Redis 内存优化最佳实践：\n1. 设置 maxmemory 和淘汰策略\n2. 使用压缩数据结构（ziplist、intset）\n3. 大 Key 拆分（单个 Key 不超过 10MB）\n4. 定期执行 MEMORY PURGE\n5. 监控 INFO memory 中的 RSS 与 used_memory 比值', tags: ['redis', 'cache', 'optimization'], source: 'doc', created_at: '2026-05-22 08:30:00' },
  { id: 6, title: 'SSL 证书到期紧急替换', content: 'SSL 证书即将到期时的处理流程：\n1. 生成新证书或从 CA 下载\n2. 上传到服务器 /etc/ssl/certs/\n3. 更新 Nginx/Traefik 配置\n4. 重载: nginx -s reload\n5. 验证: openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | openssl x509 -noout -dates', tags: ['ssl', 'security', 'certificate'], source: 'runbook', created_at: '2026-05-20 15:20:00' },
  { id: 7, title: '跨机房网络延迟故障', content: '机房 A 到机房 B 网络延迟从 2ms 飙升至 200ms 的排查过程：\n发现是某条光缆被施工挖断，流量切换到备份链路导致延迟增加。\n\n处理：\n1. 确认备份链路带宽充足\n2. 通知施工方修复光缆\n3. 修复后切回主链路', tags: ['network', 'incident'], source: 'incident', created_at: '2026-05-18 22:10:00' },
  { id: 8, title: 'Ansible Tower 使用指南', content: 'Ansible Tower 日常操作指南：\n1. Job Template 创建与配置\n2. 凭据管理（SSH Key / Vault 密码）\n3. 工作流模板设计\n4. 通知配置（邮件 / Webhook）\n5. 权限控制与审计', tags: ['ansible', 'tower', 'automation'], source: 'doc', created_at: '2026-05-15 10:00:00' },
])

function sourceTagType(src: string) {
  const map: Record<string, string> = { runbook: 'success', incident: 'danger', doc: 'primary' }
  return map[src] || 'info'
}

function previewText(content: string) {
  return content ? content.replace(/\n/g, ' ').substring(0, 200) + (content.length > 200 ? '...' : '') : ''
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (filterSource.value) params.source = filterSource.value
    const res = await GetKnowledgeList(params)
    const items = res.data?.results || res.data || res.results || []
    if (items.length > 0) {
      list.value = items
      total.value = res.data?.count || res.count || items.length
      useMock.value = false
    } else {
      fallbackMock()
    }
  } catch {
    fallbackMock()
  }
  loading.value = false
}

function fallbackMock() {
  let items = [...mockData.value]
  if (filterSource.value) items = items.filter(i => i.source === filterSource.value)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(i => i.title.toLowerCase().includes(q) || i.content.toLowerCase().includes(q))
  }
  list.value = items
  total.value = items.length
  useMock.value = true
}

async function onSearch() { page.value = 1; fetchData() }
function onPageChange() { fetchData() }

function resetForm() {
  form.title = ''
  form.content = ''
  form.tags = []
  form.source = 'doc'
  editingId.value = null
  isEditing.value = false
}

function openCreate() { resetForm(); formVisible.value = true }
function openEdit(row: any) {
  isEditing.value = true
  editingId.value = row.id
  form.title = row.title
  form.content = row.content
  form.tags = [...(row.tags || [])]
  form.source = row.source || 'doc'
  formVisible.value = true
}

async function handleSave() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('Title and content are required')
    return
  }
  saving.value = true
  try {
    const data = { title: form.title, content: form.content, tags: form.tags, source: form.source }
    if (isEditing.value && editingId.value) {
      await UpdateKnowledge(editingId.value, data)
      ElMessage.success('Updated')
    } else {
      await CreateKnowledge(data)
      ElMessage.success('Created')
    }
    formVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Operation failed')
  }
  saving.value = false
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm('Delete this entry?', 'Confirm', { type: 'warning' })
    useMock.value ? fallbackMock() : await DeleteKnowledge(row.id)
    ElMessage.success('Deleted')
    await fetchData()
  } catch { /* cancelled */ }
}

function openView(row: any) { viewRow.value = row; viewVisible.value = true }

onMounted(fetchData)
</script>

<style scoped>
.opsflow-knowledge-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; background: #f0f2f5; overflow: hidden;
}
.knowledge-page-body {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
  margin: 8px; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.toolbar {
  display: flex; gap: 12px; align-items: center; padding: 12px 16px;
  background: #fff; border-bottom: 1px solid #ebeef5; flex-shrink: 0; flex-wrap: wrap;
}
.toolbar-left { display: flex; gap: 12px; align-items: center; flex: 1; }
.mock-badge {
  font-size: 11px; color: #E6A23C; background: #fdf6ec;
  padding: 2px 8px; border-radius: 4px; flex-shrink: 0;
}
.card-list {
  flex: 1; overflow-y: auto; padding: 16px;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px;
  align-content: start;
}
.knowledge-card { cursor: pointer; }
.knowledge-card:hover { border-color: #409EFF; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-title { font-size: 15px; font-weight: 600; color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 8px; }
.card-preview { font-size: 13px; color: #606266; margin: 8px 0 0; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
.card-time { font-size: 12px; color: #C0C4CC; }
.card-actions { display: flex; gap: 4px; }
.pagination-wrap {
  display: flex; justify-content: flex-end; padding: 12px 16px;
  background: #fff; flex-shrink: 0; border-top: 1px solid #ebeef5;
}
.view-header { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.view-title { margin: 0; font-size: 18px; color: #303133; }
.view-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.view-content { font-size: 14px; color: #303133; line-height: 1.7; white-space: pre-wrap; }
.view-footer { font-size: 12px; color: #C0C4CC; margin-top: 16px; }
</style>
