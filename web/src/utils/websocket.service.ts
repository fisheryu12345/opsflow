/**
 * WebSocket 服务 — 统一连接管理与事件分发
 *
 * 单例模式，全应用共享一个 WebSocket 连接。
 * 组件通过 on(topic, handler) 订阅关心的消息 topic。
 *
 * 消息格式统一为 { topic, action, payload, timestamp }，
 * 兼容旧格式 { contentType, content, unread } 自动转换。
 */

import { ElNotification } from 'element-plus'
import { Session } from '/@/utils/storage'
import { getWsBaseURL } from '/@/utils/baseUrl'
import { useUserInfo } from '/@/stores/userInfo'

/** 心跳间隔（毫秒）— 30s，Daphne 自带 ping/pong 保活 */
const HEARTBEAT_INTERVAL = 30 * 1000
/** 最大重连次数 */
const MAX_RECONNECT = 3
/** 重连间隔（毫秒） */
const RECONNECT_INTERVAL = 5 * 1000

class WebSocketService {
  private ws: WebSocket | null = null
  private _isConnected = false
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectCount = 0
  private topics = new Map<string, Set<(msg: WsMessage) => void>>()

  /** 当前是否已连接 */
  get isConnected(): boolean {
    return this._isConnected
  }

  /** 订阅指定 topic 的消息 */
  on(topic: string, handler: (msg: WsMessage) => void): void {
    let handlers = this.topics.get(topic)
    if (!handlers) {
      handlers = new Set()
      this.topics.set(topic, handlers)
    }
    handlers.add(handler)
  }

  /** 取消订阅指定 topic 的消息 */
  off(topic: string, handler: (msg: WsMessage) => void): void {
    const handlers = this.topics.get(topic)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.topics.delete(topic)
      }
    }
  }

  /** 建立 WebSocket 连接 */
  connect(): void {
    if (this.ws) {
      return  // 已连接或正在连接
    }
    if (!('WebSocket' in window)) {
      ElNotification({ title: '提示', message: '浏览器不支持WebSocket', type: 'warning' })
      return
    }
    const token = Session.get('token')
    if (!token) {
      return
    }
    const wsUrl = `${getWsBaseURL()}ws/${token}/`
    this.ws = new WebSocket(wsUrl)
    this.ws.onmessage = this.onMessage
    this.ws.onclose = this.onClose
    this.ws.onopen = this.onOpen
    // onerror left empty — onclose fires after error, reconnect handles it
    this.ws.onerror = () => {}
  }

  /** 强制重连（手动触发） */
  reconnect(): void {
    this.disconnect()
    this.connect()
  }

  /** 断开 WebSocket 连接 */
  disconnect(): void {
    this.stopHeartbeat()
    this.clearReconnect()
    this.reconnectCount = 0
    if (this.ws) {
      this.ws.onclose = null  // prevent reconnect trigger
      this.ws.close()
      this.ws = null
    }
    this.setConnected(false)
  }

  // -- Private ---------------------------------------------------------------

  private onOpen = (): void => {
    this.setConnected(true)
    this.reconnectCount = 0  // 重置重连计数
    this.startHeartbeat()
  }

  private onClose = (): void => {
    this.setConnected(false)
    this.stopHeartbeat()
    this.ws = null
    this.scheduleReconnect()
  }

  private onMessage = (event: MessageEvent): void => {
    let data: any
    try {
      data = JSON.parse(event.data)
    } catch {
      return
    }

    // 统一消息格式：新格式 { topic, action, payload, timestamp }
    // 兼容旧格式 { contentType, content, unread }
    const msg: WsMessage = data.topic
      ? data  // 新格式
      : this.normalizeLegacyMessage(data)  // 旧格式转换

    if (!msg) return

    // 分发到订阅了对应 topic 的处理器
    const handlers = this.topics.get(msg.topic)
    if (handlers) {
      handlers.forEach(fn => fn(msg))
    }
  }

  /** 将旧 contentType 格式转换为统一信封格式 */
  private normalizeLegacyMessage(data: any): WsMessage | null {
    const { contentType, content, unread, sender } = data
    switch (contentType) {
      case 'SYSTEM':
        return {
          topic: 'notification',
          action: 'unread',
          payload: { unread, content, sender },
          timestamp: new Date().toISOString(),
        }
      case 'TEXT':
        return {
          topic: 'notification',
          action: 'info',
          payload: { content, unread, sender },
          timestamp: new Date().toISOString(),
        }
      case 'NODE_STATUS':
        return {
          topic: 'node_status',
          action: 'update',
          payload: content || {},
          timestamp: new Date().toISOString(),
        }
      default:
        return null
    }
  }

  /** 发送心跳 */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ token: Session.get('token') }))
      }
    }, HEARTBEAT_INTERVAL)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /** 调度自动重连 */
  private scheduleReconnect(): void {
    this.clearReconnect()
    if (this.reconnectCount >= MAX_RECONNECT) {
      return  // 超过最大重连次数
    }
    this.reconnectCount++
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, RECONNECT_INTERVAL)
  }

  private clearReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /** 同步连接状态到 Pinia */
  private setConnected(state: boolean): void {
    this._isConnected = state
    useUserInfo().setWebSocketState(state)
  }
}

/** 全局单例 */
const wsService = new WebSocketService()
export default wsService
