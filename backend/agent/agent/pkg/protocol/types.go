package protocol

// MessageType defines all message types in the Agent protocol.
type MessageType string

const (
	MsgCommand       MessageType = "command"
	MsgCommandResult MessageType = "command_result"
	MsgHeartbeat     MessageType = "heartbeat"
	MsgRegister      MessageType = "register"
	MsgRegisterAck   MessageType = "register_ack"
	MsgFilePush      MessageType = "file_push"
	MsgFilePull      MessageType = "file_pull"
	MsgFileProgress  MessageType = "file_progress"
	MsgCollect       MessageType = "collect"
	MsgCollectResult MessageType = "collect_result"
	MsgUpgrade       MessageType = "upgrade"
	MsgUpgradeAck    MessageType = "upgrade_ack"
	MsgGatewayRoute  MessageType = "gateway_route"
	MsgDisconnect    MessageType = "disconnect"
)

// Message is the unified message envelope for all Agent protocol messages.
type Message struct {
	Version   string          `json:"version"`
	MsgID     string          `json:"msg_id"`
	Type      MessageType     `json:"type"`
	Topic     string          `json:"topic"`
	Timestamp string          `json:"timestamp"`
	Source    string          `json:"source"` // server | agent | gateway
	Target    *Target         `json:"target,omitempty"`
	Body      any             `json:"body,omitempty"`
	TTL       int             `json:"ttl,omitempty"`
	TraceID   string          `json:"trace_id,omitempty"`
}

// Target identifies the recipient(s) of a message.
type Target struct {
	AgentID string   `json:"agent_id,omitempty"`
	BizID   string   `json:"biz_id,omitempty"`
	Hosts   []string `json:"hosts,omitempty"`
}

// CommandBody is the payload for MsgCommand.
type CommandBody struct {
	ExecID        string            `json:"exec_id"`
	Timeout       int               `json:"timeout"`
	ScriptType    string            `json:"script_type"` // shell | python | bat | powershell
	ScriptContent string            `json:"script_content"`
	ScriptParams  []string          `json:"script_params,omitempty"`
	EnvVars       map[string]string `json:"env_vars,omitempty"`
	WorkDir       string            `json:"work_dir,omitempty"`
	OutputLimit   int64             `json:"output_limit,omitempty"`
}

// CommandResultBody is the payload for MsgCommandResult (streaming).
type CommandResultBody struct {
	ExecID     string `json:"exec_id"`
	Seq        int    `json:"seq"`
	IsFinal    bool   `json:"is_final"`
	Stdout     string `json:"stdout,omitempty"`
	Stderr     string `json:"stderr,omitempty"`
	ExitCode   *int   `json:"exit_code,omitempty"`
	FinishTime int64  `json:"finish_time,omitempty"`
	Error      string `json:"error,omitempty"`
}

// HeartbeatBody is the payload for MsgHeartbeat.
type HeartbeatBody struct {
	AgentID     string         `json:"agent_id"`
	Hostname    string         `json:"hostname"`
	IP          string         `json:"ip"`
	Version     string         `json:"version"`
	Uptime      int64          `json:"uptime"`
	Load        []float64      `json:"load,omitempty"`
	MemoryUsage float64        `json:"memory_usage"`
	DiskUsage   map[string]float64 `json:"disk_usage,omitempty"`
	CPUCount    int            `json:"cpu_count"`
	Timestamp   int64          `json:"timestamp"`
}

// RegisterBody is the payload for MsgRegister.
type RegisterBody struct {
	AgentID     string `json:"agent_id"`
	Token       string `json:"token"`
	Hostname    string `json:"hostname"`
	IP          string `json:"ip"`
	OS          string `json:"os"`
	OSVersion   string `json:"os_version"`
	Arch        string `json:"arch"`
	Version     string `json:"version"`
	HostID      string `json:"host_id"`
}

// RegisterAckBody is the payload for MsgRegisterAck.
type RegisterAckBody struct {
	AgentID         string `json:"agent_id"`
	Accepted        bool   `json:"accepted"`
	HeartbeatInterval int   `json:"heartbeat_interval"`
	Message         string `json:"message,omitempty"`
}

// UpgradeBody is the payload for MsgUpgrade.
type UpgradeBody struct {
	UpgradeID        string `json:"upgrade_id"`
	DownloadURL      string `json:"download_url"`
	Checksum         string `json:"checksum"`
	Version          string `json:"version"`
	Timeout          int    `json:"timeout"`
	RollbackVersion  string `json:"rollback_version"`
	RollbackChecksum string `json:"rollback_checksum"`
}

// UpgradeAckBody is the payload for MsgUpgradeAck.
type UpgradeAckBody struct {
	UpgradeID string `json:"upgrade_id"`
	Success   bool   `json:"success"`
	Version   string `json:"version"`
	Message   string `json:"message,omitempty"`
}

// FilePushBody is the payload for MsgFilePush.
type FilePushBody struct {
	FileTaskID string `json:"file_task_id"`
	FileName   string `json:"file_name"`
	FileSize   int64  `json:"file_size"`
	FileHash   string `json:"file_hash"`
	ChunkSize  int    `json:"chunk_size"`
	ChunkCount int    `json:"chunk_count"`
	TargetPath string `json:"target_path"`
	DownloadURL string `json:"download_url"`
}

