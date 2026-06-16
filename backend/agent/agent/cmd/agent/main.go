package main

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"opsflow/agent/agent/internal/config"
	"opsflow/agent/agent/internal/core"
	"opsflow/agent/agent/internal/osutil"
)

var (
	configPath  = flag.String("config", "/etc/opsflow-agent/opsflow-agent.toml", "path to config file")
	mode        = flag.String("mode", "agent", "agent | gateway")
	installSvc  = flag.Bool("install", false, "install as system service")
	uninstallSvc = flag.Bool("uninstall", false, "uninstall system service")
)

func main() {
	flag.Parse()

	cfg, err := config.LoadFromFile(*configPath)
	if err != nil {
		slog.Error("failed to load config", "path", *configPath, "error", err)
		os.Exit(1)
	}

	// Setup logging
	opts := &slog.HandlerOptions{Level: parseLogLevel(cfg.Log.Level)}
	if cfg.Log.File != "" {
		f, err := os.OpenFile(cfg.Log.File, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err == nil {
			slog.SetDefault(slog.New(slog.NewJSONHandler(f, opts)))
			defer f.Close()
		}
	} else {
		slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, opts)))
	}

	// Handle service install/uninstall
	if *installSvc {
		if err := installService(); err != nil {
			slog.Error("install service failed", "error", err)
			os.Exit(1)
		}
		return
	}
	if *uninstallSvc {
		if err := uninstallService(); err != nil {
			slog.Error("uninstall service failed", "error", err)
			os.Exit(1)
		}
		return
	}

	slog.Info("agent starting", "version", "1.0.0", "mode", *mode)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	if *mode == "gateway" {
		gw := core.NewGateway(cfg)
		go func() {
			if err := gw.Start(ctx); err != nil {
				slog.Error("gateway failed", "error", err)
				os.Exit(1)
			}
		}()
		<-sigCh
		slog.Info("gateway shutting down...")
		gw.Stop()
	} else {
		agent := core.NewAgent(cfg)
		if err := agent.Start(ctx); err != nil {
			slog.Error("agent failed", "error", err)
			os.Exit(1)
		}
		<-sigCh
		slog.Info("shutting down...")
		agent.Stop()
	}
}

func parseLogLevel(level string) slog.Level {
	switch level {
	case "debug":
		return slog.LevelDebug
	case "info":
		return slog.LevelInfo
	case "warn":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

func installService() error {
	return osutil.InstallService()
}

func uninstallService() error {
	return osutil.UninstallService()
}

func init() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, nil)))
}
