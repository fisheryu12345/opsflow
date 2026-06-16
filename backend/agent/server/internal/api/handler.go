package api

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"opsflow/agent/server/internal/file"
	"opsflow/agent/server/internal/ws"
)

// newMsgID generates a unique message ID.
func newMsgID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}

// Handler provides REST API endpoints for Django to forward commands.
type Handler struct {
	wsServer    *ws.Server
	fileCoord   *file.Coordinator
	chunkHandler http.HandlerFunc
}

// NewHandler creates a new REST API handler.
func NewHandler(wsServer *ws.Server, fileCoord *file.Coordinator, chunkHandler http.HandlerFunc) *Handler {
	return &Handler{
		wsServer:    wsServer,
		fileCoord:   fileCoord,
		chunkHandler: chunkHandler,
	}
}

// Router returns the HTTP handler with all routes registered.
func (h *Handler) Router() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/tasks/exec", h.handleExec)
	mux.HandleFunc("/api/v1/files/push", h.handleFilePush)
	mux.HandleFunc("/chunks/", h.chunkHandler)
	mux.HandleFunc("/health", h.handleHealth)
	return mux
}

func (h *Handler) handleExec(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		AgentID       string `json:"agent_id"`
		ExecID        string `json:"exec_id"`
		ScriptType    string `json:"script_type"`
		ScriptContent string `json:"script_content"`
		Timeout       int    `json:"timeout"`
		TargetHost    string `json:"target_host"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"invalid body: %s"}`, err), http.StatusBadRequest)
		return
	}

	slog.Info("received exec request", "agent_id", req.AgentID, "exec_id", req.ExecID)

	agent := h.wsServer.GetAgent(req.AgentID)
	if agent == nil {
		agent = h.wsServer.GetAgentByHost(req.TargetHost)
	}
	if agent == nil || !agent.Connected() {
		slog.Warn("agent not connected", "agent_id", req.AgentID)
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]any{
			"success": false, "exec_id": req.ExecID,
			"status": "offline", "error": "agent not connected",
		})
		return
	}

	msg := map[string]any{
		"version":   "1.0",
		"msg_id":    newMsgID(),
		"type":      "command",
		"topic":     "agent:*",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"source":    "server",
		"target":    map[string]any{"agent_id": req.AgentID},
		"body": map[string]any{
			"exec_id":        req.ExecID,
			"timeout":        req.Timeout,
			"script_type":    req.ScriptType,
			"script_content": req.ScriptContent,
		},
		"ttl": 300,
	}

	if err := agent.SendJSON(msg); err != nil {
		slog.Error("send command failed", "agent_id", req.AgentID, "error", err)
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]any{
			"success": false, "exec_id": req.ExecID,
			"status": "error", "error": err.Error(),
		})
		return
	}

	slog.Info("command sent to agent", "agent_id", req.AgentID, "exec_id", req.ExecID)
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]any{
		"success": true, "exec_id": req.ExecID, "status": "sent",
	})
}

func (h *Handler) handleFilePush(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	task := &file.PushTask{}
	if err := json.NewDecoder(r.Body).Decode(task); err != nil {
		http.Error(w, fmt.Sprintf(`{"error":"invalid body: %s"}`, err), http.StatusBadRequest)
		return
	}

	slog.Info("file push request received", "task_id", task.FileTaskID, "target", task.TargetHost, "file", task.FileName)

	// Run coordinator asynchronously
	go func() {
		if err := h.fileCoord.HandlePush(task); err != nil {
			slog.Error("file push failed", "task_id", task.FileTaskID, "error", err)
		}
	}()

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]any{
		"success": true, "file_task_id": task.FileTaskID, "status": "processing",
	})
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]any{
		"status":       "ok",
		"agents_count": h.wsServer.GetAgentCount(),
	})
}