// FileProgressBody is the payload for MsgFileProgress.
type FileProgressBody struct {
	FileTaskID string `json:"file_task_id"`
	Progress   int    `json:"progress"` // 0-100
	Status     string `json:"status"`   // transferring | success | failed
	Message    string `json:"message,omitempty"`
}

// CollectResultBody is the payload for MsgCollectResult.
type CollectResultBody struct {
	AgentID     string `json:"agent_id"`
	CollectType string `json:"collect_type"` // host_info | process | disk | network | package
	Data        any    `json:"data"`
	Timestamp   int64  `json:"timestamp"`
}

// ── Process Management Types ──────────────────────────────────────

const (
	MsgCollectProcess    MessageType = "collect_process"
	MsgProcessControl    MessageType = "process_control"
	MsgProcessCtrlResult MessageType = "process_control_result"
)

// ── App Registry Types ────────────────────────────────────────────

const (
	MsgAppRegister   MessageType = "app_register"
	MsgAppUnregister MessageType = "app_unregister"
	MsgAppList       MessageType = "app_list"
	MsgAppListResult MessageType = "app_list_result"
)

// AppRegisterBody is the payload for MsgAppRegister.
type AppRegisterBody struct {
	Name        string `json:"name"`
	Command     string `json:"command"`
	User        string `json:"user,omitempty"`
	StopCommand string `json:"stop_command,omitempty"`
	PIDFile     string `json:"pid_file,omitempty"`
	AutoRestart bool   `json:"auto_restart"`
}

// AppUnregisterBody is the payload for MsgAppUnregister.
type AppUnregisterBody struct {
	Name string `json:"name"`
}

// AppListBody is the response for MsgAppListResult.
type AppListBody struct {
	Apps     []AppEntryInfo `json:"apps"`
}

// AppEntryInfo is a single registered app in list responses.
type AppEntryInfo struct {
	Name        string `json:"name"`
	Command     string `json:"command"`
	User        string `json:"user,omitempty"`
	StopCommand string `json:"stop_command,omitempty"`
	PIDFile     string `json:"pid_file,omitempty"`
	AutoRestart bool   `json:"auto_restart"`
	Running     bool   `json:"running"`
	PID         int    `json:"pid,omitempty"`
}

// ── SetConfig Types ────────────────────────────────────────────

const MsgSetConfig MessageType = "set_config"

type SetConfigBody struct {
	AppUsers []string `json:"app_users,omitempty"`
}

// ProcessCollectBody is the payload for MsgCollectResult (collect_type="process").
type ProcessCollectBody struct {
	AgentID     string         `json:"agent_id"`
	CollectType string         `json:"collect_type"`
	Processes   []ProcessInfo  `json:"processes,omitempty"`
	Services    []ServiceInfo  `json:"services,omitempty"`
	Connections []NetConn      `json:"connections,omitempty"`
	Timestamp   int64          `json:"timestamp"`
}

// ProcessInfo represents a single running process.
type ProcessInfo struct {
	PID         int          `json:"pid"`
	Name        string       `json:"name"`
	User        string       `json:"user"`
	Cmdline     string       `json:"cmdline"`
	CPUPercent  float64      `json:"cpu_percent"`
	MemoryMB    float64      `json:"memory_mb"`
	Status      string       `json:"status"`
	ListenAddrs []ListenAddr `json:"listen_addrs,omitempty"`
	Source      string       `json:"source"`           // systemd|agent|discovery
	Registered  bool         `json:"registered"`
	ServiceUnit string       `json:"service_unit,omitempty"` // systemd unit name
}

// ListenAddr represents a TCP listen address.
type ListenAddr struct {
	IP       string `json:"ip"`
	Port     int    `json:"port"`
	Protocol string `json:"protocol"` // tcp/tcp6
}

// NetConn represents an active TCP connection.
type NetConn struct {
	PID        int    `json:"pid,omitempty"`    // Process PID from ss -tnp
	RemoteIP   string `json:"remote_ip"`
	RemotePort int    `json:"remote_port"`
	LocalPort  int    `json:"local_port"`
	Protocol   string `json:"protocol"` // tcp/tcp6
}

// ServiceInfo represents a systemd service unit.
type ServiceInfo struct {
	UnitName    string `json:"unit_name"`
	State       string `json:"state"`     // active/inactive/failed
	SubState    string `json:"sub_state"` // running/exited/dead
	MainPID     int    `json:"main_pid"`
	WorkerPIDs  []int  `json:"worker_pids,omitempty"`
	Enabled     bool   `json:"enabled"`
	Description string `json:"description"`
}

// ProcessControlBody is the payload for MsgProcessControl.
type ProcessControlBody struct {
	ControlID   string `json:"control_id"`
	Action      string `json:"action"`       // start|stop|restart|status
	ServiceName string `json:"service_name"` // systemd unit or app name
	PID         *int   `json:"pid,omitempty"`
	Force       bool   `json:"force,omitempty"`
	Timeout     int    `json:"timeout,omitempty"` // default 30s
}

// ProcessCtrlResultBody is the payload for MsgProcessCtrlResult.
type ProcessCtrlResultBody struct {
	ControlID string `json:"control_id"`
	Success   bool   `json:"success"`
	Action    string `json:"action"`
	Message   string `json:"message,omitempty"`
	PID       *int   `json:"pid,omitempty"`
	Status    string `json:"status,omitempty"` // running|stopped|not_found
}
