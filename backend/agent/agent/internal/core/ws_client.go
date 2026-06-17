package core

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"sync"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/pkg/protocol"

	"github.com/gorilla/websocket"
)

// WSClient manages the WebSocket connection to the Agent Server.
type WSClient struct {
	cfg           *config.Config
	agentID       string
	conn          *websocket.Conn
	mu            sync.RWMutex
	msgHandler    func(*protocol.Message)
	heartbeatInterval int
	heartbeatTick *time.Ticker
	stopCh        chan struct{}
	writeCh       chan []byte
}

// NewWSClient creates a new WebSocket client.
func NewWSClient(cfg *config.Config, agentID string, handler func(*protocol.Message)) *WSClient {
	return &WSClient{
		cfg:           cfg,
		agentID:       agentID,
		msgHandler:    handler,
		heartbeatInterval: cfg.Heartbeat.Interval,
		stopCh:        make(chan struct{}),
		writeCh:       make(chan []byte, 100),
	}
}

// Connect establishes the WebSocket connection and starts read/write loops.
// Blocks on reconnect until context is cancelled.
func (c *WSClient) Connect(ctx context.Context) {
	backoff := 1 * time.Second
	maxBackoff := 60 * time.Second

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		slog.Info("connecting to server", "endpoint", c.cfg.Server.Endpoint)
		conn, _, err := websocket.DefaultDialer.Dial(c.cfg.Server.Endpoint, nil)
		if err != nil {
			slog.Warn("connection failed, retrying", "error", err, "backoff", backoff)
			time.Sleep(backoff)
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
			continue
		}
		backoff = 1 * time.Second

		c.mu.Lock()
		c.conn = conn
		c.mu.Unlock()

		slog.Info("connected to server")

		// Register with server
		c.register()

		// Start heartbeat
		c.startHeartbeat()

		// Start write pump
		go c.writePump(ctx)

		// Read pump (blocking)
		c.readPump(ctx)

		// Connection lost, cleanup and reconnect
		c.stopHeartbeat()
		c.mu.Lock()
		if c.conn != nil {
			c.conn.Close()
			c.conn = nil
		}
		c.mu.Unlock()
		slog.Warn("connection lost, reconnecting...")
	}
}

// SendJSON sends a JSON-encoded message to the server.
func (c *WSClient) SendJSON(msg *protocol.Message) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	select {
	case c.writeCh <- data:
	default:
		slog.Warn("write channel full, dropping message", "type", msg.Type)
	}
	return nil
}

// Close closes the WebSocket connection.
func (c *WSClient) Close() {
	close(c.stopCh)
	c.stopHeartbeat()
	c.mu.Lock()
	if c.conn != nil {
		c.conn.WriteMessage(websocket.CloseMessage, []byte{})
		c.conn.Close()
		c.conn = nil
	}
	c.mu.Unlock()
}

// UpdateHeartbeatInterval dynamically changes the heartbeat interval.
func (c *WSClient) UpdateHeartbeatInterval(interval int) {
	if interval < 5 {
		interval = 5
	}
	c.heartbeatInterval = interval
	c.stopHeartbeat()
	c.startHeartbeat()
}

func (c *WSClient) register() {
	body := &protocol.RegisterBody{
		AgentID:   c.agentID,
		Token:     c.cfg.Agent.Token,
		Hostname:  getHostname(),
		Version:   "1.0.0",
	}
	msg := protocol.NewRegister("agent", body)
	c.SendJSON(msg)
}

func (c *WSClient) startHeartbeat() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.heartbeatTick != nil {
		c.heartbeatTick.Stop()
	}
	c.heartbeatTick = time.NewTicker(time.Duration(c.heartbeatInterval) * time.Second)

	go func() {
		for range c.heartbeatTick.C {
			body := &protocol.HeartbeatBody{
				AgentID:   c.agentID,
				Timestamp: time.Now().Unix(),
			}
			msg := protocol.NewHeartbeat("agent", body)
			c.SendJSON(msg)
		}
	}()
}

func (c *WSClient) stopHeartbeat() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.heartbeatTick != nil {
		c.heartbeatTick.Stop()
		c.heartbeatTick = nil
	}
}

func (c *WSClient) readPump(ctx context.Context) {
	defer slog.Debug("read pump stopped")

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		c.mu.RLock()
		conn := c.conn
		c.mu.RUnlock()

		if conn == nil {
			return
		}

		_, data, err := conn.ReadMessage()
		if err != nil {
			slog.Warn("read error", "error", err)
			return
		}

		var msg protocol.Message
		if err := json.Unmarshal(data, &msg); err != nil {
			slog.Warn("unmarshal error", "error", err)
			continue
		}

		if c.msgHandler != nil {
			c.msgHandler(&msg)
		}
	}
}

func (c *WSClient) writePump(ctx context.Context) {
	defer slog.Debug("write pump stopped")

	for {
		select {
		case <-ctx.Done():
			return
		case data, ok := <-c.writeCh:
			if !ok {
				return
			}
			c.mu.RLock()
			conn := c.conn
			c.mu.RUnlock()
			if conn == nil {
				continue
			}
			if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
				slog.Warn("write error", "error", err)
			}
		}
	}
}

func getHostname() string {
	if hostname, err := os.Hostname(); err == nil {
		return hostname
	}
	return "unknown-host"
}
