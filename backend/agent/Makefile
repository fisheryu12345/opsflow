# Agent Cross-platform Build Makefile
# Builds Agent Server and Agent for Linux, Windows, and AIX

VERSION := 1.0.0
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
BUILD_TIME := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
LDFLAGS := -ldflags="-X main.version=$(VERSION) -X main.commit=$(COMMIT) -X main.buildTime=$(BUILD_TIME)"

.PHONY: all clean deps server agent linux windows aix install

all: linux windows aix

# === Install Go dependencies ===
deps:
	cd server && go mod tidy
	cd agent && go mod tidy

# === Build all platforms ===
linux: server-linux agent-linux

windows: server-windows agent-windows

aix: agent-aix

# === Agent Server ===
server-linux:
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o build/server-linux-amd64 ./server/cmd/server

server-windows:
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o build/server-windows-amd64.exe ./server/cmd/server

# === Agent ===
agent-linux:
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o build/agent-linux-amd64 ./agent/cmd/agent

agent-windows:
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o build/agent-windows-amd64.exe ./agent/cmd/agent

agent-aix:
	GOOS=aix GOARCH=ppc64 go build $(LDFLAGS) -o build/agent-aix-ppc64 ./agent/cmd/agent

# === Development build (current platform) ===
dev:
	go build -o build/agent-server ./server/cmd/server
	go build -o build/agent ./agent/cmd/agent

# === Helper install targets ===
install-linux: agent-linux
	@echo "Installing agent-linux-amd64 to /usr/local/bin/agent ..."
	install -m 755 build/agent-linux-amd64 /usr/local/bin/agent
	@echo "Creating config directory /etc/agent ..."
	mkdir -p /etc/agent
	@echo "Copying example config ..."
	cp -n agent/agent.toml.example /etc/agent/agent.toml 2>/dev/null || true
	@echo "Done. Edit /etc/agent/agent.toml and run: agent --config /etc/agent/agent.toml"

# === Clean ===
clean:
	rm -rf build/

# === Package for release ===
package: all
	cd build && tar czf agent-server-linux-amd64-$(VERSION).tar.gz server-linux-amd64
	cd build && tar czf agent-linux-amd64-$(VERSION).tar.gz agent-linux-amd64 agent.toml.example
	cd build && zip agent-windows-amd64-$(VERSION).zip agent-windows-amd64.exe agent.toml.example
	cd build && tar czf agent-aix-ppc64-$(VERSION).tar.gz agent-aix-ppc64 agent.toml.example
