package core

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/pkg/protocol"
)

// ProcCollector collects process and service information from the host.
type ProcCollector struct {
	cfg      *config.Config
	wsClient *WSClient
	registry *AppRegistry
	ticker   *time.Ticker
	agentID  string
	appUsers map[string]bool
}

// NewProcCollector creates a new ProcCollector.
func NewProcCollector(cfg *config.Config, wsClient *WSClient, registry *AppRegistry, agentID string) *ProcCollector {
	appUsers := make(map[string]bool)
	for _, u := range cfg.Collector.AppUsers {
		appUsers[u] = true
	}
	return &ProcCollector{
		cfg:      cfg,
		wsClient: wsClient,
		registry: registry,
		agentID:  agentID,
		appUsers: appUsers,
	}
}

// UpdateAppUsers dynamically updates the app user whitelist.
func (c *ProcCollector) UpdateAppUsers(users []string) {
	newMap := make(map[string]bool)
	for _, u := range users {
		newMap[u] = true
	}
	c.appUsers = newMap
	slog.Info("app users updated", "count", len(users))
}

// Start begins the periodic process collection cycle.
func (c *ProcCollector) Start(ctx context.Context) {
	interval := c.cfg.Collector.Interval
	if interval <= 0 {
		interval = 300
	}
	c.ticker = time.NewTicker(time.Duration(interval) * time.Second)
	defer c.ticker.Stop()

	slog.Info("process collector started", "interval", interval)
	c.CollectNow()

	for {
		select {
		case <-ctx.Done():
			return
		case <-c.ticker.C:
			c.CollectNow()
		}
	}
}

// CollectNow triggers an immediate process collection cycle.
func (c *ProcCollector) CollectNow() {
	defer func() {
		if r := recover(); r != nil {
			slog.Error("process collector panic (recovered)", "panic", r)
		}
	}()
	body := c.Collect()
	if body != nil && c.wsClient != nil {
		msg := protocol.NewMessage(protocol.MsgCollectResult, "agent", body)
		c.wsClient.SendJSON(msg)
	}
}

// Collect runs a full process collection cycle.
func (c *ProcCollector) Collect() *protocol.ProcessCollectBody {
	procs := c.psAux()
	if procs == nil {
		return nil
	}

	c.ssListen(procs)
	svcs := c.systemctlList()

	for _, svc := range svcs {
		for i := range procs {
			if procs[i].PID == svc.MainPID {
				procs[i].Source = "systemd"
				procs[i].ServiceUnit = svc.UnitName
				procs[i].Registered = svc.State == "active"
				break
			}
		}
	}

	if c.registry != nil {
		for i := range procs {
			if c.registry.IsRegisteredPID(procs[i].PID) {
				procs[i].Source = "agent"
				procs[i].Registered = true
			}
		}
	}

	conns := c.extractConnections(procs)

	return &protocol.ProcessCollectBody{
		AgentID:     c.agentID,
		CollectType: "process",
		Processes:   procs,
		Services:    svcs,
		Connections: conns,
		Timestamp:   time.Now().Unix(),
	}
}

// psAux runs ps aux and returns parsed process info (no filtering).
func (c *ProcCollector) psAux() []protocol.ProcessInfo {
	out, err := exec.Command("ps", "aux").Output()
	if err != nil {
		out, err = exec.Command("ps", "-ef").Output()
		if err != nil {
			return nil
		}
	}

	scanner := bufio.NewScanner(bytes.NewReader(out))
	var procs []protocol.ProcessInfo
	lineNum := 0

	for scanner.Scan() {
		line := scanner.Text()
		lineNum++
		if lineNum == 1 {
			continue
		}

		fields := splitPSLine(line)
		if len(fields) < 11 {
			continue
		}

		pid, _ := strconv.Atoi(fields[1])
		if pid == 0 {
			continue
		}
		// App user whitelist: if configured, skip users not in the list
		if len(c.appUsers) > 0 && !c.appUsers[fields[0]] {
			continue
		}

		cpu, _ := strconv.ParseFloat(fields[2], 64)
		memKB, _ := strconv.ParseFloat(fields[4], 64)
		cmdline := truncateStr(strings.Join(fields[10:], " "), 200)

		status := "running"
		stat := strings.TrimSpace(fields[7])
		if stat == "Z" || stat == "Z+" {
			status = "zombie"
		} else if stat == "T" || stat == "T+" {
			status = "stopped"
		} else if stat == "D" || stat == "D+" {
			status = "sleeping"
		}

		name := extractProcessName(cmdline)

		procs = append(procs, protocol.ProcessInfo{
			PID:        pid,
			Name:       name,
			User:       fields[0],
			Cmdline:    cmdline,
			CPUPercent: cpu,
			MemoryMB:   memKB / 1024,
			Status:     status,
			Source:     "discovery",
			Registered: false,
		})
	}
	return procs
}

