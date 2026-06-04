<template>
  <div class="tp-wrap">
    <!-- Toolbar -->
    <div class="tp-bar">
      <el-button-group>
        <el-button :icon="ZoomIn" size="small" @click="zoomIn" />
        <el-button :icon="ZoomOut" size="small" @click="zoomOut" />
        <el-button :icon="FullScreen" size="small" @click="fitView" />
        <el-button :icon="Refresh" size="small" @click="resetExpand" />
      </el-button-group>
      <span class="tp-sep" />
      <span class="tp-hint">{{ count }} 节点 · 单击展开/收起 · 右键详情</span>
    </div>

    <!-- Canvas -->
    <div ref="containerRef" class="tp-cvs" />

    <!-- Context Menu (detail) -->
    <div v-if="ctxNode" class="tp-ctx" :style="{ left: ctxPos.x + 'px', top: ctxPos.y + 'px' }" @click.stop>
      <div class="tp-ctx-hd">
        <strong>{{ ctxNode.label }}</strong>
        <el-tag size="small" :type="tagType(ctxNode.type)" effect="dark">{{ typeLabel(ctxNode.type) }}</el-tag>
      </div>
      <div class="tp-ctx-bd">
        <div v-for="(v, k) in ctxAttrs" :key="k" class="tp-ctx-r">
          <span class="tp-ctx-k">{{ k }}</span>
          <span class="tp-ctx-v">{{ v }}</span>
        </div>
      </div>
      <el-button size="small" text @click="ctxNode = null" style="width:100%;margin-top:6px;">关闭</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import G6 from '@antv/g6'
