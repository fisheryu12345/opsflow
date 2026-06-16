package core

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/pkg/protocol"

	"github.com/gorilla/websocket"
)

// Gateway represents an agent gateway that proxies connections
// for agents in the same network segment to the central server.
type Gateway struct {
	cfg        *config.Config
	upstream   *WSClient
	localUpgrader websocket.Upgrader
	localAgents   map[string]*websocket.Conn
	mu            sync.RWMutex
	httpServer    *http.Server
	stopCh        chan struct{}
}

// NewGateway creates a new gateway.
func NewGateway(cfg *config.Config) *Gateway {
	return &Gateway{
		cfg: cfg,
		localUpgrader: websocket.Upgrader{
			ReadBufferSize:  4096,
			WriteBufferSize: 4096,
			CheckOrigin:     func(r *http.Request) bool { return true },
		},
		localAgents: make(map[string]*websocket.Conn),
		stopCh:      make(chan struct{}),
	}
}

// Start starts the gateway: connects upstream and listens locally.
func (g *Gateway) Start(ctx context.Context) error {
	slog.Info("gateway starting",
		"upstream", g.cfg.Server.Endpoint,
		"local_port", g.cfg.Agent.DataDir, // reuse data_dir for local port
	)

	// Connect to upstream server (reuses Agent WSClient logic)
	msgHandler := func(msg *protocol.Message) {
		g.handleUpstreamMessage(msg)
	}
	g.upstream = NewWSClient(g.cfg, fmt.Sprintf("gateway-%d", time.Now().UnixNano()), msgHandler)
	go g.upstream.Connect(ctx)

	// Start local WS listener for agents in this site
	addr := fmt.Sprintf(":%d", 18080) // gateway uses 18080 for local agents
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", g.handleLocalAgent)

	g.httpServer = &http.Server{Addr: addr, Handler: mux}
	slog.Info("gateway listening for local agents", "addr", addr)

	if err := g.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

// Stop shuts down the gateway.
func (g *Gateway) Stop() {
	if g.httpServer != nil {
		g.httpServer.Shutdown(context.Background())
	}
	if g.upstream != nil {
		g.upstream.Close()
	}
}

func (g *Gateway) handleLocalAgent(w http.ResponseWriter, r *http.Request) {
	conn, err := g.localUpgrader.Upgrade(w, r, nil)
	if err != nil {
		slog.Warn("local upgrade failed", "error", err)
		return
	}
	defer conn.Close()

	agentID := r.URL.Query().Get("agent_id")
	if agentID != "" {
		g.mu.Lock()
		g.localAgents[agentID] = conn
		g.mu.Unlock()
		defer func() {
			g.mu.Lock()
			delete(g.localAgents, agentID)
			g.mu.Unlock()
		}()
	}

	slog.Info("local agent connected", "agent_id", agentID)

	// Read loop: forward local agent messages upstream
	for {
		_, data, err := conn.ReadMessage()
		if err != nil {
			break
		}
		// Forward to upstream server
		if g.upstream != nil {
			var msg protocol.Message
			if err := json.Unmarshal(data, &msg); err == nil {
				g.upstream.SendJSON(&msg)
			}
		}
	}
}

func (g *Gateway) handleUpstreamMessage(msg *protocol.Message) {
	// Forward messages from upstream to the target local agent
	if msg.Target != nil && msg.Target.AgentID != "" {
		g.mu.RLock()
		conn, ok := g.localAgents[msg.Target.AgentID]
		g.mu.RUnlock()
		if ok {
			conn.WriteJSON(msg)
		}
	}
}
