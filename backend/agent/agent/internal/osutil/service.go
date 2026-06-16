package osutil

import (
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"runtime"
)

const (
	serviceName  = "opsflow-agent"
	configPath   = "/etc/opsflow-agent/opsflow-agent.toml"
	serviceFile  = "/etc/systemd/system/opsflow-agent.service"
)

// InstallService registers the agent as a system service.
func InstallService() error {
	switch runtime.GOOS {
	case "linux":
		return installSystemd()
	case "windows":
		return installWinService()
	case "aix":
		return installSRC()
	default:
		return fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}
}

// UninstallService removes the agent system service.
func UninstallService() error {
	switch runtime.GOOS {
	case "linux":
		return uninstallSystemd()
	case "windows":
		return uninstallWinService()
	case "aix":
		return uninstallSRC()
	default:
		return fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}
}

func installSystemd() error {
	exe, _ := os.Executable()
	unit := fmt.Sprintf(`[Unit]
Description=OpsFlow Agent
After=network.target

[Service]
Type=simple
ExecStart=%s --config %s
Restart=always
RestartSec=10
User=%s

[Install]
WantedBy=multi-user.target
`, exe, configPath, serviceUser())

	slog.Info("installing systemd service", "service", serviceName)
	if err := os.WriteFile(serviceFile, []byte(unit), 0644); err != nil {
		return err
	}
	exec.Command("systemctl", "daemon-reload").Run()
	exec.Command("systemctl", "enable", serviceName).Run()
	exec.Command("systemctl", "start", serviceName).Run()
	return nil
}

func uninstallSystemd() error {
	exec.Command("systemctl", "stop", serviceName).Run()
	exec.Command("systemctl", "disable", serviceName).Run()
	return os.Remove(serviceFile)
}

func installWinService() error {
	slog.Warn("Windows service install requires admin")
	return nil
}

func uninstallWinService() error {
	slog.Warn("Windows service uninstall")
	return nil
}

func installSRC() error {
	slog.Warn("AIX SRC install requires root")
	return nil
}

func uninstallSRC() error {
	return nil
}

func serviceUser() string {
	if runtime.GOOS == "windows" {
		return "LocalSystem"
	}
	return "opsflow-agent"
}
