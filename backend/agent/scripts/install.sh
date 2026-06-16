#!/bin/bash
# opsflow-agent install.sh — installs the Agent binary and registers as a system service.
# Usage: curl -fsSL https://opsflow-agent.example.com/install.sh | bash -s -- --token=TKN-XXXX --server=opsflow-agent.example.com:8081

set -euo pipefail

BIN_NAME="opsflow-agent"
SERVICE_NAME="opsflow-agent"
BIN_DIR="/usr/local/bin"
CONFIG_DIR="/etc/opsflow-agent"
DATA_DIR="/var/lib/opsflow-agent"
LOG_DIR="/var/log/opsflow-agent"

# Defaults
TOKEN=""
SERVER="opsflow-agent.example.com:8081"
VERSION="latest"

parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --token=*) TOKEN="${arg#*=}" ;;
            --server=*) SERVER="${arg#*=}" ;;
            --version=*) VERSION="${arg#*=}" ;;
        esac
    done
}

detect_platform() {
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$os" in
        linux) os="linux" ;;
        aix) os="aix" ;;
        mingw*|msys*|cygwin*) os="windows" ;;
        *) echo "Unsupported OS: $os"; exit 1 ;;
    esac
    case "$arch" in
        x86_64|amd64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        ppc64|ppc64le) arch="ppc64" ;;
        *) echo "Unsupported arch: $arch"; exit 1 ;;
    esac

    echo "${os}-${arch}"
}

install_agent() {
    local platform="$1"
    local binary_url="https://${SERVER}/v1/agents/download/${VERSION}/${BIN_NAME}-${platform}"

    echo "Downloading ${BIN_NAME} binary for ${platform}..."
    mkdir -p "${BIN_DIR}" "${CONFIG_DIR}" "${DATA_DIR}" "${LOG_DIR}"

    curl -fsSL -o "${BIN_DIR}/${BIN_NAME}" "${binary_url}"
    chmod 755 "${BIN_DIR}/${BIN_NAME}"

    if [ ! -f "${CONFIG_DIR}/opsflow-agent.toml" ]; then
        curl -fsSL -o "${CONFIG_DIR}/opsflow-agent.toml" "https://${SERVER}/v1/agents/download/opsflow-agent.toml.example"
        sed -i "s|endpoint = .*|endpoint = \"wss://${SERVER}/ws\"|" "${CONFIG_DIR}/opsflow-agent.toml"
        if [ -n "$TOKEN" ]; then
            sed -i "s/token = .*/token = \"${TOKEN}\"/" "${CONFIG_DIR}/opsflow-agent.toml"
        fi
    fi

    echo "${BIN_NAME} installed to ${BIN_DIR}/${BIN_NAME}"
}

register_service() {
    case "$(uname -s)" in
        Linux)
            cat > /etc/systemd/system/${SERVICE_NAME}.service << SVC
[Unit]
Description=OpsFlow Agent
After=network.target

[Service]
Type=simple
ExecStart=${BIN_DIR}/${BIN_NAME} --config ${CONFIG_DIR}/opsflow-agent.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVC
            systemctl daemon-reload
            systemctl enable ${SERVICE_NAME}
            systemctl start ${SERVICE_NAME}
            echo "${SERVICE_NAME} service registered and started (systemd)"
            ;;
        AIX)
            echo "Registering ${BIN_NAME} with SRC..."
            mkssys -s ${SERVICE_NAME} -p ${BIN_DIR}/${BIN_NAME} -a "--config ${CONFIG_DIR}/opsflow-agent.toml" -u 0 -S -n 15 -f 9
            startsrc -s ${SERVICE_NAME}
            echo "${SERVICE_NAME} service registered (SRC)"
            ;;
        *)
            echo "Service registration not implemented for $(uname -s)"
            echo "Run manually: ${BIN_DIR}/${BIN_NAME} --config ${CONFIG_DIR}/opsflow-agent.toml"
            ;;
    esac
}

main() {
    parse_args "$@"
    local platform
    platform=$(detect_platform)
    install_agent "$platform"
    register_service
    echo "Installation complete."
}

main "$@"
