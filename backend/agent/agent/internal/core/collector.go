package core

import (
	"bufio"
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/pkg/protocol"
)

// Collector collects host information for CMDB reporting.
// NOTE: Process collection is handled by ProcCollector (process_collector.go).
type Collector struct {
	cfg      *config.Config
	wsClient *WSClient
	ticker   *time.Ticker
	agentID  string
}

// NewCollector creates a new Collector.
func NewCollector(cfg *config.Config, wsClient *WSClient, agentID string) *Collector {
	return &Collector{
		cfg:      cfg,
		wsClient: wsClient,
		agentID:  agentID,
	}
}

// Start begins the periodic collection cycle.
func (c *Collector) Start(ctx context.Context) {
	c.ticker = time.NewTicker(time.Duration(c.cfg.Collector.Interval) * time.Second)
	defer c.ticker.Stop()

	slog.Info("collector started", "interval", c.cfg.Collector.Interval)

	// Collect immediately on start
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

// CollectNow triggers an immediate host_info collection cycle.
func (c *Collector) CollectNow() {
	hostInfo := c.collectHostInfo()
	if hostInfo == nil {
		slog.Warn("collector: hostInfo is nil")
		return
	}
	if c.wsClient == nil {
		slog.Warn("collector: wsClient is nil")
		return
	}
	msg := protocol.NewMessage(protocol.MsgCollectResult, "agent", hostInfo)
	c.wsClient.SendJSON(msg)
	slog.Info("collector: host_info sent", "hostname", hostInfo["hostname"], "os", hostInfo["os"], "cpu", hostInfo["cpu_count"])
}

// collectHostInfo gathers basic host information.
func (c *Collector) collectHostInfo() map[string]any {
	hostname, _ := os.Hostname()
	ip := getOutboundIP()
	memMB, diskGB := getSystemResources()
	osVersion := getOSVersion()
	return map[string]any{
		"agent_id":     c.agentID,
		"collect_type": "host_info",
		"hostname":     hostname,
		"ip":          ip,
		"os":          runtime.GOOS,
		"os_version":  osVersion,
		"arch":        runtime.GOARCH,
		"cpu_count":   runtime.NumCPU(),
		"memory_total": memMB,
		"disk_total":  diskGB,
		"go_version":  runtime.Version(),
		"timestamp":   time.Now().Unix(),
	}
}

// getOSVersion reads /etc/os-release or falls back to uname.
func getOSVersion() string {
	f, err := os.Open("/etc/os-release")
	if err != nil {
		// Fallback: try /etc/centos-release, /etc/redhat-release
		for _, p := range []string{"/etc/centos-release", "/etc/redhat-release", "/etc/debian_version"} {
			if data, err := os.ReadFile(p); err == nil {
				return strings.TrimSpace(string(data))
			}
		}
		return ""
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	versionID := ""
	prettyName := ""
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "VERSION_ID=") {
			versionID = strings.Trim(strings.TrimPrefix(line, "VERSION_ID="), "\"")
		}
		if strings.HasPrefix(line, "PRETTY_NAME=") {
			prettyName = strings.Trim(strings.TrimPrefix(line, "PRETTY_NAME="), "\"")
		}
	}
	if prettyName != "" {
		return prettyName
	}
	return versionID
}

// getSystemResources returns total memory (MB) and root disk (GB).
func getSystemResources() (int64, int64) {
	memKB := getMemTotalKB()
	diskGB := getRootDiskGB()
	return memKB / 1024, diskGB
}

func getMemTotalKB() int64 {
	f, err := os.Open("/proc/meminfo")
	if err != nil {
		return 0
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				var kb int64
				if _, err := fmt.Sscanf(fields[1], "%d", &kb); err == nil {
					return kb
				}
			}
		}
	}
	return 0
}

func getRootDiskGB() int64 {
	out, err := exec.Command("df", "-k", "--output=size", "/").Output()
	if err != nil {
		return 0
	}
	lines := strings.Fields(string(out))
	for _, f := range lines {
		kb, err := strconv.ParseInt(f, 10, 64)
		if err == nil && kb > 0 {
			return kb / 1024 / 1024
		}
	}
	return 0
}

// getOutboundIP gets the preferred outbound IP of this machine.
func getOutboundIP() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return ""
	}
	defer conn.Close()
	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP.String()
}
