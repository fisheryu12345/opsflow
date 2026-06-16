package config

import (
	"fmt"
	"os"

	"github.com/BurntSushi/toml"
)

// Config holds all configuration for the Agent Server.
type Config struct {
	Server ServerConfig `yaml:"server"`
	WS     WSConfig     `yaml:"ws"`
	Store  StoreConfig  `yaml:"store"`
	Django DjangoConfig `yaml:"django"`
	Log    LogConfig    `yaml:"log"`
}

type ServerConfig struct {
	Host    string `yaml:"host"`
	Port    int    `yaml:"port"`
	TLSKey  string `yaml:"tls_key,omitempty"`
	TLSCert string `yaml:"tls_cert,omitempty"`
}

type WSConfig struct {
	Host            string `yaml:"host"`
	Port            int    `yaml:"port"`
	Path            string `yaml:"path"`
	MaxConn         int    `yaml:"max_conn"`
	HeartbeatCheck  int    `yaml:"heartbeat_check"` // seconds
	DefaultInterval int    `yaml:"default_interval"` // heartbeat interval for agents
}

type StoreConfig struct {
	DataDir    string `yaml:"data_dir"`
	BoltDBPath string `yaml:"boltdb_path"`
}

type DjangoConfig struct {
	BaseURL    string `yaml:"base_url"`
	APIToken   string `yaml:"api_token"`
	BatchSize  int    `yaml:"batch_size"`
	BatchEvery int    `yaml:"batch_every"` // seconds
}

type LogConfig struct {
	Level      string `yaml:"level"`
	File       string `yaml:"file"`
	MaxSize    int    `yaml:"max_size"`
	MaxBackups int    `yaml:"max_backups"`
}

// DefaultConfig returns a configuration with sensible defaults.
func DefaultConfig() *Config {
	return &Config{
		Server: ServerConfig{
			Host: "0.0.0.0",
			Port: 18080,
		},
		WS: WSConfig{
			Host:            "0.0.0.0",
			Port:            8081,
			Path:            "/ws",
			MaxConn:         10000,
			HeartbeatCheck:  90,
			DefaultInterval: 30,
		},
		Store: StoreConfig{
			DataDir:    "/var/lib/opsflow-agent/server",
			BoltDBPath: "/var/lib/opsflow-agent/server/db/agent-server.db",
		},
		Django: DjangoConfig{
			BaseURL:    "http://localhost:8000",
			APIToken:   "",
			BatchSize:  50,
			BatchEvery: 2,
		},
		Log: LogConfig{
			Level:      "info",
			File:       "/var/log/opsflow-agent/server.log",
			MaxSize:    100,
			MaxBackups: 7,
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