// ssListen runs ss -tlnp, attaches listen addresses to matching processes.
func (c *ProcCollector) ssListen(procs []protocol.ProcessInfo) {
	out, err := exec.Command("ss", "-tlnp").Output()
	if err != nil {
		return
	}

	pidRe := regexp.MustCompile(`pid=(\d+)`)
	scanner := bufio.NewScanner(bytes.NewReader(out))

	for scanner.Scan() {
		line := scanner.Text()
		if !pidRe.MatchString(line) {
			continue
		}
		pidMatch := pidRe.FindStringSubmatch(line)
		pid, _ := strconv.Atoi(pidMatch[1])
		idx := findProcByPID(procs, pid)
		if idx < 0 {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 5 {
			continue
		}
		local := fields[3]
		proto := "tcp"
		if strings.HasPrefix(fields[0], "tcp6") {
			proto = "tcp6"
		}
		ip, portStr := splitAddr(local)
		port, _ := strconv.Atoi(portStr)
		if ip == "*" {
			ip = "0.0.0.0"
		}
		procs[idx].ListenAddrs = append(procs[idx].ListenAddrs, protocol.ListenAddr{IP: ip, Port: port, Protocol: proto})
	}
}

// extractConnections extracts active TCP connections from ss -tnp.
func (c *ProcCollector) extractConnections(_ []protocol.ProcessInfo) []protocol.NetConn {
	out, err := exec.Command("ss", "-tnp").Output()
	if err != nil {
		return nil
	}
	pidRe := regexp.MustCompile(`pid=(\d+)`)
	scanner := bufio.NewScanner(bytes.NewReader(out))
	var conns []protocol.NetConn
	for scanner.Scan() {
		line := scanner.Text()
		pidMatch := pidRe.FindStringSubmatch(line)
		if pidMatch == nil {
			continue
		}
		pid, _ := strconv.Atoi(pidMatch[1])
		fields := strings.Fields(line)
		if len(fields) < 5 {
			continue
		}
		_, locPortStr := splitAddr(fields[3])
		remIP, remPortStr := splitAddr(fields[4])
		locPort, _ := strconv.Atoi(locPortStr)
		remPort, _ := strconv.Atoi(remPortStr)
		proto := "tcp"
		if strings.HasPrefix(fields[0], "tcp6") {
			proto = "tcp6"
		}
		conns = append(conns, protocol.NetConn{PID: pid, RemoteIP: remIP, RemotePort: remPort, LocalPort: locPort, Protocol: proto})
	}
	return conns
}

// systemctlList runs systemctl list-units and returns parsed services.
func (c *ProcCollector) systemctlList() []protocol.ServiceInfo {
	out, err := exec.Command("systemctl", "list-units", "--type=service", "--no-pager", "--no-legend").Output()
	if err != nil {
		return nil
	}
	scanner := bufio.NewScanner(bytes.NewReader(out))
	var svcs []protocol.ServiceInfo
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 4 {
			continue
		}
		unitName := fields[0]
		if !strings.HasSuffix(unitName, ".service") {
			continue
		}
		svcs = append(svcs, protocol.ServiceInfo{
			UnitName:    unitName,
			State:       fields[2],
			SubState:    fields[3],
			MainPID:     c.getServiceMainPID(unitName),
			WorkerPIDs:  c.getServiceWorkerPIDs(unitName),
			Enabled:     c.isServiceEnabled(unitName),
			Description: strings.Join(fields[4:], " "),
		})
	}
	return svcs
}

func (c *ProcCollector) getServiceMainPID(unit string) int {
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

func (c *ProcCollector) getServiceWorkerPIDs(unit string) []int {
	cgOut, err := exec.Command("find", fmt.Sprintf("/sys/fs/cgroup/system.slice/%s/", unit), "-name", "cgroup.procs", "-exec", "cat", "{}", "+").Output()
	if err != nil {
		return nil
	}
	pids := parsePIDList(string(cgOut))
	if len(pids) == 0 {
		return nil
	}
	mainPID := c.getServiceMainPID(unit)
	var workers []int
	for _, p := range pids {
		if p != mainPID && p > 0 {
			workers = append(workers, p)
		}
	}
	return workers
}

func parsePIDList(output string) []int {
	lines := strings.Fields(output)
	var pids []int
	for _, line := range lines {
		pid, err := strconv.Atoi(strings.TrimSpace(line))
		if err == nil && pid > 0 {
			pids = append(pids, pid)
		}
	}
	return pids
}

func (c *ProcCollector) isServiceEnabled(unit string) bool {
	return exec.Command("systemctl", "is-enabled", unit, "--no-pager", "--quiet").Run() == nil
}

// ── Helpers ──

func truncateStr(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}

func splitPSLine(line string) []string {
	var result []string
	var current strings.Builder
	inSpace := true
	for _, ch := range line {
		if ch == ' ' || ch == '\t' {
			if !inSpace {
				result = append(result, current.String())
				current.Reset()
			}
			inSpace = true
		} else {
			current.WriteRune(ch)
			inSpace = false
		}
	}
	if current.Len() > 0 {
		result = append(result, current.String())
	}
	return result
}

func splitAddr(addr string) (string, string) {
	if len(addr) == 0 {
		return "", "0"
	}
	if addr[0] == '[' {
		closeBracket := strings.LastIndex(addr, "]")
		if closeBracket > 0 && closeBracket+1 < len(addr) && addr[closeBracket+1] == ':' {
			return addr[1:closeBracket], addr[closeBracket+2:]
		}
	}
	idx := strings.LastIndex(addr, ":")
	if idx < 0 {
		return addr, "0"
	}
	return addr[:idx], addr[idx+1:]
}

func findProcByPID(procs []protocol.ProcessInfo, pid int) int {
	for i, p := range procs {
		if p.PID == pid {
			return i
		}
	}
	return -1
}

func extractProcessName(cmdline string) string {
	parts := strings.Fields(cmdline)
	if len(parts) == 0 {
		return "unknown"
	}
	name := parts[0]
	if idx := strings.LastIndex(name, "/"); idx >= 0 {
		name = name[idx+1:]
	}
	name = strings.TrimRight(name, ":")
	if len(name) > 64 {
		name = name[:64]
	}
	return name
}
