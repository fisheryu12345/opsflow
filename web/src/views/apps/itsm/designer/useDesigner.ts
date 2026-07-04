import { ref, shallowRef, computed, watch, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Graph, Shape, Stencil, MiniMap, Snapline, Clipboard, Selection, Keyboard } from '@antv/x6'
import {
  resolveItsmShape, updateItsmNode, showNodePorts, refreshPortStates,
  DEFAULT_EDGE_ATTRS, CARD_WIDTH, CARD_HEIGHT, ITSM_NODE_CONFIG,
  getNodeConfig, DEFAULT_NODE_FIELDS,
} from './shapes'
import { StateSync, TransitionSync, FieldBatchUpdate, workflowApi, stateApi, transitionApi, DeployWorkflow } from '/@/api/itsm/index'

export function useDesigner(containerId: string, workflowId?: number) {
  const { locale } = useI18n()
  const graph = shallowRef<Graph | null>(null)
  const stencil = shallowRef<Stencil | null>(null)
  const selectedNode = ref<any>(null)
  const selectedEdge = ref<any>(null)
  const loading = ref(false)
  const saving = ref(false)
  const workflow = ref<any>(null)
  const nodes = ref<any[]>([])
  const edges = ref<any[]>([])
  const fields = ref<any[]>([])
  const validateErrors = ref<string[]>([])

  // ── Graph 初始化 ──
  function initGraph(minimapContainer?: HTMLElement) {
    if (graph.value) return

    const g = new Graph({
      container: document.getElementById(containerId)!,
      grid: true,
      panning: { enabled: true },
      mousewheel: { enabled: true, zoomAtMousePosition: true },
      connecting: {
        router: { name: 'manhattan', args: { padding: { top: 30, bottom: 30, left: 30, right: 30 }, step: 20, maxLoopCount: 10000 } },
        connector: { name: 'rounded' },
        anchor: { name: 'center', args: { dx: 0, dy: 0 } },
        connectionPoint: { name: 'boundary', args: { sticky: true } },
        allowBlank: false,
        allowMulti: true,
        allowLoop: false,
        snap: true,
        highlight: true,
        validateConnection: () => true,
      },
      highlighting: {
        nodeAvailable: { name: 'stroke', args: { padding: 4, attrs: { stroke: '#409EFF' } } },
      },
    })

    g.use(new Snapline())
    g.use(new Clipboard())
    g.use(new Selection({ rubberband: true, showNodeSelectionBox: true, modifiers: 'shift' }))
    g.use(new Keyboard({ enabled: true }))
    if (minimapContainer) {
      g.use(new MiniMap({ container: minimapContainer, width: 200, height: 140 }))
    }

    g.on('node:click', ({ node }) => {
      const data = node.getData() || {}
      selectedNode.value = { ...data, _x6Id: node.id }
      selectedEdge.value = null
      g.cleanSelection()
      g.select(node.id)
    })
    g.on('edge:click', ({ edge }) => {
      const data = edge.getData() || {}
      selectedEdge.value = { ...data, _id: edge.id, _x6Id: edge.id }
      selectedNode.value = null
    })
    g.on('blank:click', () => { selectedNode.value = null; selectedEdge.value = null })
    g.on('node:change:data', ({ node }) => {
      if (node.shape === 'itsm-node') updateItsmNode(node)
    })
    g.on('node:mouseenter', ({ node }) => {
      showNodePorts(node, true)
      const ports = node.getPorts()
      for (const p of ports) { node.setPortProp(p.id as string, 'attrs/circle/r', 6) }
      if (node.shape === 'itsm-node') {
        node.setAttrs({ 'del-btn-bg': { visibility: 'visible' }, 'del-btn-icon': { visibility: 'visible' } })
      }
    })
    g.on('node:mouseleave', ({ node }) => {
      showNodePorts(node, false)
      const ports = node.getPorts()
      for (const p of ports) { node.setPortProp(p.id as string, 'attrs/circle/r', 4) }
      if (node.shape === 'itsm-node') {
        node.setAttrs({ 'del-btn-bg': { visibility: 'hidden' }, 'del-btn-icon': { visibility: 'hidden' } })
      }
    })
    g.on('edge:connected', ({ edge }) => {
      const t = edge.getTargetCell()
      const s = edge.getSourceCell()
      if (s && t) { refreshPortStates(s); refreshPortStates(t) }
    })
    g.bindKey('del', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.bindKey('backspace', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.on('node:added', ({ node }) => {
      const data = node.getData() || {}
      // 填单/审批/会签节点自动注入默认表单字段（仅在首次拖入时）
      if ((data.type === 'NORMAL' || data.type === 'APPROVAL' || data.type === 'SIGN') && data.fields == null) {
        data.fields = JSON.parse(JSON.stringify(DEFAULT_NODE_FIELDS[data.type] || []))
        node.setData(data)
      }
      if (node.shape === 'itsm-node') updateItsmNode(node)
    })
    g.on('edge:added', ({ edge }) => {
      if (!edge.getData()) {
        edge.setData({ label: '' })
      }
    })


    graph.value = g
  // 边配置修改自动同步回 X6 cell
  watch(selectedEdge, (val) => {
    if (val && val._x6Id && graph.value) {
      const cell = graph.value.getCellById(val._x6Id)
      if (cell && cell.isEdge()) {
        cell.setData({ ...val })
      }
    }
  }, { deep: true })
  // 节点配置修改自动同步回 X6 cell（名称变更触发视觉更新）
  watch(selectedNode, (val) => {
    if (val && val._x6Id && graph.value) {
      const cell = graph.value.getCellById(val._x6Id)
      if (cell && cell.isNode()) {
        cell.setData({ ...val })
      }
    }
  }, { deep: true })
  }

  // ── Stencil 初始化 ──
  function initStencil(target: HTMLElement) {
    if (!graph.value || stencil.value) return
    const s = new Stencil({
      target: graph.value,
      search: false,
      title: 'FlowNode',
      groups: [{ name: 'itsm', label: 'FlowNode', graphHeight: 700 }],
      stencilGraphWidth: 200,
      layout: (model) => {
        const nodes = model.getNodes()
        const d = (n: any) => n.getData() || {}
        nodes.forEach((n) => {
          const t = d(n).type
          if (t === 'START')             n.setPosition({ x: 26, y: 8 })
          else if (t === 'END')           n.setPosition({ x: 110, y: 8 })
          else if (t === 'EXCLUSIVE')     n.setPosition({ x: 14, y: 82 })
          else if (t === 'CONDITIONAL_PARALLEL') n.setPosition({ x: 110, y: 82 })
          else if (t === 'PARALLEL')      n.setPosition({ x: 14, y: 160 })
          else if (t === 'COVERAGE')      n.setPosition({ x: 110, y: 160 })
          else if (t === 'NORMAL')        n.setPosition({ x: 4, y: 244 })
          else if (t === 'APPROVAL')      n.setPosition({ x: 4, y: 300 })
          else if (t === 'SIGN')          n.setPosition({ x: 4, y: 356 })
          else if (t === 'TASK')          n.setPosition({ x: 4, y: 412 })
        })
      },
      getDropNode(node) {
        const d = node.getData()
        // 将 stencil 卡片预览节点转换为正式 itsm-node 形状
        if (d?.type && !['START', 'END', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL', 'COVERAGE'].includes(d.type)) {
          const n = node.clone()
          n.prop('shape', 'itsm-node')
          n.setSize({ width: CARD_WIDTH, height: CARD_HEIGHT })
          return n
        }
        return node.clone()
      },
    })

    // START/END use circle shape
    const eventNodes = ['START', 'END'].map(type => {
      const shape = type === 'START' ? 'itsm-start-event' : 'itsm-end-event'
      return graph.value!.createNode({ shape, width: 56, height: 56, data: { node_type: 'atom', type } })
    })
    // Gateways use diamond with visible label
    const gatewayCfgs = [
      { type: 'EXCLUSIVE', shape: 'itsm-exclusive-gateway' },
      { type: 'CONDITIONAL_PARALLEL', shape: 'itsm-conditional-parallel-gateway' },
      { type: 'PARALLEL', shape: 'itsm-parallel-gateway' },
      { type: 'COVERAGE', shape: 'itsm-converge-gateway' },
    ]
    const gatewayNodes = gatewayCfgs.map(cfg =>
      graph.value!.createNode({
        shape: cfg.shape, width: 70, height: 70,
        data: { node_type: 'atom', type: cfg.type },
      })
    )
    // Business nodes use card shape
    const cardItems = [
      { type: 'NORMAL', iconText: '📝', title: '填单' },
      { type: 'APPROVAL', iconText: '✓', title: '审批' },
      { type: 'SIGN', iconText: '✍', title: '会签' },
      { type: 'TASK', iconText: '⚙', title: '自动任务' },
    ]
    const cardNodes = cardItems.map(item => {
      const cfg = getNodeConfig(item.type)
      return graph.value!.createNode({
        shape: 'itsm-stencil', width: 168, height: 48,
        attrs: {
          iconRect: { fill: `${cfg.color}18` },
          iconLabel: { text: item.iconText, fill: cfg.color },
          title: { text: item.title },
        },
        data: { node_type: 'atom', type: item.type },
      })
    })

    s.load([...eventNodes, ...gatewayNodes, ...cardNodes], 'itsm')
    target.appendChild(s.container!)
    stencil.value = s
  }

  // ── 加载 Workflow ──
  async function loadWorkflow(id: number) {
    loading.value = true
    try {
      const [wfRes, stRes, trRes] = await Promise.all([
        workflowApi.detail(String(id)),
        stateApi.list({ workflow: id }),
        transitionApi.list({ workflow: id }),
      ])
      workflow.value = wfRes.data?.data || wfRes.data || wfRes
      const states = stRes.data?.data || stRes.data?.results || stRes.data || []
      const trans = trRes.data?.data || trRes.data?.results || trRes.data || []
      nodes.value = states
      edges.value = trans
      _renderGraph(states, trans)
    } catch (e) { console.error(e); ElMessage.error('加载流程失败') }
    loading.value = false
  }

  function _renderGraph(states: any[], trans: any[]) {
    const g = graph.value
    if (!g) return
    g.clearCells()

    const contentStates = states.filter((s: any) => s.type !== 'START' && s.type !== 'END')

    contentStates.forEach((s: any, i: number) => {
      const col = Math.floor(i / 10)
      const row = i % 10
      s._x = 80 + col * 280
      s._y = 80 + row * 90
    })

    states.forEach((s: any) => {
      const nodeId = `node_${s.id}`
      const shap = resolveItsmShape(s.type)
      const isGateway = ['itsm-exclusive-gateway', 'itsm-conditional-parallel-gateway', 'itsm-parallel-gateway', 'itsm-converge-gateway'].includes(shap)
      const isEvent = shap === 'itsm-start-event' || shap === 'itsm-end-event'
      g.addNode({
        shape: shap, id: nodeId,
        x: s._x || 80, y: s._y || 80,
        width: isEvent ? 56 : isGateway ? 70 : CARD_WIDTH,
        height: isEvent ? 56 : isGateway ? 70 : CARD_HEIGHT,
        data: { ...s, id: s.id },
      })
    })

    trans.forEach((t: any) => {
      const fromNode = g.getCellById(`node_${t.from_state}`)
      const toNode = g.getCellById(`node_${t.to_state}`)
      if (!fromNode || !toNode) return
      const isReject = t.direction === 'reject' || t.name === 'reject'
      g.addEdge({
        source: { cell: fromNode.id, port: 'bottom' },
        target: { cell: toNode.id, port: 'top' },
        attrs: {
          line: {
            stroke: isReject ? '#F56C6C' : t.condition ? '#E6A23C' : '#DCDFE6',
            strokeWidth: 1.5, targetMarker: 'classic',
            strokeDasharray: isReject ? '8,4' : undefined,
          },
        },
        data: {
          ...t, _from_state: t.from_state, _to_state: t.to_state,
          isReject, label: isReject ? '驳回' : (t.condition ? '条件' : ''),
        },
      })
    })

    g.centerContent()
  }

  // ── 保存 ──
  async function saveDesigner(workflowData: any, nodeList: any[], edgeList: any[]) {
    saving.value = true
    try {
      const wfId = workflow.value?.id || workflowData.id
      const stData = nodeList
        .filter((n: any) => n.type !== 'START' && n.type !== 'END')
        .map((n: any) => ({
          id: n.originId || n.id, workflow_id: wfId, name: n.name || getNodeConfig(n.type).label,
          type: n.type, processors_type: n.processors_type || '',
          processors: n.processorsRaw || n.processors || '',
          is_multi: n.is_multi ?? false, is_sequential: n.is_sequential ?? false,
          is_allow_skip: n.is_allow_skip ?? false, is_builtin: n.is_builtin ?? false,
          fields: n.fields || [],
        }))
      const trData = edgeList.map((e: any) => ({
        id: e.originId || e._id, workflow_id: wfId, name: e.label || '',
        from_state_id: e._from_state, to_state_id: e._to_state,
        condition: e.condition || null, condition_type: e.condition ? 'script' : '',
        direction: e.isReject ? 'reject' : 'forward',
      }))
      // 同步流程名称等元数据
      await workflowApi.update(String(wfId), {
        name: workflowData.name,
        description: workflowData.description,
        itsm_type: workflowData.itsm_type,
      })
      await StateSync(wfId, stData)
      await TransitionSync(wfId, trData)
      await loadWorkflow(wfId)
      ElMessage.success('保存成功')
    } catch (e) { console.error(e); ElMessage.error('保存失败') }
    saving.value = false
  }

  // ── 部署 ──
  async function deployWorkflow() {
    const errs = validateWorkflow()
    if (errs.length > 0) {
      validateErrors.value = errs
      ElMessage.warning(`校验未通过: ${errs[0]}`)
      return
    }
    const g = graph.value
    if (!g || !workflow.value?.id) return
    const cells = g.getCells()
    const nodeList: any[] = []
    const edgeList: any[] = []
    for (const cell of cells) {
      if (cell.isNode()) {
        const data = cell.getData()
        if (data && data.type !== 'START' && data.type !== 'END') nodeList.push(data)
      } else if (cell.isEdge()) {
        const data = cell.getData()
        if (data) edgeList.push(data)
      }
    }
    await saveDesigner(workflow.value, nodeList, edgeList)
    try {
      await DeployWorkflow(String(workflow.value.id))
      ElMessage.success('部署成功')
      await loadWorkflow(workflow.value.id)
    } catch (e) { console.error(e); ElMessage.error('部署失败') }
  }

  // ── 校验 ──
  function validateWorkflow(): string[] {
    const errs: string[] = []
    const g = graph.value
    if (!g) return ['画布未初始化']
    const nodeDataList = g.getCells().filter(c => c.isNode()).map(c => c.getData()).filter(Boolean)
    if (!nodeDataList.some((d: any) => d.type === 'START')) errs.push('缺少开始节点')
    if (!nodeDataList.some((d: any) => d.type === 'END')) errs.push('缺少结束节点')
    nodeDataList.filter((d: any) => d.type === 'APPROVAL').forEach((a: any) => {
      if (!a.processors_type && !a.processorsRaw) errs.push(`${a.name || '审批节点'}未配置处理人`)
    })
    const pg = nodeDataList.filter((d: any) => d.type === 'CONDITIONAL_PARALLEL' || d.type === 'PARALLEL')
    const cg = nodeDataList.filter((d: any) => d.type === 'COVERAGE')
    // 排他网关出边校验：前端约束，至少有一条无条件边
    const edgeDataList = allCells.filter(c => c.isEdge()).map(c => c.getData()).filter(Boolean)
    nodeDataList.filter((d: any) => d.type === 'EXCLUSIVE').forEach((gw: any) => {
      const outEdges = edgeDataList.filter((e: any) => e._from_state === gw.id || e._from_state === String(gw.id))
      const hasDefault = outEdges.some((e: any) => !e.condition && !e.isReject)
      if (!hasDefault) errs.push('排他网关「' + (gw.name || gw.type) + '」缺少默认（无条件）出边')
    })
    if (pg.length > cg.length) errs.push('并行网关与汇聚网关数量不匹配')
    validateErrors.value = errs
    return errs
  }

  // ── 自动布局 (调用后端 Sugiyama 布局引擎) ──
  async function autoLayout() {
    const g = graph.value
    if (!g) return
    const cells = g.getCells()
    const nodeList = cells.filter(c => c.isNode())
    const edgeList = cells.filter(c => c.isEdge())

    if (!nodeList.length) return

    const wfId = workflow.value?.id
    if (!wfId) {
      ElMessage.warning('请先保存流程后再使用自动布局')
      return
    }

    // 收集节点数据 (id + type + name)
    const nodesData = nodeList.map(n => {
      const d = n.getData() || {}
      return { id: d.id || n.id, type: d.type, name: d.name || '' }
    })

    // 收集边数据 (from_state → to_state)
    const edgesData = edgeList.map((e: any) => {
      const d = e.getData() || {}
      const src = e.getSourceCellId?.() || ''
      const tgt = e.getTargetCellId?.() || ''
      // Extract state IDs from X6 cell IDs (format: node_<id>)
      const fromId = d.from_state || d._from_state || (src.startsWith('node_') ? src.slice(5) : src)
      const toId = d.to_state || d._to_state || (tgt.startsWith('node_') ? tgt.slice(5) : tgt)
      return { id: d.id || e.id, from_state: String(fromId), to_state: String(toId) }
    })

    try {
      const { workflowApi } = await import('/@/api/itsm/index')
      // Use a dedicated request for layout since workflowApi doesn't have a layout method
      const { request } = await import('/@/utils/service')
      const res: any = await request({
        url: `/api/itsm/workflows/${wfId}/layout/`,
        method: 'post',
        data: { nodes: nodesData, edges: edgesData },
      })
      const positions = (res as any).data?.positions || (res as any).positions || []
      if (!positions.length) {
        ElMessage.warning('Layout returned no positions')
        return
      }

      // Apply positions: map state ID → X6 cell ID (node_<id>)
      for (const pos of positions) {
        const cell = g.getCellById(`node_${pos.id}`)
        if (cell && cell.isNode()) {
          cell.setPosition({ x: pos.x, y: pos.y })
        }
      }
      g.centerContent()
      ElMessage.success('Auto layout complete')
    } catch (e: any) {
      console.error('Layout failed:', e)
      ElMessage.error(e?.msg || 'Layout computation failed')
    }
  }

  function destroy() {
    graph.value?.dispose()
    graph.value = null
  }

  return {
    graph, stencil, selectedNode, selectedEdge, loading, saving,
    workflow, nodes, edges, fields, validateErrors,
    initGraph, initStencil, loadWorkflow, saveDesigner, deployWorkflow, validateWorkflow, autoLayout, destroy,
  }
}
