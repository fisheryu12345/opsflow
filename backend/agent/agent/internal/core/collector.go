package core

import (
	"context"
	"log/slog"
	"runtime"
	"time"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/pkg/protocol"
)

// Collector collects host information for CMDB reporting.
type Collector struct {
	cfg      *config.Config
	wsClient *WSClient
	ticker   *time.Ticker
}

// NewCollector creates a new Collector.
func NewCollector(cfg *config.Config, wsClient *WSClient) *Collector {
	return &Collector{
		cfg:      cfg,
		wsClient: wsClient,
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

// CollectNow triggers an immediate collection cycle.
func (c *Collector) CollectNow() {
	hostInfo := c.collectHostInfo()
	if hostInfo != nil && c.wsClient != nil {
		msg := protocol.NewMessage(protocol.MsgCollectResult, "agent", hostInfo)
		c.wsClient.SendJSON(msg)
	}
}

// collectHostInfo gathers basic host information.
func (c *Collector) collectHostInfo() map[string]any {
	return map[string]any{
		"collect_type": "host_info",
		"os":          runtime.GOOS,
		"arch":        runtime.GOARCH,
		"cpu_count":   runtime.NumCPU(),
		"go_version":  runtime.Version(),
		"timestamp":   time.Now().Unix(),
	}
}
