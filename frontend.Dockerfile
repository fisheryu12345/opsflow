# ============================================================
# OPSflow Frontend Build Dockerfile
# ============================================================
# Usage (build the Vue app for production):
#   docker build -t opsflow-frontend -f frontend.Dockerfile .
#
# Output: /app/web/dist/  →  mount into nginx container
# ============================================================

FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY web/package.json web/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source and build
COPY web/ .
RUN npm run build

# ============================================================
# Production stage: only need dist/
FROM alpine:3.19

COPY --from=builder /app/dist /dist

CMD ["cp", "-r", "/dist/.", "/output/"]
