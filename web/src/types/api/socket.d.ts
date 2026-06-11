/**
 * WebSocket 统一消息类型定义
 *
 * 所有 WebSocket 消息使用统一的 topic/action/payload/timestamp 格式。
 * 与后端 application/ws_push.py 中 _build_message() 保持一致。
 */

/** WebSocket 统一消息信封 */
interface WsMessage {
  topic: string;
  action: string;
  payload: Record<string, any>;
  timestamp: string;
}

/** WebSocket 服务实例接口 */
interface WebSocketServiceInstance {
  /** 订阅指定 topic 的消息 */
  on(topic: string, handler: (msg: WsMessage) => void): void;
  /** 取消订阅指定 topic 的消息 */
  off(topic: string, handler: (msg: WsMessage) => void): void;
  /** 建立 WebSocket 连接 */
  connect(): void;
  /** 断开 WebSocket 连接 */
  disconnect(): void;
  /** 当前连接状态 */
  readonly isConnected: boolean;
}
