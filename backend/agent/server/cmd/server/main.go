package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"opsflow/agent/server/internal/api"
	"opsflow/agent/server/internal/backend"
	"opsflow/agent/server/internal/config"
	"opsflow/agent/server/internal/file"
	"opsflow/agent/server/internal/ws"
)

var configPath = flag.String("config", "/etc/opsflow-agent/server.toml", "path to config file")

func main() {
	flag.Parse()

	cfg, err := config.LoadFromFile(*configPath)
	if err != nil {
		if cfg, err = config.LoadFromFile("./server.toml"); err != nil {
			slog.Error("failed to load config", "error", err)
			os.Exit(1)
		}
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

	slog.Info("agent server starting", "version", "1.0.0")
	slog.Info("configuration",
		"ws_endpoint", cfg.WS.Host+":"+itoa(cfg.WS.Port),
		"api_port", cfg.Server.Port,
		"django_base", cfg.Django.BaseURL,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start backend client (async batch write-back to Django)
	backendClient := backend.NewClient(&cfg.Django)
	backendClient.Start()

	// Start WebSocket listener
	wsServer := ws.NewServer(cfg)
	wsServer.Backend = backendClient
	go func() {
		if err := wsServer.Start(ctx); err != nil {
			slog.Error("WS server failed", "error", err)
			os.Exit(1)
		}
	}()

	// Start file coordinator
	fileCoord := file.NewCoordinator(cfg.Store.DataDir, wsServer,
			fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port))

	// Start REST API server (for Django to forward commands)
	apiHandler := api.NewHandler(wsServer, fileCoord, fileCoord.ChunkHandler())
	apiServer := &http.Server{
		Addr:    fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port),
		Handler: apiHandler.Router(),
	}
	go func() {
		slog.Info("REST API starting", "addr", apiServer.Addr)
		if err := apiServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("REST API failed", "error", err)
			os.Exit(1)
		}
	}()

	// Wait for shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	slog.Info("shutting down...")
	wsServer.Stop()
	slog.Info("server stopped")
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

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var buf [12]byte
	pos := len(buf)
	for i > 0 {
		pos--
		buf[pos] = byte('0' + i%10)
		i /= 10
	}
	return string(buf[pos:])
}

func init() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, nil)))
}
