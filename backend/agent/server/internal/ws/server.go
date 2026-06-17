package ws

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"opsflow/agent/server/internal/config"
	"opsflow/agent/server/internal/backend"

	"github.com/gorilla/websocket"
)

// AgentConn represents a connected agent.
type AgentConn struct {
	AgentID    string
	Conn       *websocket.Conn
	RemoteAddr string
	ConnectedAt time.Time
	LastHeartbeat time.Time
	Version    string
	Hostname   string
	IP         string
	OS         string
	OSVersion  string
	mu         sync.Mutex
}

// SendJSON sends a JSON message to this agent connection.
func (a *AgentConn) SendJSON(v any) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.Conn.WriteJSON(v)
}

// Server manages all WebSocket connections from agents.
type Server struct {
	cfg       *config.Config
	agents    map[string]*AgentConn // agent_id -> conn
	mu        sync.RWMutex
	upgrader  websocket.Upgrader
	httpServer *http.Server
	Backend   *backend.Client
}

// NewServer creates a new WebSocket server.
func NewServer(cfg *config.Config) *Server {
	return &Server{
		cfg:    cfg,
		agents: make(map[string]*AgentConn),
		upgrader: websocket.Upgrader{
			ReadBufferSize:  4096,
			WriteBufferSize: 4096,
			CheckOrigin:     func(r *http.Request) bool { return true },
		},
	}
}

// Start begins listening for WebSocket connections.
func (s *Server) Start(ctx context.Context) error {
	addr := fmt.Sprintf("%s:%d", s.cfg.WS.Host, s.cfg.WS.Port)

	mux := http.NewServeMux()
	mux.HandleFunc(s.cfg.WS.Path, s.handleWS)

	s.httpServer = &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	// Start heartbeat checker
	go s.heartbeatChecker(ctx)

	slog.Info("WS listener starting", "addr", addr, "path", s.cfg.WS.Path)

	// TODO: support TLS
	if s.cfg.Server.TLSCert != "" && s.cfg.Server.TLSKey != "" {
		return s.httpServer.ListenAndServeTLS(s.cfg.Server.TLSCert, s.cfg.Server.TLSKey)
	}
	return s.httpServer.ListenAndServe()
}

// Stop gracefully shuts down the server.
func (s *Server) Stop() {
	if s.httpServer != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		s.httpServer.Shutdown(ctx)
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	for id, conn := range s.agents {
		conn.Conn.Close()
		delete(s.agents, id)
	}
}

// GetAgent returns an agent connection by ID.
func (s *Server) GetAgent(agentID string) *AgentConn {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.agents[agentID]
}

// GetAgentCount returns the number of connected agents.
func (s *Server) GetAgentCount() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.agents)
}

// GetAgentByHost finds an agent connection by hostname or IP.
func (s *Server) GetAgentByHost(host string) *AgentConn {
	if host == "" {
		return nil
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, agent := range s.agents {
		if agent.Hostname == host || agent.IP == host {
			return agent
		}
	}
	return nil
}

// Connected returns true if the agent connection is active.
func (a *AgentConn) Connected() bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.Conn != nil
}

// Broadcast sends a message to all connected agents.
func (s *Server) Broadcast(v any) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, agent := range s.agents {
		agent.SendJSON(v)
	}
}

func (s *Server) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		slog.Warn("upgrade failed", "error", err)
		return
	}

	agentID := r.URL.Query().Get("agent_id")
	ac := &AgentConn{
		AgentID:    agentID,
		Conn:       conn,
		RemoteAddr: r.RemoteAddr,
		ConnectedAt: time.Now(),
		LastHeartbeat: time.Now(),
	}

	slog.Info("agent connected", "agent_id", agentID, "remote", r.RemoteAddr)

	if agentID != "" {
		s.mu.Lock()
		// Close existing connection if any
		if old, ok := s.agents[agentID]; ok {
			old.Conn.Close()
		}
		s.agents[agentID] = ac
		s.mu.Unlock()
	}

	defer func() {
		conn.Close()
		s.mu.Lock()
		if s.agents[agentID] == ac {
			delete(s.agents, agentID)
		}
		s.mu.Unlock()
		slog.Info("agent disconnected", "agent_id", agentID)
	}()

	// Read loop
	for {
		_, data, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				slog.Warn("unexpected close", "agent_id", agentID, "error", err)
			}
			break
		}

		// Parse message
		var msg struct {
			Type string `json:"type"`
		}
		if err := json.Unmarshal(data, &msg); err != nil {
			slog.Warn("parse error", "error", err)
			continue
		}

		// Update heartbeat on any message
		ac.LastHeartbeat = time.Now()

		// Route message to handler
		s.handleMessage(ac, msg.Type, data)
	}
}

func (s *Server) handleMessage(agent *AgentConn, msgType string, data []byte) {
	slog.Debug("message received", "agent_id", agent.AgentID, "type", msgType)

	switch msgType {
	case "register":
		s.handleRegister(agent, data)
	case "heartbeat":
		s.handleHeartbeat(agent, data)
	case "command_result":
		s.handleCommandResult(agent, data)
	case "collect_result":
		s.handleCollectResult(agent, data)
	default:
		slog.Warn("unknown message type", "type", msgType)
	}
}

