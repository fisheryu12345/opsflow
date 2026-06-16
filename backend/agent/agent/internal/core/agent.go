package core

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/internal/file"
	"opsflow/agent/agent/pkg/protocol"
)

// Agent represents the agent daemon running on managed hosts.
type Agent struct {
	cfg       *config.Config
	wsClient  *WSClient
	executor  *Executor
	collector *Collector
	mu        sync.RWMutex
	agentID   string
	stopCh    chan struct{}
}

// NewAgent creates a new Agent instance.
func NewAgent(cfg *config.Config) *Agent {
	return &Agent{
		cfg:    cfg,
		stopCh: make(chan struct{}),
	}
}

// Start starts the agent and connects to the server.
func (a *Agent) Start(ctx context.Context) error {
	a.agentID = a.cfg.Agent.AgentID
	if a.agentID == "" {
		a.agentID = generateHostID()
		slog.Info("generated agent ID", "agent_id", a.agentID)
	}

	// Initialize WebSocket client
	a.wsClient = NewWSClient(a.cfg, a.agentID, a.handleMessage)
	a.executor = NewExecutor(a.wsClient)

	// Start collector if enabled
	if a.cfg.Collector.Enable {
		a.collector = NewCollector(a.cfg, a.wsClient)
		go a.collector.Start(ctx)
	}

	// Start WebSocket connection (blocking with auto-reconnect)
	go a.wsClient.Connect(ctx)

	slog.Info("agent started",
		"agent_id", a.agentID,
		"endpoint", a.cfg.Server.Endpoint,
		"collector_enabled", a.cfg.Collector.Enable,
	)
	return nil
}

// Stop gracefully shuts down the agent.
func (a *Agent) Stop() {
	close(a.stopCh)
	if a.wsClient != nil {
		a.wsClient.Close()
	}
	slog.Info("agent stopped")
}

// handleMessage dispatches incoming messages based on their type.
func (a *Agent) handleMessage(msg *protocol.Message) {
	slog.Debug("received message", "type", msg.Type, "msg_id", msg.MsgID)

	switch msg.Type {
	case protocol.MsgCommand:
		a.handleCommand(msg)
	case protocol.MsgFilePush:
		a.handleFilePush(msg)
	case protocol.MsgCollect:
		a.handleCollect(msg)
	case protocol.MsgUpgrade:
		a.handleUpgrade(msg)
	case protocol.MsgRegisterAck:
		a.handleRegisterAck(msg)
	case protocol.MsgDisconnect:
		a.handleDisconnect(msg)
	default:
		slog.Warn("unknown message type", "type", msg.Type)
	}
}

func (a *Agent) handleCommand(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok {
		slog.Error("invalid command body")
		return
	}

	// Parse body into CommandBody
	cmdBody := &protocol.CommandBody{
		ExecID:        getString(body, "exec_id"),
		Timeout:       getInt(body, "timeout"),
		ScriptType:    getString(body, "script_type"),
		ScriptContent: getString(body, "script_content"),
		WorkDir:       getString(body, "work_dir"),
	}
	cmdBody.ScriptParams = getStringSlice(body, "script_params")
	if env, ok := body["env_vars"].(map[string]any); ok {
		cmdBody.EnvVars = make(map[string]string)
		for k, v := range env {
			cmdBody.EnvVars[k] = fmt.Sprint(v)
		}
	}

	if a.executor != nil {
		go a.executor.Execute(cmdBody)
	}
}

func (a *Agent) handleFilePush(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok {
		slog.Error("invalid file_push body")
		return
	}
	task := &file.FileTask{
		FileTaskID:  getString(body, "file_task_id"),
		FileName:    getString(body, "file_name"),
		FileSize:    getInt64(body, "file_size"),
		FileHash:    getString(body, "file_hash"),
		ChunkSize:   getInt(body, "chunk_size"),
		ChunkCount:  getInt(body, "chunk_count"),
		TargetPath:  getString(body, "target_path"),
		DownloadURL: getString(body, "download_url"),
	}

	slog.Info("file push received, downloading", "task_id", task.FileTaskID, "file", task.FileName, "chunks", task.ChunkCount)

	workDir := a.cfg.Agent.DataDir
	if workDir == "" {
		workDir = "/tmp"
	}

	downloader := file.NewDownloader(workDir)
	if err := downloader.DownloadFile(task); err != nil {
		slog.Error("file download failed", "task_id", task.FileTaskID, "error", err)
		if a.wsClient != nil {
			a.wsClient.SendJSON(protocol.NewMessage(protocol.MsgFileProgress, "agent", map[string]any{
				"file_task_id": task.FileTaskID,
				"status":       "failed",
				"progress":     0,
				"message":      err.Error(),
			}))
		}
		return
	}

	slog.Info("file download complete", "task_id", task.FileTaskID, "path", task.TargetPath)
	if a.wsClient != nil {
		a.wsClient.SendJSON(protocol.NewMessage(protocol.MsgFileProgress, "agent", map[string]any{
			"file_task_id": task.FileTaskID,
			"status":       "success",
			"progress":     100,
		}))
	}
}

func (a *Agent) handleCollect(msg *protocol.Message) {
	if a.collector != nil {
		go a.collector.CollectNow()
	}
}

func (a *Agent) handleUpgrade(msg *protocol.Message) {
	slog.Info("upgrade request received", "msg_id", msg.MsgID)
	// TODO: Phase 3 - upgrade implementation
}

func (a *Agent) handleRegisterAck(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok {
		return
	}
	if interval, ok := body["heartbeat_interval"].(float64); ok {
		a.wsClient.UpdateHeartbeatInterval(int(interval))
		slog.Info("heartbeat interval updated", "interval", int(interval))
	}
}

func (a *Agent) handleDisconnect(msg *protocol.Message) {
	slog.Info("server requested disconnect")
	a.Stop()
}

// generateHostID creates a unique host identifier.
func generateHostID() string {
	return fmt.Sprintf("agent-%d", time.Now().UnixNano())
}

// Helper functions for type-safe map access.
func getString(m map[string]any, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func getInt64(m map[string]any, key string) int64 {
	switch v := m[key].(type) {
	case float64:
		return int64(v)
	case int64:
		return v
	case int:
		return int64(v)
	default:
		return 0
	}
}

func getInt(m map[string]any, key string) int {
	switch v := m[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	default:
		return 0
	}
}

func getStringSlice(m map[string]any, key string) []string {
	if v, ok := m[key].([]any); ok {
		result := make([]string, len(v))
		for i, item := range v {
			result[i] = fmt.Sprint(item)
		}
		return result
	}
	return nil
}
