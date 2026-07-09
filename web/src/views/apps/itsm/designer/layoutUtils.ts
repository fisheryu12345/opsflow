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

  const gatewayIds = new Set(nodes.filter(n => n.node_type === 'exclusive_gateway').map(n => n.id))
  const inDeg: Record<string, number> = {}
  const adj: Record<string, string[]> = {}
  for (const n of nodes) { inDeg[n.id] = 0; adj[n.id] = [] }
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    if (adj[f]) adj[f].push(t)
    if (inDeg[t] != null) inDeg[t]++
  }

  const loopbackTargets = new Set<string>()
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    if (gatewayIds.has(f)) {
      const visited = new Set([t])
      const q = [t]
      let reaches = false
      while (q.length) {
        const n = q.shift()!
        if (n === f) { reaches = true; break }
        for (const nb of adj[n] || []) {
          if (!visited.has(nb)) { visited.add(nb); q.push(nb) }
        }
      }
      if (reaches) loopbackTargets.add(t)
    }
  }

  for (const n of nodes) inDeg[n.id] = 0
  for (const e of edges) {
    const f = e.from || (e as any).source
    const t = e.to || (e as any).target
    const isLoopback = gatewayIds.has(f) && loopbackTargets.has(t)
    if (inDeg[t] != null && !isLoopback) inDeg[t]++
  }

  const level: Record<string, number> = {}
  const queue: string[] = []
  for (const n of nodes) {
    if (inDeg[n.id] === 0) { level[n.id] = 0; queue.push(n.id) }
  }
  let maxLevel = 0
  while (queue.length) {
    const id = queue.shift()!
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
  for (const n of nodes) {
    if (level[n.id] == null) level[n.id] = 0
  }

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
  return positions
}
