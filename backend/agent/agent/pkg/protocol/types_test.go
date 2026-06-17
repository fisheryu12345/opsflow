package protocol

import (
	"encoding/json"
	"testing"
)

func TestProcessCollectBody(t *testing.T) {
	body := ProcessCollectBody{
		CollectType: "process",
		Processes: []ProcessInfo{
			{PID: 1001, Name: "nginx", User: "root", Status: "running", Source: "systemd", ServiceUnit: "nginx.service"},
		},
		Services: []ServiceInfo{
			{UnitName: "nginx.service", State: "active", MainPID: 1001, Enabled: true},
		},
		Connections: []NetConn{
			{RemoteIP: "10.0.1.2", RemotePort: 3306, LocalPort: 54321, Protocol: "tcp"},
		},
		Timestamp: 1234567890,
	}

	data, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	var decoded ProcessCollectBody
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if len(decoded.Processes) != 1 || decoded.Processes[0].PID != 1001 {
		t.Fatalf("process round-trip failed: %+v", decoded.Processes)
	}
	if decoded.Services[0].UnitName != "nginx.service" {
		t.Fatalf("service round-trip failed")
	}
	if decoded.Connections[0].RemotePort != 3306 {
		t.Fatalf("connection round-trip failed")
	}
	t.Logf("ProcessCollectBody round-trip OK (%d bytes)", len(data))
}

func TestProcessControlBody(t *testing.T) {
	body := ProcessControlBody{
		ControlID:   "ctrl-001",
		Action:      "start",
		ServiceName: "nginx.service",
		Timeout:     30,
	}

	data, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	var decoded ProcessControlBody
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if decoded.Action != "start" || decoded.ServiceName != "nginx.service" {
		t.Fatalf("control body round-trip failed")
	}
	t.Logf("ProcessControlBody round-trip OK (%d bytes)", len(data))
}

func TestProcessCtrlResultBody(t *testing.T) {
	pid := 1234
	body := ProcessCtrlResultBody{
		ControlID: "ctrl-001",
		Success:   true,
		Action:    "start",
		Message:   "started",
		PID:       &pid,
	}

	data, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	var decoded ProcessCtrlResultBody
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if !decoded.Success || *decoded.PID != 1234 {
		t.Fatalf("result body round-trip failed")
	}
	t.Logf("ProcessCtrlResultBody round-trip OK (%d bytes)", len(data))
}
