# ============================================================
# OPSflow Backend Dockerfile
# ============================================================
# Usage:
#   docker build -t opsflow-backend -f backend/Dockerfile .
# ============================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend code
COPY backend/ .

# Copy bamboo engine
COPY bamboo-engine-master/ /app/bamboo-engine-master/

# Expose Django ASGI port
EXPOSE 8000

# Entry point
COPY backend/docker_start.sh /docker_start.sh
RUN chmod +x /docker_start.sh

CMD ["/docker_start.sh"]
