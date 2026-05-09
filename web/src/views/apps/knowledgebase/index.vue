<template>
  <div class="trading-page">
    <PageHeader title="知识库" />

    <div class="kb-layout">
      <!-- Sidebar -->
      <div class="kb-sidebar">
        <div class="kb-sidebar-header">
          <el-input v-model="searchText" placeholder="搜索文档..." clearable size="small" />
        </div>
        <div class="kb-tree-wrap">
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="treeProps"
            node-key="path"
            highlight-current
            default-expand-all
            :filter-node-method="filterNode"
            @node-click="onNodeClick"
          >
            <template #default="{ node, data }">
              <span class="kb-tree-node">
                <el-icon v-if="data.is_dir" size="14" style="margin-right: 4px;">
                  <FolderOpened />
                </el-icon>
                <el-icon v-else size="14" style="margin-right: 4px; color: #1890ff;">
                  <Document />
                </el-icon>
                <span class="kb-tree-label">{{ data.label }}</span>
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- Content -->
      <div class="kb-content">
        <div v-if="loadingContent" class="kb-loading">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <span style="margin-left: 8px;">加载中...</span>
        </div>
        <div v-else-if="!currentFile" class="kb-empty">
          <el-empty description="请从左侧选择一篇文档" />
        </div>
        <div v-else class="kb-markdown" v-html="renderedContent" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { ElTree } from 'element-plus'
import { FolderOpened, Document, Loading } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import PageHeader from '/@/views/apps/components/PageHeader.vue'
import { GetTree, GetContent, type TreeNode } from './api'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

const treeRef = ref<InstanceType<typeof ElTree>>()
const treeData = ref<TreeNode[]>([])
const treeProps = { children: 'children', label: 'label' }
const searchText = ref('')
const currentFile = ref<string | null>(null)
const loadingContent = ref(false)
const renderedContent = ref('')

watch(searchText, (val) => {
  treeRef.value?.filter(val)
})

function filterNode(value: string, data: TreeNode): boolean {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

async function loadTree() {
  try {
    const res = await GetTree()
    if (res.data?.code === 2000) {
      treeData.value = res.data.data || []
    }
  } catch (e) {
    console.error('Failed to load knowledge base tree:', e)
  }
}

async function onNodeClick(data: TreeNode) {
  if (data.is_dir) return
  loadingContent.value = true
  currentFile.value = data.path
  renderedContent.value = ''
  try {
    const res = await GetContent(data.path)
    if (res.data?.code === 2000) {
      const content = res.data.data.content
      renderedContent.value = md.render(content)
      await nextTick()
      // scroll to top when content changes
      document.querySelector('.kb-content')?.scrollTo(0, 0)
    }
  } catch (e) {
    console.error('Failed to load content:', e)
    renderedContent.value = '<p style="color:red">加载失败</p>'
  } finally {
    loadingContent.value = false
  }
}

onMounted(() => {
  loadTree()
})
</script>

<style scoped>
.kb-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  min-height: calc(100vh - 200px);
}

.kb-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.kb-sidebar-header {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.kb-tree-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.kb-tree-node {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.kb-tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-content {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 32px 40px;
  min-height: calc(100vh - 200px);
  overflow-y: auto;
}

.kb-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #999;
}

.kb-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

/* Markdown content styling */
.kb-markdown :deep(h1) {
  font-size: 24px;
  border-bottom: 2px solid #1a1a2e;
  padding-bottom: 8px;
  margin-bottom: 20px;
  margin-top: 0;
}

.kb-markdown :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid #e8e8e8;
  padding-bottom: 6px;
  margin: 28px 0 16px;
}

.kb-markdown :deep(h3) {
  font-size: 16px;
  margin: 24px 0 12px;
}

.kb-markdown :deep(h4) {
  font-size: 14px;
  margin: 20px 0 10px;
}

.kb-markdown :deep(p) {
  line-height: 1.8;
  margin: 12px 0;
  color: #333;
}

.kb-markdown :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
  color: #d93025;
  font-family: 'Fira Code', 'Consolas', monospace;
}

.kb-markdown :deep(pre) {
  background: #f6f8fa;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  border: 1px solid #e8e8e8;
}

.kb-markdown :deep(pre code) {
  background: none;
  padding: 0;
  color: #333;
}

.kb-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.kb-markdown :deep(th) {
  background: #fafafa;
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
}

.kb-markdown :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e8e8e8;
}

.kb-markdown :deep(tr:nth-child(even)) {
  background: #fafafa;
}

.kb-markdown :deep(blockquote) {
  border-left: 4px solid #1890ff;
  margin: 16px 0;
  padding: 8px 16px;
  background: #f0f7ff;
  color: #555;
}

.kb-markdown :deep(ul),
.kb-markdown :deep(ol) {
  line-height: 1.8;
  padding-left: 24px;
}

.kb-markdown :deep(li) {
  margin: 4px 0;
}

.kb-markdown :deep(a) {
  color: #1890ff;
  text-decoration: none;
}

.kb-markdown :deep(a:hover) {
  text-decoration: underline;
}

.kb-markdown :deep(hr) {
  border: none;
  border-top: 1px solid #e8e8e8;
  margin: 24px 0;
}

.kb-markdown :deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 12px 0;
}

.kb-markdown :deep(strong) {
  font-weight: 600;
}
</style>
