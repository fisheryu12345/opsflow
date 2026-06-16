package upgrade

import (
	"log/slog"
	"os"
	"path/filepath"
	"time"
)

// WatchConfig describes auto-upgrade watch configuration.
type WatchConfig struct {
	AutoUpgrade   bool          `json:"auto_upgrade"`
	CheckInterval time.Duration `json:"check_interval"`
	ServerURL     string        `json:"server_url"`
	CurrentVersion string       `json:"current_version"`
}

// Watcher periodically checks the server for new versions.
type Watcher struct {
	config     *WatchConfig
	upgrader   *UpgradeManager
	stopCh     chan struct{}
}

// NewWatcher creates a new upgrade watcher.
func NewWatcher(config *WatchConfig, upgrader *UpgradeManager) *Watcher {
	return &Watcher{
		config:   config,
		upgrader: upgrader,
		stopCh:   make(chan struct{}),
	}
}

// Start begins the periodic version check loop.
func (w *Watcher) Start() {
	if !w.config.AutoUpgrade {
		slog.Info("auto-upgrade disabled")
		return
	}

	ticker := time.NewTicker(w.config.CheckInterval)
	defer ticker.Stop()

	slog.Info("upgrade watcher started", "interval", w.config.CheckInterval)

	// Check immediately on start
	w.checkVersion()

	for {
		select {
		case <-w.stopCh:
			return
		case <-ticker.C:
			w.checkVersion()
		}
	}
}

// Stop stops the watcher.
func (w *Watcher) Stop() {
	close(w.stopCh)
}

func (w *Watcher) checkVersion() {
	// TODO: query server API for latest version
	// GET /api/v1/agents/versions/latest
	// response: { version, download_url, checksum }
	slog.Debug("checking for updates", "current", w.config.CurrentVersion)
}