func (s *Server) handleRegister(agent *AgentConn, data []byte) {
	var msg struct {
		Body struct {
			AgentID   string `json:"agent_id"`
			Token     string `json:"token"`
			Hostname  string `json:"hostname"`
			IP        string `json:"ip"`
			OS        string `json:"os"`
			OSVersion string `json:"os_version"`
			Version   string `json:"version"`
		} `json:"body"`
	}
	if err := json.Unmarshal(data, &msg); err != nil {
		slog.Warn("invalid register data", "error", err)
		return
	}

	body := msg.Body
	agent.AgentID = body.AgentID
	agent.Hostname = body.Hostname
	agent.IP = body.IP
	agent.OS = body.OS
	agent.OSVersion = body.OSVersion
	agent.Version = body.Version

	// Update registry with agent_id as key
	s.mu.Lock()
	if old, ok := s.agents[agent.AgentID]; ok && old != agent {
		old.Conn.Close()
	}
	s.agents[agent.AgentID] = agent
	s.mu.Unlock()

	slog.Info("agent registered",
		"agent_id", agent.AgentID,
		"hostname", agent.Hostname,
		"ip", agent.IP,
		"os", agent.OS,
		"version", agent.Version,
	)

	// Sync to Django
	go s.syncAgentToDjango(agent)

	// Send register ack
	ack := map[string]any{
		"type":    "register_ack",
		"msg_id":  fmt.Sprintf("ack-%d", time.Now().UnixNano()),
		"version": "1.0",
		"body": map[string]any{
			"agent_id":           agent.AgentID,
			"accepted":           true,
			"heartbeat_interval": s.cfg.WS.DefaultInterval,
		},
	}
	agent.SendJSON(ack)

	// TODO: notify Django about agent registration via async batch
}

func (s *Server) handleHeartbeat(agent *AgentConn, data []byte) {
	agent.LastHeartbeat = time.Now()
}

func (s *Server) handleCommandResult(agent *AgentConn, data []byte) {
	slog.Debug("command result received", "agent_id", agent.AgentID)

	// Parse the command result
	var msg struct {
		Body struct {
			ExecID   string `json:"exec_id"`
			Seq      int    `json:"seq"`
			IsFinal  bool   `json:"is_final"`
			Stdout   string `json:"stdout,omitempty"`
			Stderr   string `json:"stderr,omitempty"`
			ExitCode *int   `json:"exit_code,omitempty"`
			Error    string `json:"error,omitempty"`
		} `json:"body"`
	}
	if err := json.Unmarshal(data, &msg); err != nil {
		slog.Warn("invalid command_result", "error", err)
		return
	}

	body := msg.Body

	// Determine status
	status := "running"
	if body.IsFinal {
		if body.ExitCode != nil && *body.ExitCode == 0 {
			status = "success"
		} else {
			status = "failed"
		}
	}

	// Push to Django via backend client
	if s.Backend != nil {
		s.Backend.Push(&backend.BatchResult{
			ExecID:   body.ExecID,
			Status:   status,
			Seq:      body.Seq,
			IsFinal:  body.IsFinal,
			Stdout:   body.Stdout,
			Stderr:   body.Stderr,
			ExitCode: body.ExitCode,
			ErrorMsg: body.Error,
		})
		slog.Info("command result pushed to Django",
			"exec_id", body.ExecID, "seq", body.Seq, "final", body.IsFinal)
	}
}

func (s *Server) handleCollectResult(agent *AgentConn, data []byte) {
	client := &http.Client{Timeout: 5 * time.Second}
	req, err := http.NewRequest("POST",
		fmt.Sprintf("%s/api/agent/internal/collect_reports/", s.cfg.Django.BaseURL),
		bytes.NewReader(data),
	)
	if err != nil {
		slog.Debug("forward collect result failed", "agent_id", agent.AgentID, "error", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		slog.Debug("forward collect result failed", "agent_id", agent.AgentID, "error", err)
		return
	}
	resp.Body.Close()
	slog.Info("collect result forwarded to Django", "agent_id", agent.AgentID)
}

// heartbeatChecker periodically checks for stale connections.
func (s *Server) syncAgentToDjango(agent *AgentConn) {
	client := &http.Client{Timeout: 5 * time.Second}
	body := map[string]any{
		"agent_id":   agent.AgentID,
		"hostname":   agent.Hostname,
		"ip":         agent.IP,
		"os_type":    agent.OS,
		"os_version": agent.OSVersion,
		"arch":       "",
		"agent_version": agent.Version,
	}
	data, _ := json.Marshal(body)
	url := fmt.Sprintf("%s/api/agent/internal/register/", s.cfg.Django.BaseURL)
	req, err := http.NewRequest("POST", url, bytes.NewReader(data))
	if err != nil {
		slog.Debug("sync agent failed", "agent_id", agent.AgentID, "error", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		slog.Debug("sync agent failed", "agent_id", agent.AgentID, "error", err)
		return
	}
	resp.Body.Close()
	slog.Debug("agent synced to django", "agent_id", agent.AgentID)
}

func (s *Server) heartbeatChecker(ctx context.Context) {
	timeout := time.Duration(s.cfg.WS.HeartbeatCheck) * time.Second
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.mu.Lock()
			for id, agent := range s.agents {
				if time.Since(agent.LastHeartbeat) > timeout {
					slog.Warn("agent heartbeat timeout", "agent_id", id)
					agent.Conn.Close()
					delete(s.agents, id)
				}
			}
			s.mu.Unlock()
		}
	}
}
