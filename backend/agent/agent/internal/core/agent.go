package core

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/internal/file"
	"opsflow/agent/agent/pkg/protocol"
)

// Agent represents the agent daemon running on managed hosts.
type Agent struct {
	cfg           *config.Config
	wsClient      *WSClient
	executor      *Executor
	collector     *Collector
	procCollector *ProcCollector
	procRegistry  *AppRegistry
	mu            sync.RWMutex
	agentID       string
	stopCh        chan struct{}
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
		a.agentID = generateHostID(a.cfg.Agent.DataDir)
		slog.Info("generated agent ID", "agent_id", a.agentID)
	}

	// Initialize WebSocket client
	a.wsClient = NewWSClient(a.cfg, a.agentID, a.handleMessage)
	a.executor = NewExecutor(a.wsClient)

	// Initialize app registry
	registryDir := a.cfg.Agent.DataDir + "/apps"
	a.procRegistry = NewAppRegistry(registryDir)

	// Start collectors if enabled
	if a.cfg.Collector.Enable {
		a.collector = NewCollector(a.cfg, a.wsClient, a.agentID)
		go a.collector.Start(ctx)

		a.procCollector = NewProcCollector(a.cfg, a.wsClient, a.procRegistry, a.agentID)
		go a.procCollector.Start(ctx)
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
	case protocol.MsgCollectProcess:
		if a.procCollector != nil {
			go a.procCollector.CollectNow()
		}
	case protocol.MsgProcessControl:
		a.handleProcessControl(msg)
	case protocol.MsgAppRegister:
		a.handleAppRegister(msg)
	case protocol.MsgSetConfig:
		a.handleSetConfig(msg)
	case protocol.MsgAppUnregister:
		a.handleAppUnregister(msg)
	case protocol.MsgAppList:
		a.handleAppList(msg)
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
func (a *Agent) handleSetConfig(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok {
		slog.Error("invalid set_config body")
		return
	}
	if appUsers, ok := body["app_users"].([]any); ok {
		users := make([]string, 0, len(appUsers))
		for _, v := range appUsers {
			if s, ok := v.(string); ok {
				users = append(users, s)
			}
		}
		if a.procCollector != nil {
			a.procCollector.UpdateAppUsers(users)
		}
		slog.Info("config updated", "app_users", len(users))
	}
}
func (a *Agent) handleProcessControl(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok {
		slog.Error("invalid process_control body")
		return
	}

	ctrl := &protocol.ProcessControlBody{
		ControlID:   getString(body, "control_id"),
		Action:      getString(body, "action"),
		ServiceName: getString(body, "service_name"),
		Force:       getBool(body, "force"),
		Timeout:     getInt(body, "timeout"),
	}
	if pid, ok := body["pid"].(float64); ok {
		pidInt := int(pid)
		ctrl.PID = &pidInt
	}

	if ctrl.Timeout <= 0 {
		ctrl.Timeout = 30
	}

	result := a.executeProcessControl(ctrl)

	if a.wsClient != nil {
		a.wsClient.SendJSON(protocol.NewProcessCtrlResult("agent", result))
	}
}

func (a *Agent) executeProcessControl(ctrl *protocol.ProcessControlBody) *protocol.ProcessCtrlResultBody {
	result := &protocol.ProcessCtrlResultBody{
		ControlID: ctrl.ControlID,
		Action:    ctrl.Action,
	}

	switch ctrl.Action {
	case "start":
		result.Success, result.Message, result.PID = a.startProcess(ctrl)
	case "stop":
		result.Success, result.Message = a.stopProcess(ctrl)
	case "restart":
		result.Success, result.Message, result.PID = a.restartProcess(ctrl)
	case "status":
		result.Success, result.Message, result.Status = a.statusProcess(ctrl)
	default:
		result.Message = fmt.Sprintf("unknown action: %s", ctrl.Action)
	}
	return result
}

func (a *Agent) startProcess(ctrl *protocol.ProcessControlBody) (bool, string, *int) {
	// Try systemctl first if service name looks like a unit
	if strings.Contains(ctrl.ServiceName, ".service") || exec.Command("systemctl", "is-enabled", ctrl.ServiceName, "--quiet").Run() == nil {
		out, err := exec.Command("systemctl", "start", ctrl.ServiceName).CombinedOutput()
		if err != nil {
			return false, fmt.Sprintf("systemctl start failed: %s", strings.TrimSpace(string(out))), nil
		}
		// Sleep 1s then verify
		time.Sleep(1 * time.Second)
		pid := a.getServicePID(ctrl.ServiceName)
		if pid > 0 {
			return true, "started", &pid
		}
		return false, "systemctl start reported success but process not found", nil
	}

	// Direct command (not systemd)
	cmd := exec.Command("sh", "-c", ctrl.ServiceName)
	if err := cmd.Start(); err != nil {
		return false, err.Error(), nil
	}
	pid := cmd.Process.Pid
	if a.procRegistry != nil {
		a.procRegistry.Register(fmt.Sprintf("app-%d", pid), ctrl.ServiceName, nil)
	}
	return true, "started", &pid
}

func (a *Agent) stopProcess(ctrl *protocol.ProcessControlBody) (bool, string) {
	if strings.Contains(ctrl.ServiceName, ".service") || exec.Command("systemctl", "is-enabled", ctrl.ServiceName, "--quiet").Run() == nil {
		cmd := exec.Command("systemctl", "stop", ctrl.ServiceName)
		if ctrl.Force {
			cmd = exec.Command("systemctl", "kill", "--signal=SIGKILL", ctrl.ServiceName)
		}
		out, err := cmd.CombinedOutput()
		if err != nil {
			return false, fmt.Sprintf("stop failed: %s", strings.TrimSpace(string(out)))
		}
		return true, "stopped"
	}

	// Kill by PID
	if ctrl.PID != nil {
		if a.procRegistry != nil && !a.procRegistry.IsRegisteredPID(*ctrl.PID) {
			return false, "PID not managed by this agent"
		}
		sig := "TERM"
		if ctrl.Force {
			sig = "KILL"
		}
		err := exec.Command("kill", fmt.Sprintf("-%s", sig), fmt.Sprintf("%d", *ctrl.PID)).Run()
		if err != nil {
			return false, fmt.Sprintf("kill failed: %s", err.Error())
		}
		return true, fmt.Sprintf("signal %s sent to PID %d", sig, *ctrl.PID)
	}
	return false, "no PID specified and not a systemd service"
}

func (a *Agent) restartProcess(ctrl *protocol.ProcessControlBody) (bool, string, *int) {
	// Stop
	if strings.Contains(ctrl.ServiceName, ".service") {
		exec.Command("systemctl", "restart", ctrl.ServiceName).Run()
		time.Sleep(1 * time.Second)
		pid := a.getServicePID(ctrl.ServiceName)
		return true, "restarted", &pid
	}
	return false, "restart only supported for systemd services", nil
}

func (a *Agent) statusProcess(ctrl *protocol.ProcessControlBody) (bool, string, string) {
	if ctrl.PID != nil {
		err := exec.Command("ps", "-p", fmt.Sprintf("%d", *ctrl.PID)).Run()
		if err == nil {
			return true, "running", "running"
		}
		return true, "stopped", "stopped"
	}
	out, err := exec.Command("systemctl", "is-active", ctrl.ServiceName).Output()
	if err != nil {
		return true, "stopped", "stopped"
	}
	return true, strings.TrimSpace(string(out)), strings.TrimSpace(string(out))
}

func (a *Agent) getServicePID(unit string) int {
	out, err := exec.Command("systemctl", "show", "-p", "MainPID", unit, "--no-pager").Output()
	if err != nil {
		return 0
	}
	line := strings.TrimSpace(string(out))
	parts := strings.SplitN(line, "=", 2)
	if len(parts) != 2 {
		return 0
	}
	pid, _ := strconv.Atoi(strings.TrimSpace(parts[1]))
	return pid
}

func getBool(m map[string]any, key string) bool {
	switch v := m[key].(type) {
	case bool:
		return v
	case string:
		return v == "true" || v == "1"
	default:
		return false
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
func (a *Agent) handleAppRegister(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok || a.procRegistry == nil {
		slog.Error("invalid app_register body or registry not available")
		return
	}
	name := getString(body, "name")
	command := getString(body, "command")
	if name == "" || command == "" {
		slog.Error("app_register: name and command required")
		return
	}
	opts := map[string]any{
		"user":         getString(body, "user"),
		"stop_command": getString(body, "stop_command"),
		"pid_file":     getString(body, "pid_file"),
		"auto_restart": getBool(body, "auto_restart"),
	}
	if err := a.procRegistry.Register(name, command, opts); err != nil {
		slog.Error("app_register failed", "name", name, "error", err)
		return
	}
	slog.Info("app registered", "name", name)
}

func (a *Agent) handleAppUnregister(msg *protocol.Message) {
	body, ok := msg.Body.(map[string]any)
	if !ok || a.procRegistry == nil {
		return
	}
	name := getString(body, "name")
	if name == "" {
		return
	}
	a.procRegistry.Unregister(name)
	slog.Info("app unregistered", "name", name)
}

func (a *Agent) handleAppList(msg *protocol.Message) {
	if a.procRegistry == nil || a.wsClient == nil {
		return
	}
	entries := a.procRegistry.List()
	apps := make([]protocol.AppEntryInfo, 0, len(entries))
	for _, e := range entries {
		pid := 0
		running := false
		// Try pidfile first
		pidFile := e.PIDFile
		if pidFile == "" {
			pidFile = fmt.Sprintf("/var/run/%s.pid", e.Name)
		}
		if data, err := os.ReadFile(pidFile); err == nil {
			if _, err := fmt.Sscanf(strings.TrimSpace(string(data)), "%d", &pid); err == nil && pid > 0 {
				if _, err := os.Stat(fmt.Sprintf("/proc/%d/status", pid)); err == nil {
					running = true
				}
			}
		}
		// Fallback: check via pgrep
		if !running && e.Name != "" {
			out, err := exec.Command("pgrep", "-x", e.Name).Output()
			if err == nil {
				lines := strings.Fields(string(out))
				if len(lines) > 0 {
					if p, err := strconv.Atoi(lines[0]); err == nil && p > 0 {
						pid = p
						running = true
					}
				}
			}
			// Also try matching without -x (for truncated names)
			if !running {
				out, err = exec.Command("pgrep", e.Name).Output()
				if err == nil {
					lines := strings.Fields(string(out))
					if len(lines) > 0 {
						if p, err := strconv.Atoi(lines[0]); err == nil && p > 0 {
							pid = p
							running = true
						}
					}
				}
			}
		}
		apps = append(apps, protocol.AppEntryInfo{
			Name:        e.Name,
			Command:     e.Command,
			User:        e.User,
			StopCommand: e.StopCommand,
			PIDFile:     e.PIDFile,
			AutoRestart: e.AutoRestart,
			Running:     running,
			PID:         pid,
		})
	}
	result := &protocol.AppListBody{Apps: apps}
	a.wsClient.SendJSON(protocol.NewAppListResult("agent", result))
}


// generateHostID creates a persistent machine identifier.
// First run: generate from hardware fingerprint, save to disk in dataDir.
// Subsequent runs: load from disk so agent_id never changes.
func generateHostID(dataDir string) string {
	if dataDir == "" {
		dataDir = "/var/lib/opsflow-agent"
	}
	idFile := dataDir + "/machine-id"

	// Try to load existing ID
	if data, err := os.ReadFile(idFile); err == nil && len(data) > 0 {
		return strings.TrimSpace(string(data))
	}

	// Generate from machine-id + MAC for stable fingerprint
	var fingerprint string
	if data, err := os.ReadFile("/etc/machine-id"); err == nil {
		fingerprint = strings.TrimSpace(string(data))
	} else if data, err := os.ReadFile("/var/lib/dbus/machine-id"); err == nil {
		fingerprint = strings.TrimSpace(string(data))
	} else {
		// Fallback: hostname + MAC
		hostname, _ := os.Hostname()
		fingerprint = fmt.Sprintf("%s-%d", hostname, time.Now().UnixNano())
	}

	// Append agent-specific suffix for uniqueness
	agentID := fmt.Sprintf("agent-%s", fingerprint)

	// Save to disk
	os.MkdirAll(dataDir, 0755)
	os.WriteFile(idFile, []byte(agentID), 0644)

	return agentID
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
