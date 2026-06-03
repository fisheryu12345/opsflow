import { ref, onBeforeUnmount } from 'vue'

export function useMonitor() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const nodeStatuses = ref<Record<string, string>>({})
  const executionStatus = ref<string>('')

  function connect(executionId: number) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/opsflow/execution/${executionId}/`

    const socket = new WebSocket(url)
    socket.onopen = () => { connected.value = true }
    socket.onclose = () => { connected.value = false }
    socket.onerror = () => { connected.value = false }
    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'node_status') {
          nodeStatuses.value[msg.node_id] = msg.status
        } else if (msg.type === 'execution_completed') {
          executionStatus.value = msg.status
          // 不断开 WS：保留连接以接收可能延迟到达的节点状态消息
          //（Celery 通知 vs 前端 execution_completed 的时序竞争）
          // 用户离开页面时 onBeforeUnmount → disconnect() 会清理连接
        } else if (msg.type === 'init_state') {
          if (msg.data.node_status) {
            nodeStatuses.value = { ...msg.data.node_status }
          }
          executionStatus.value = msg.data.status
        }
      } catch (e) {
        console.error('WebSocket 消息解析失败', e)
      }
    }

    ws.value = socket
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  function send(data: any) {
    if (ws.value && connected.value) {
      ws.value.send(JSON.stringify(data))
    }
  }

  function getNodeColor(status: string): string {
    switch (status) {
      case 'completed': return '#67C23A'
      case 'running': return '#E6A23C'
      case 'failed': return '#F56C6C'
      case 'pending': return '#909399'
      case 'skipped': return '#C0C4CC'
      case 'pending_approval': return '#9B59B6'
      default: return '#909399'
    }
  }

  onBeforeUnmount(() => disconnect())

  return {
    ws, connected, nodeStatuses, executionStatus,
    connect, disconnect, send, getNodeColor,
  }
}
