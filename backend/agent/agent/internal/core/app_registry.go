package core

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
)

// AppEntry represents a registered application managed by this agent.
type AppEntry struct {
	Name        string            `json:"name"`
	Version     int               `json:"version"`
	CreatedAt   string            `json:"created_at"`
	Command     string            `json:"command"`
	User        string            `json:"user,omitempty"`
	StopCommand string            `json:"stop_command,omitempty"`
	PIDFile     string            `json:"pid_file,omitempty"`
	Env         map[string]string `json:"env,omitempty"`
	AutoRestart bool              `json:"auto_restart"`
}

// AppRegistry manages registered applications on disk.
type AppRegistry struct {
	dir string
}

// NewAppRegistry creates an AppRegistry reading from the given directory.
func NewAppRegistry(dir string) *AppRegistry {
	return &AppRegistry{dir: dir}
}

// Register saves an app entry to disk.
func (r *AppRegistry) Register(name, command string, opts map[string]any) error {
	if err := os.MkdirAll(r.dir, 0755); err != nil {
		return fmt.Errorf("create registry dir: %w", err)
	}

	entry := AppEntry{
		Name:    name,
		Command: command,
	}
	if opts != nil {
		if v, ok := opts["user"].(string); ok {
			entry.User = v
		}
		if v, ok := opts["stop_command"].(string); ok {
			entry.StopCommand = v
		}
		if v, ok := opts["pid_file"].(string); ok {
			entry.PIDFile = v
		}
		if v, ok := opts["auto_restart"].(bool); ok {
			entry.AutoRestart = v
		}
	}
	entry.Version = 1

	data, err := json.MarshalIndent(entry, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal entry: %w", err)
	}

	path := filepath.Join(r.dir, name+".json")
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("write entry: %w", err)
	}
	slog.Info("app registered", "name", name, "path", path)
	return nil
}

// Unregister removes an app entry from disk.
func (r *AppRegistry) Unregister(name string) error {
	path := filepath.Join(r.dir, name+".json")
	if err := os.Remove(path); os.IsNotExist(err) {
		return nil
	}
	slog.Info("app unregistered", "name", name)
	return nil
}

// List returns all registered app entries.
func (r *AppRegistry) List() []AppEntry {
	entries, err := os.ReadDir(r.dir)
	if err != nil {
		return nil
	}
	var result []AppEntry
	for _, e := range entries {
		if !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(r.dir, e.Name()))
		if err != nil {
			continue
		}
		var entry AppEntry
		if err := json.Unmarshal(data, &entry); err != nil {
			continue
		}
		result = append(result, entry)
	}
	return result
}

// FindByPID checks if any registered app's PID file contains the given PID.
func (r *AppRegistry) FindByPID(pid int) *AppEntry {
	for _, entry := range r.List() {
		pidFile := entry.PIDFile
		if pidFile == "" {
			pidFile = fmt.Sprintf("/var/run/%s.pid", entry.Name)
		}
		data, err := os.ReadFile(pidFile)
		if err != nil {
			continue
		}
		var storedPID int
		if _, err := fmt.Sscanf(strings.TrimSpace(string(data)), "%d", &storedPID); err != nil {
			continue
		}
		if storedPID == pid {
			return &entry
		}
	}
	// Also match by cmdline pattern if PID file not found
	for _, entry := range r.List() {
		if entry.Command != "" {
			cmdName := filepath.Base(strings.Fields(entry.Command)[0])
			// caller should match against ps output separately
			_ = cmdName
		}
	}
	return nil
}

// IsRegisteredPID checks whether the given PID belongs to a registered app.
func (r *AppRegistry) IsRegisteredPID(pid int) bool {
	return r.FindByPID(pid) != nil
}