import { ZoomIn, ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'

const props = defineProps<{ nodes: any[]; edges: any[] }>()
const emit = defineEmits<{ nodeClick: [n: any] }>()

const containerRef = ref<HTMLDivElement | null>(null)
const graph = ref<any>(null)
const count = ref(0)
const ctxNode = ref<any>(null)
const ctxPos = ref({ x: 0, y: 0 })

const NAMES: Record<string, string> = { Biz: '业务', Set: '集群', Module: '模块', Host: '主机', Process: '进程', biz: '业务', set: '集群', module: '模块', host: '主机', process: '进程' }
const TAG_TYPES: Record<string, string> = { Biz: 'primary', Set: 'success', Module: 'warning', Host: 'info', Process: '', biz: 'primary', set: 'success', module: 'warning', host: 'info', process: '' }
function typeLabel(t: string) { return NAMES[t] || t || '未知' }
function tagType(t: string) { return TAG_TYPES[t] || 'info' }

function getType(n: any): string { return n.model_code || n.type || '' }
function getAttrs(n: any): any { return n.attrs || n }
function getStatus(n: any): string {
  const a = getAttrs(n)
  return a.status || ''
}

// ─── Build tree ───
function toTree(): any {
  if (!props.nodes.length) return null
  const nodeMap: Record<string, any> = {}
  const children: Record<string, string[]> = {}
  const parent: Record<string, string> = {}
  for (const n of props.nodes) { nodeMap[n.id] = n; children[n.id] = [] }
  for (const e of props.edges) {
    // Skip non-hierarchical relationships for tree building
    if (e.type === 'RUNS' || e.type === 'DEPENDS_ON' || e.type === 'runs' || e.type === 'depends_on') continue
    if (children[e.from]) children[e.from].push(e.to)
    parent[e.to] = e.from
  }
  const roots = props.nodes.filter(n => !parent[n.id]).map(n => n.id)
  if (!roots.length && props.nodes.length) roots.push(props.nodes[0].id)

  function walk(id: string): any {
    const n = nodeMap[id]
    if (!n) return null
    const a = getAttrs(n)
    const st = getStatus(n)
    const tp = getType(n)
    const color = (tp === 'Host' || tp === 'host' || tp === 'Process' || tp === 'process')
      ? ({ normal: '#52c41a', alarm: '#f5222d', offline: '#8c8c8c', maintenance: '#faad14' }[st] || '#1890ff')
      : ({ Biz: '#1890ff', Set: '#52c41a', Module: '#722ed1', Host: '#13c2c2', Process: '#8c8c8c',
           biz: '#1890ff', set: '#52c41a', module: '#722ed1', host: '#13c2c2', process: '#8c8c8c' }[tp] || '#1890ff')
    const kids = (children[id] || []).map(walk).filter(Boolean)
    return {
      id,
      label: (n.label || id).slice(0, 20),
      type: tp,
      color,
      sub: tp === 'Host' || tp === 'host' ? (a.ip || a.hostname || '') : tp === 'Process' || tp === 'process' ? (a.name || '') : '',
      attrs: a,
      collapsible: kids.length > 0,
      collapsed: true,
      children: kids.length ? kids : undefined,
    }
  }
  if (roots.length === 1) return walk(roots[0])
  return { id: '_root', label: 'CMDB', type: 'root', color: '#1890ff', collapsible: true, collapsed: true, children: roots.map(walk).filter(Boolean) }
}

// ─── Init ───
function init() {
  if (!containerRef.value) return
  if (graph.value) { graph.value.destroy(); graph.value = null }

  const data = toTree()
  if (!data) return

  // Force container to have size
  const rect = containerRef.value.getBoundingClientRect()
  const w = rect.width || containerRef.value.clientWidth || 800
  const h = rect.height || containerRef.value.clientHeight || 500

  const g = new G6.TreeGraph({
    container: containerRef.value,
    width: w,
    height: h,
    fitView: true,
    fitViewPadding: [40, 40, 40, 100],
    animate: { duration: 300, easing: 'easeCubic' },
    modes: {
      default: ['zoom-canvas', 'drag-canvas'],
    },
    defaultEdge: {
      type: 'smooth',
      style: { stroke: '#ccc', lineWidth: 1.5, endArrow: { path: 'M0,0 L5,4 L5,-4 Z', fill: '#ccc' } },
    },
    layout: {
      type: 'compactBox',
      direction: 'LR',
      getWidth: () => 110,
      getHeight: () => 32,
      getVGap: () => 20,
      getHGap: () => 50,
    },
  })

  // ✅ Built-in collapse/expand: G6 TreeGraph handles `collapsed` automatically
  // when `animate: true` is set — just toggle the model property.

  g.on('node:click', (evt: any) => {
    const model = evt.item.getModel()
    // Toggle collapse
    if (model.collapsible) {
      model.collapsed = !model.collapsed
      g.updateChild(model, model.id)
      g.layout()
    }
  })

  // Show detail on right-click
  g.on('node:contextmenu', (evt: any) => {
    evt.preventDefault?.()
    const model = evt.item.getModel()
    const raw = model
    ctxNode.value = raw
    const cp = g.getCanvasByClient(evt.clientX, evt.clientY)
    ctxPos.value = { x: Math.min(cp.x + 10, w - 260), y: Math.min(cp.y - 10, h - 200) }
    emit('nodeClick', raw)
  })

  g.on('canvas:click', () => { ctxNode.value = null })

  g.data(data)
  g.render()
  g.fitView([40, 40, 40, 100])

  count.value = g.getNodes().length
  graph.value = g
  watchSize()
}

// ── Resize ──
let ro: ResizeObserver | null = null
function watchSize() {
  if (!containerRef.value) return
  ro = new ResizeObserver(() => {
    if (graph.value && containerRef.value) {
      const r = containerRef.value.getBoundingClientRect()
      if (r.width > 0 && r.height > 0) graph.value.changeSize(r.width, r.height)
    }
  })
  ro.observe(containerRef.value)
}

// ── Controls ──
function zoomIn() { graph.value?.zoom(1.25) }
function zoomOut() { graph.value?.zoom(0.8) }
function fitView() { graph.value?.fitView([40, 40, 40, 100]) }
function resetExpand() {
  if (!graph.value) return
  const d = graph.value.getData()
  function walk(n: any) { n.collapsed = true; if (n.children) n.children.forEach(walk) }
  walk(d)
  graph.value.data(d)
  graph.value.render()
  graph.value.fitView([40, 40, 40, 100])
}

// ── Ctx attrs ──
const ctxAttrs = computed(() => {
  if (!ctxNode.value) return {}
  const a = ctxNode.value.attrs || {}
  const L: Record<string, string> = {
    ip: 'IP', hostname: '主机名', status: '状态', os_type: '系统',
    cpu_cores: 'CPU', memory_mb: '内存(MB)', disk_gb: '磁盘(GB)',
    agent_status: 'Agent', region: '区域',
    lifecycle: '生命周期', operator: '负责人', env_type: '环境',
    service_type: '服务类型', name: '名称', port: '端口',
    protocol: '协议', version: '版本', description: '描述',
  }
  const r: Record<string, any> = {}
  for (const [k, v] of Object.entries(a)) r[L[k] || k] = v
  return r
})

// ── Watch data ──
watch(() => [props.nodes.length, props.edges.length], () => {
  if (graph.value) { graph.value.destroy(); graph.value = null }
  init()
})

// ── Lifecycle ──
onMounted(() => {
  // Use rAF to ensure DOM is ready
  requestAnimationFrame(() => init())
})
onBeforeUnmount(() => {
  ro?.disconnect()
  graph.value?.destroy()
})
</script>

<style scoped>
.tp-wrap { width: 100%; height: 100%; display: flex; flex-direction: column; background: #fafafa; overflow: hidden; position: relative; }
.tp-bar { display: flex; align-items: center; gap: 6px; padding: 6px 16px; background: #fff; border-bottom: 1px solid #ebeef5; flex-shrink: 0; z-index: 10; }
.tp-sep { width: 1px; height: 18px; background: #dcdfe6; margin: 0 4px; }
.tp-hint { font-size: 12px; color: #909399; }
.tp-cvs { flex: 1; min-height: 400px; width: 100%; }

/* Context menu */
.tp-ctx {
  position: absolute; z-index: 100;
  background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,.1); padding: 10px 14px;
  min-width: 200px; max-width: 280px;
  pointer-events: auto;
}
.tp-ctx-hd { display: flex; align-items: center; margin-bottom: 8px; gap: 6px; }
.tp-ctx-hd strong { font-size: 13px; }
.tp-ctx-r { display: flex; justify-content: space-between; padding: 3px 0; font-size: 12px; }
.tp-ctx-k { color: #909399; }
.tp-ctx-v { color: #303133; font-weight: 500; }
</style>
