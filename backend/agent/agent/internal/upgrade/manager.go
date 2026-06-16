package upgrade

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"time"
)

// UpgradeManager handles agent self-upgrade.
type UpgradeManager struct {
	binDir    string
	dataDir   string
	client    *http.Client
	currentExe string
}

// NewUpgradeManager creates an upgrade manager.
func NewUpgradeManager(binDir, dataDir string) *UpgradeManager {
	exe, _ := os.Executable()
	return &UpgradeManager{
		binDir:     binDir,
		dataDir:    dataDir,
		client:     &http.Client{Timeout: 300 * time.Second},
		currentExe: exe,
	}
}

// Upgrade represents an upgrade task.
type Upgrade struct {
	UpgradeID        string `json:"upgrade_id"`
	DownloadURL      string `json:"download_url"`
	Checksum         string `json:"checksum"`
	Version          string `json:"version"`
	RollbackExe      string `json:"rollback_exe,omitempty"`
	RollbackChecksum string `json:"rollback_checksum,omitempty"`
}

// Perform performs the upgrade: download → verify → swap → restart.
func (um *UpgradeManager) Perform(upgrade *Upgrade) error {
	slog.Info("upgrade started", "version", upgrade.Version, "url", upgrade.DownloadURL)

	// Download new binary
	newBinary := filepath.Join(um.dataDir, "upgrades", fmt.Sprintf("agent-%s%s", upgrade.Version, exeSuffix()))
	if err := os.MkdirAll(filepath.Dir(newBinary), 0755); err != nil {
		return fmt.Errorf("create upgrade dir: %w", err)
	}

	if err := um.downloadFile(upgrade.DownloadURL, newBinary); err != nil {
		return fmt.Errorf("download: %w", err)
	}
	slog.Info("binary downloaded", "path", newBinary)

	// Verify checksum
	if err := um.verifyChecksum(newBinary, upgrade.Checksum); err != nil {
		os.Remove(newBinary)
		return fmt.Errorf("checksum: %w", err)
	}
	slog.Info("checksum verified")

	// Make executable
	if err := os.Chmod(newBinary, 0755); err != nil {
		return fmt.Errorf("chmod: %w", err)
	}

	// Backup current binary for rollback
	backupPath := filepath.Join(um.dataDir, "upgrades", fmt.Sprintf("agent-rollback-%d%s", time.Now().Unix(), exeSuffix()))
	if err := um.copyFile(um.currentExe, backupPath); err != nil {
		slog.Warn("backup failed, continuing", "error", err)
	} else {
		upgrade.RollbackExe = backupPath
		slog.Info("current binary backed up", "path", backupPath)
	}

	// Swap: rename new binary to current binary location
	if err := um.swapBinary(newBinary, um.currentExe); err != nil {
		return fmt.Errorf("swap binary: %w", err)
	}
	slog.Info("binary swapped, restarting...")

	// Restart process
	if err := um.restartSelf(); err != nil {
		return fmt.Errorf("restart: %w", err)
	}

	return nil
}

// Rollback restores the previous version.
func (um *UpgradeManager) Rollback(backupPath string) error {
	if backupPath == "" {
		return fmt.Errorf("no rollback binary available")
	}
	slog.Info("rolling back agent", "backup", backupPath)

	if err := um.copyFile(backupPath, um.currentExe); err != nil {
		return fmt.Errorf("restore backup: %w", err)
	}
	if err := os.Chmod(um.currentExe, 0755); err != nil {
		return err
	}
	return um.restartSelf()
}

func (um *UpgradeManager) downloadFile(url, dest string) error {
	resp, err := um.client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

func (um *UpgradeManager) verifyChecksum(path, expected string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	hasher := sha256.New()
	if _, err := io.Copy(hasher, f); err != nil {
		return err
	}
	actual := hex.EncodeToString(hasher.Sum(nil))
	if actual != expected {
		return fmt.Errorf("expected %s, got %s", expected, actual)
	}
	return nil
}

func (um *UpgradeManager) swapBinary(src, dst string) error {
	// On Windows, the running exe is locked, so we rename the current exe
	// and rename the new one into place, then rely on restart to clean up.
	tmpPath := dst + ".old"
	os.Remove(tmpPath)          // remove previous leftover
	os.Rename(dst, tmpPath)     // rename current → .old
	if err := os.Rename(src, dst); err != nil {
		// Restore on failure
		os.Rename(tmpPath, dst)
		return err
	}
	os.Remove(tmpPath) // cleanup old binary
	return nil
}

func (um *UpgradeManager) restartSelf() error {
	// Fork a new process with the same arguments
	argv := os.Args
	cmd := exec.Command(um.currentExe, argv[1:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start new process: %w", err)
	}

	// Exit the current process (the new one will take over)
	slog.Info("new process started, exiting", "pid", cmd.Process.Pid)
	os.Exit(0)
	return nil
}

func (um *UpgradeManager) copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return err
	}

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

func exeSuffix() string {
	if runtime.GOOS == "windows" {
		return ".exe"
	}
	return ""
}
