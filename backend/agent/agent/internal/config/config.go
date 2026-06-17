package config

import (
	"fmt"
	"os"

	"github.com/BurntSushi/toml"
)

// Config holds all configuration for the Agent daemon.
type Config struct {
	Agent   AgentConfig   `yaml:"agent"`
	Server  ServerConfig  `yaml:"server"`
	Heartbeat HeartbeatConfig `yaml:"heartbeat"`
	Collector CollectorConfig `yaml:"collector"`
	Subproc  SubprocConfig   `yaml:"subproc"`
	Upgrade  UpgradeConfig   `yaml:"upgrade"`
	Log      LogConfig       `yaml:"log"`
}

type AgentConfig struct {
	AgentID string `yaml:"agent_id"`
	Token   string `yaml:"token"`
	DataDir string `yaml:"data_dir"`
}

type ServerConfig struct {
	Endpoint         string `yaml:"endpoint"`
	APIEndpoint      string `yaml:"api_endpoint"`
	BackupEndpoint   string `yaml:"backup_endpoint"`
	FingerprintVerify bool  `yaml:"fingerprint_verify"`
}

type HeartbeatConfig struct {
	Interval int `yaml:"interval"`
	Jitter   int `yaml:"jitter"`
}

type CollectorConfig struct {
	Enable   bool     `yaml:"enable"`
	Interval int      `yaml:"interval"`
	AppUsers []string `yaml:"app_users"`
}

type SubprocConfig struct {
	Enable  bool   `yaml:"enable"`
	BinDir  string `yaml:"bin_dir"`
	DataDir string `yaml:"data_dir"`
}

type UpgradeConfig struct {
	AutoUpgrade    bool `yaml:"auto_upgrade"`
	CheckInterval  int  `yaml:"check_interval"`
}

type LogConfig struct {
	Level      string `yaml:"level"`
	File       string `yaml:"file"`
	MaxSize    int    `yaml:"max_size"`
	MaxBackups int    `yaml:"max_backups"`
	MaxAge     int    `yaml:"max_age"`
	Compress   bool   `yaml:"compress"`
}

// DefaultConfig returns a configuration with sensible defaults.
func DefaultConfig() *Config {
	return &Config{
		Agent: AgentConfig{
			DataDir: "/var/lib/opsflow-agent",
		},
		Server: ServerConfig{
			Endpoint:   "wss://opsflow-agent.example.com:8081/ws",
			FingerprintVerify: true,
		},
		Heartbeat: HeartbeatConfig{
			Interval: 30,
			Jitter:   5,
		},
		Collector: CollectorConfig{
			Enable:   true,
			Interval: 30,
		},
		Subproc: SubprocConfig{
			Enable:  true,
			BinDir:  "/var/lib/opsflow-agent/bin",
			DataDir: "/var/lib/opsflow-agent/data",
		},
		Upgrade: UpgradeConfig{
			AutoUpgrade:   true,
			CheckInterval: 3600,
		},
		Log: LogConfig{
			Level:      "info",
			File:       "/var/log/opsflow-agent/agent.log",
			MaxSize:    100,
			MaxBackups: 7,
			MaxAge:     30,
			Compress:   true,
		},
	}
}

// LoadFromFile loads configuration from a YAML file.
func LoadFromFile(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config file: %w", err)
	}
	cfg := DefaultConfig()
	if err := toml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config file: %w", err)
	}
	return cfg, nil
}
