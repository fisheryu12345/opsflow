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
  // Persistent node_key counter to avoid duplicates when multiple nodes
  // are added in the same tick (each node:added handler independently
  // computing maxN from g.getNodes() can race).
  let _nodeKeyCounter = 0
  function _nextNodeKey(): string {
    if (_nodeKeyCounter === 0) {
      const g = graph.value
      if (g) {
        for (const cell of g.getNodes()) {
          const m = (cell.getData()?.node_key || '').match(/^node_(\d+)$/)
          if (m) _nodeKeyCounter = Math.max(_nodeKeyCounter, parseInt(m[1], 10))
        }
      }
    }
    return `node_${++_nodeKeyCounter}`
  }
  const selectedNode = ref<any>(null)
  const selectedEdge = ref<any>(null)

  // Auto-sync selectedNode changes back to cell data immediately.
  // Without this, configuring multiple nodes and saving only syncs the last one.
  watch(selectedNode, (sn) => {
    if (!sn?._x6Id) return
    const g = graph.value
    if (!g) return
    const cell = g.getCellById(sn._x6Id)
    if (!cell || !cell.isNode()) return
    const cellData = cell.getData()
    if (!cellData) return
    const dirtyKeys = ['_usePreset', 'preset_id', 'preset', 'processorsRaw', 'processors_type', 'processors', 'name', 'is_multi', 'is_sequential', 'is_allow_skip', 'distribute_type', 'type', 'fields']
    let synced = false
    for (const k of dirtyKeys) {
      if (sn[k] !== undefined && cellData[k] !== sn[k]) {
        cellData[k] = sn[k]
        synced = true
      }
    }
  }, { deep: true })
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
        validateConnection({ sourceCell, targetCell, sourcePort, targetPort }) {
          if (!sourceCell || !sourcePort) return false
          // Must connect to a valid cell port
          if (!targetCell && !targetPort) return false
          // START only has outgoing connections
          if (sourceCell?.getData()?.type === 'END') return false
          // END only has incoming connections
          if (targetCell?.getData()?.type === 'START') return false
          return true
        },
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
      const s = edge.getSourceCell()
      const t = edge.getTargetCell()
      const src = edge.getSource()
      const tgt = edge.getTarget()
      // Fix edge data after connection is finalized (edge:added fires before target is resolved)
      if (tgt?.cell) {
        const ed = edge.getData() || {}
        ed.from_node_key = s?.getData()?.node_key || src.cell || ''
        ed.to_node_key = t?.getData()?.node_key || tgt.cell || ''
        ed._from_state = src.cell || ''
        ed._to_state = tgt.cell || ''
        edge.setData(ed)
      }
      if (s && t) { refreshPortStates(s); refreshPortStates(t) }
    })
    g.bindKey('del', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.bindKey('backspace', () => { const c = g.getSelectedCells(); if (c.length) g.removeCells(c) })
    g.on('node:added', ({ node }) => {
      const data = node.getData() || {}
      const isCardNode = node.shape === 'itsm-node'
      const isEvent = node.shape === 'itsm-start-event' || node.shape === 'itsm-end-event'
      const isGateway = ['itsm-exclusive-gateway', 'itsm-conditional-parallel-gateway', 'itsm-parallel-gateway', 'itsm-converge-gateway'].includes(node.shape)
      // Generate node_key for START/END like content nodes
      if (isEvent && !data._initialized) {
        data.node_key = _nextNodeKey()
        data._initialized = true
        node.setData(data)
      }
      // Initialize gateway nodes on drop from stencil — they need node_key to survive save/reload
      if (isGateway && !data._initialized) {
        if (!data.node_key) {
          data.node_key = _nextNodeKey()
        }
        data._initialized = true
        node.setData(data)
      }
      // Populate complete default data on first drop from stencil
      // (stencil nodes only have { node_type, type }; without this the config panel shows empty)
      if (isCardNode && !data._initialized) {
        // Generate stable node_key (node_{N+1} format) — does NOT change X6 cell ID
        if (!data.node_key) {
          data.node_key = _nextNodeKey()
        }
        const cfg = getNodeConfig(data.type || 'NORMAL')
        data.name = data.name || cfg.label
        data.processors_type = data.processors_type || ''
        // Populate processorsRaw from processors on load; processorsRaw is the
        // frontend canonical field; processors is the backend TextField value.
        data.processorsRaw = data.processorsRaw || data.processors || ''
        // Backend returns 'preset' (FK id), frontend uses 'preset_id'
        data.preset_id = data.preset_id ?? data.preset ?? null
        data._usePreset = data._usePreset ?? (data.preset_id ? true : false)
        data.is_multi = data.is_multi ?? false
        data.is_sequential = data.is_sequential ?? false
        data.is_allow_skip = data.is_allow_skip ?? false
        data.is_builtin = data.is_builtin ?? false
        data.node_key = data.node_key || node.id
        data.api_instance_id = data.api_instance_id ?? 0
        // Inject default form fields for fill/approval/sign nodes
        if ((data.type === 'NORMAL' || data.type === 'APPROVAL' || data.type === 'SIGN') && data.fields == null) {
          data.fields = JSON.parse(JSON.stringify(DEFAULT_NODE_FIELDS[data.type] || []))
        }
        data._initialized = true
        node.setData(data)
      }
      if (isCardNode) updateItsmNode(node)
    })
    g.on('edge:added', ({ edge }) => {
      const ed = edge.getData() || {}
      const srcCell = edge.getSourceCell()
      const tgtCell = edge.getTargetCell()
      const srcId = edge.getSourceCellId?.() || ''
      const tgtId = edge.getTargetCellId?.() || ''
      if (!ed.label && !ed._initialized) ed.label = ''
      if (!ed.from_node_key) {
        ed.from_node_key = srcCell?.getData()?.node_key || srcCell?.id || ''
      }
      if (!ed.to_node_key) {
        ed.to_node_key = tgtCell?.getData()?.node_key || tgtCell?.id || ''
      }
      if (!ed._from_state) ed._from_state = srcId
      if (!ed._to_state) ed._to_state = tgtId
      edge.setData(ed)
    })


    graph.value = g
  // Sync edge config changes back to X6 cell
  watch(selectedEdge, (val) => {
    if (val && val._x6Id && graph.value) {
      const cell = graph.value.getCellById(val._x6Id)
      if (cell && cell.isEdge()) {
        cell.setData({ ...val })
      }
    }
  }, { deep: true })
  // Sync node config changes back to X6 cell + refresh card visual
  watch(selectedNode, (val) => {
    if (val && val._x6Id && graph.value) {
      const cell = graph.value.getCellById(val._x6Id)
      if (cell && cell.isNode()) {
        cell.setData({ ...val })
        if (cell.shape === 'itsm-node') updateItsmNode(cell)
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
        // Create fresh nodes instead of cloning — cloning breaks X6 view binding
        if (d?.type) {
          const gatewayTypes = ['EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL', 'COVERAGE']
          if (gatewayTypes.includes(d.type)) return node.clone()  // gateways can clone safely
          const isEvent = d.type === 'START' || d.type === 'END'
          const shape = isEvent
            ? (d.type === 'START' ? 'itsm-start-event' : 'itsm-end-event')
            : 'itsm-node'
          const w = isEvent ? 56 : CARD_WIDTH
          const h = isEvent ? 56 : CARD_HEIGHT
          const n = graph.value!.createNode({ shape, width: w, height: h })
          n.setData({ ...d })
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
        stateApi.list({ workflow: id, page_size: 1000 }),
        transitionApi.list({ workflow: id, page_size: 1000 }),
      ])
      workflow.value = wfRes.data?.data || wfRes.data || wfRes
      const states = stRes.data?.data || stRes.data?.results || stRes.data || []
      const trans = trRes.data?.data || trRes.data?.results || trRes.data || []
      nodes.value = states
      edges.value = trans
      _renderGraph(states, trans)
      // Auto-layout after loading (non-blocking)
      setTimeout(() => autoLayout().catch(() => {}), 300)
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

    // Generate unique node_keys for old states without one (prevent conflicts)
    let maxN = 0
    for (const s of states) {
      const m = (s.node_key || '').match(/^node_(\d+)$/)
      if (m) maxN = Math.max(maxN, parseInt(m[1], 10))
    }
    _nodeKeyCounter = maxN  // sync counter with loaded states
    const stateNkMap: Record<string, string> = {}  // DB id → new node_key
    for (const s of states) {
      if (s.node_key) {
        stateNkMap[String(s.id)] = s.node_key
      } else {
        stateNkMap[String(s.id)] = `node_${++maxN}`
      }
    }

    // Render all states including START/END
    for (const s of states) {
      const nk = stateNkMap[String(s.id)]
      const nodeId = nk
      s.node_key = nk  // update source so edge lookup works
      const shap = resolveItsmShape(s.type)
      const isGateway = ['itsm-exclusive-gateway', 'itsm-conditional-parallel-gateway', 'itsm-parallel-gateway', 'itsm-converge-gateway'].includes(shap)
      const isEvent = shap === 'itsm-start-event' || shap === 'itsm-end-event'
      if (isGateway) {
      }
      g.addNode({
        shape: shap, id: nodeId,
        x: s._x || 80, y: s._y || 80,
        width: isEvent ? 56 : isGateway ? 70 : CARD_WIDTH,
        height: isEvent ? 56 : isGateway ? 70 : CARD_HEIGHT,
        data: { ...s, id: s.id, node_key: nk },
      })
    }

    // Build state_id → cell_id map for edge lookups
    const cellIdMap: Record<string, string> = {}
    for (const s of states) {
      cellIdMap[String(s.id)] = stateNkMap[String(s.id)]
    }

    trans.forEach((t: any) => {
      const fromCellId = t.from_node_key || cellIdMap[String(t.from_state)] || `node_${t.from_state}`
      const toCellId = t.to_node_key || cellIdMap[String(t.to_state)] || `node_${t.to_state}`
      const fromNode = g.getCellById(fromCellId)
      const toNode = g.getCellById(toCellId)
      if (!fromNode || !toNode) {
        return
      }
      const isReject = t.direction === 'reject' || t.name === 'reject'
      // Compute edge label for display: condition text (truncated) or reject label
      const condText = typeof t.condition === 'string' ? t.condition : ''
      const edgeLabel = isReject ? '驳回' : condText
      const labelText = edgeLabel.length > 20 ? edgeLabel.substring(0, 18) + '…' : edgeLabel

      g.addEdge({
        source: { cell: fromNode.id, port: 'right' },
        target: { cell: toNode.id, port: 'left' },
        labels: labelText ? [{ attrs: { text: { text: labelText, fontSize: 10, fill: '#909399' } } }] : undefined,
        attrs: {
          line: {
            stroke: isReject ? '#F56C6C' : t.condition ? '#E6A23C' : '#DCDFE6',
            strokeWidth: 1.5, targetMarker: 'classic',
            strokeDasharray: isReject ? '8,4' : undefined,
          },
        },
        data: {
          ...t, _from_state: fromCellId, _to_state: toCellId,
          from_node_key: t.from_node_key || '',
          to_node_key: t.to_node_key || '',
          isReject, label: edgeLabel,
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
        .map((n: any) => {
          const gatewayTypes = ['EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL', 'COVERAGE']
          if (gatewayTypes.includes(n.type)) {
          }
          // Normalize processors to JSON array format (consistent with preset expansion)
          let proc = n.processorsRaw || n.processors || ''
          if (proc && proc.trim()) {
            let arr: any[] = []
            try {
              const parsed = JSON.parse(proc)
              arr = Array.isArray(parsed) ? parsed : [parsed]
            } catch {
              // Not JSON → comma-separated, convert to JSON array
              arr = proc.split(',').map((v: string) => v.trim()).filter(Boolean)
                  .map((v: string) => /^\d+$/.test(v) ? parseInt(v, 10) : v)
            }
            proc = JSON.stringify(arr)
          }
          return {
            ...(n.originId && typeof n.originId === 'number' ? { id: n.originId } : {}),
            node_key: n.node_key || n.id, workflow_id: wfId, name: n.name || getNodeConfig(n.type).label,
            type: n.type, processors_type: n.processors_type || '',
            processors: proc,
            preset_id: n._usePreset ? (n.preset_id || null) : null,
            is_multi: n.is_multi ?? false, is_sequential: n.is_sequential ?? false,
            is_allow_skip: n.is_allow_skip ?? false, is_builtin: n.is_builtin ?? false,
            fields: n.fields || [],
          }
        })
      const trData = edgeList.map((e: any) => {
      // Re-derive node_key from real-time cell data (stale edge data can be wrong)
      const g = graph.value
      let fnk = e.from_node_key || ''
      let tnk = e.to_node_key || ''
      if (g) {
        const srcCell = g.getCellById(e._from_state || '') || (fnk ? g.getCellById(fnk) : null)
        const tgtCell = g.getCellById(e._to_state || '') || (tnk ? g.getCellById(tnk) : null)
        fnk = srcCell?.getData()?.node_key || fnk
        tnk = tgtCell?.getData()?.node_key || tnk
      }
      return {
        ...(e.originId && typeof e.originId === 'number' ? { id: e.originId } : {}),
        workflow_id: wfId, name: (e.label || '').slice(0, 60),
        from_node_key: fnk, to_node_key: tnk,
        condition: e.condition || '',
        condition_type: (typeof e.condition === 'string' && e.condition.trim()) ? 'script' : '',
        direction: e.isReject ? 'reject' : 'forward',
      }})
      // Sync workflow metadata
      await workflowApi.update(String(wfId), {
        name: workflowData.name,
        description: workflowData.description,
        itsm_type: workflowData.itsm_type,
      })
      await StateSync(wfId, stData)
      await TransitionSync(wfId, trData)
      // Mark as draft to re-enable deploy button after modifying a deployed workflow
      if (workflow.value && !workflow.value.is_draft) {
        workflow.value.is_draft = true
        await workflowApi.update(String(wfId), { is_draft: true })
      }
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

    // Sync selectedNode edits back to cell data before saving.
    if (selectedNode.value?._x6Id) {
      const sn = selectedNode.value
      const cell = g.getCellById(sn._x6Id)
      if (cell && cell.isNode()) {
        const cellData = cell.getData()
        if (cellData) {
          const syncKeys = ['_usePreset', 'preset_id', 'preset', 'processorsRaw', 'processors_type', 'processors']
          for (const k of syncKeys) {
            if (sn[k] !== undefined) {
              cellData[k] = sn[k]
            }
          }
        }
      }
    }

    const cells = g.getCells()
    const nodeList: any[] = []
    const edgeList: any[] = []
    for (const cell of cells) {
      if (cell.isNode()) {
        const data = cell.getData()
        if (data) nodeList.push(data)
      } else if (cell.isEdge()) {
        const data = cell.getData()
        if (data) edgeList.push(data)
      }
    }
    await saveDesigner(workflow.value, nodeList, edgeList)
    try {
      await DeployWorkflow(String(workflow.value.id))
      if (workflow.value) {
        workflow.value.is_draft = false
        workflow.value.is_enabled = true
      }
      ElMessage.success('部署成功')
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
    // Exclusive gateway validation: removed "default edge" requirement.
    // bamboo-engine evaluates conditions at runtime — if no condition matches,
    // the gateway simply doesn't dispatch. Aligned with opsflow behavior.
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

    // Collect node data — use X6 cell ID directly so positions map back correctly
    const nodesData = nodeList.map(n => {
      const d = n.getData() || {}
      return { id: n.id, type: d.type, name: d.name || '' }
    })

    // Collect edge data — use X6 cell IDs for source/target
    const edgesData = edgeList.map((e: any) => {
      const d = e.getData() || {}
      const srcId = e.getSourceCellId?.() || ''
      const tgtId = e.getTargetCellId?.() || ''
      return { id: e.id, from_state: srcId, to_state: tgtId }
    })

    try {
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

      // Apply positions and save to cell data for pipeline_tree reuse
      for (const pos of positions) {
        const cell = g.getCellById(String(pos.id))
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
