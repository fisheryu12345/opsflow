/**
 * BFS-based layout algorithm for ITSM flow chart nodes.
 * Aligned with Opsflow's layoutNodes in useGraphCanvas.ts.
 */
export function layoutNodes(
  nodes: any[],
  edges: { from: string; to: string }[],
  options?: { layerGap?: number; nodeGap?: number; startX?: number; startY?: number },
): Record<string, { x: number; y: number }> {
  const LAYER_GAP = options?.layerGap ?? 480
  const NODE_GAP = options?.nodeGap ?? 120
  const START_X = options?.startX ?? 50
  const START_Y = options?.startY ?? 40

  console.group('[layoutNodes] === BFS Layout Start ===')
  console.debug('[layoutNodes] params:', { nodeCount: nodes.length, edgeCount: edges.length, LAYER_GAP, NODE_GAP, START_X, START_Y })

  // ── Step 1: Collect ALL gateway types ──
  const gatewayIds = new Set(nodes.filter(n => (n.node_type || '').includes('gateway')).map(n => n.id))
  console.debug('[layoutNodes] step1 - gateways:', [...gatewayIds])
  console.debug('[layoutNodes] step1 - all nodes:', nodes.map(n => `${n.id}[${n.node_type}]`).join(', '))
  console.debug('[layoutNodes] step1 - all edges:', edges.map(e => {
    const f = e.from || (e as any).source; const t = e.to || (e as any).target
    return `${f}→${t}`
  }).join(', '))

  // ── Step 2: Build adjacency list & initial in-degree ──
  const inDeg: Record<string, number> = {}
  const adj: Record<string, string[]> = {}
  for (const n of nodes) { inDeg[n.id] = 0; adj[n.id] = [] }
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    if (adj[f]) adj[f].push(t)
    else adj[f] = [t]
    if (inDeg[t] != null) inDeg[t]++
  }
  console.debug('[layoutNodes] step2 - initial inDeg:', Object.entries(inDeg).map(([id, d]) => `${id}:${d}`).join(', '))
  console.debug('[layoutNodes] step2 - adjacency:', Object.entries(adj).map(([id, nb]) => `${id}→[${nb.join(',')}]`).join(' | '))

  // ── Step 3: Detect loopback edges from gateways ──
  const loopbackTargets = new Set<string>()
  const loopbackEdges: string[] = []
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    if (gatewayIds.has(f)) {
      const visited = new Set([t])
      const q = [t]
      let reaches = false
      while (q.length) {
        const nid = q.shift()!
        if (nid === f) { reaches = true; break }
        for (const nb of adj[nid] || []) {
          if (!visited.has(nb)) { visited.add(nb); q.push(nb) }
        }
      }
      if (reaches) {
        loopbackTargets.add(t)
        loopbackEdges.push(`${f}→${t}`)
      }
    }
  }
  console.debug('[layoutNodes] step3 - loopback edges:', loopbackEdges.length ? loopbackEdges.join(', ') : '(none)')
  console.debug('[layoutNodes] step3 - loopback targets:', [...loopbackTargets])

  // ── Step 4: Rebuild in-degree excluding loopback edges ──
  for (const n of nodes) inDeg[n.id] = 0
  const excludedEdges: string[] = []
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    const isLoopback = gatewayIds.has(f) && loopbackTargets.has(t)
    if (isLoopback) {
      excludedEdges.push(`${f}→${t}`)
      continue
    }
    if (inDeg[t] != null) inDeg[t]++
  }
  console.debug('[layoutNodes] step4 - excluded edges:', excludedEdges.length ? excludedEdges.join(', ') : '(none)')
  console.debug('[layoutNodes] step4 - final inDeg:', Object.entries(inDeg).map(([id, d]) => `${id}:${d}`).join(', '))

  // ── Step 5: BFS level assignment ──
  const level: Record<string, number> = {}
  const queue: string[] = []
  const bfsOrder: string[] = []
  for (const n of nodes) {
    if (inDeg[n.id] === 0) { level[n.id] = 0; queue.push(n.id) }
  }
  console.debug('[layoutNodes] step5 - BFS start queue (inDeg=0):', [...queue])
  let maxLevel = 0
  while (queue.length) {
    const id = queue.shift()!
    bfsOrder.push(id)
    if (!adj[id]) continue
    for (const next of adj[id]) {
      const lv = level[id] + 1
      if ((level[next] ?? Infinity) > lv) {
        level[next] = lv
        maxLevel = Math.max(maxLevel, lv)
        queue.push(next)
      }
    }
  }
  console.debug('[layoutNodes] step5 - BFS order:', bfsOrder.join(' → '))

  // ── Step 6: Fallback unassigned nodes ──
  const fallbackNodes: string[] = []
  for (const n of nodes) {
    if (level[n.id] == null) { level[n.id] = 0; fallbackNodes.push(n.id) }
  }
  if (fallbackNodes.length) {
    console.warn('[layoutNodes] step6 - nodes stuck (fell back to level 0):',
      fallbackNodes.map(id => {
        const nd = nodes.find(n => n.id === id)
        return `${id}(${nd?.node_type}, inDeg=${inDeg[id]})`
      }))
  }

  // ── Step 7: Per-node level summary ──
  console.debug('[layoutNodes] step7 - level map:', nodes.map(n => `${n.id}→L${level[n.id] ?? '?'}(${n.node_type})`).join(', '))
  console.debug('[layoutNodes] step7 - maxLevel:', maxLevel)

  // ── Step 8: Assign coordinates ──
  const layers: Record<number, string[]> = {}
  for (const n of nodes) {
    const lv = level[n.id]
    if (!layers[lv]) layers[lv] = []
    layers[lv].push(n.id)
  }

  const positions: Record<string, { x: number; y: number }> = {}
  for (let lv = 0; lv <= maxLevel; lv++) {
    const ids = layers[lv] || []
    const totalH = (ids.length - 1) * NODE_GAP
    ids.forEach((id, i) => {
      positions[id] = {
        x: START_X + lv * LAYER_GAP,
        y: START_Y + (totalH / 2) + i * NODE_GAP,
      }
    })
  }
  console.debug('[layoutNodes] step8 - positions:', Object.entries(positions).map(([id, p]) => `${id}@(${p.x},${p.y})`).join(', '))
  console.groupEnd()
  return positions
}
