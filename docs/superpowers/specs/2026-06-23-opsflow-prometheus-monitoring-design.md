# Opsflow 自监控 — Prometheus 告警规则 + Grafana 看板

## 背景

Opsflow 平台目前完全缺乏自监控能力：

- 没有 `/metrics` 端点暴露应用指标
- docker-compose 中没有 Prometheus / Grafana
- `/readiness` 只检查 MySQL，不查 Redis 和 Neo4j
- Celery worker 挂了、CMDB 同步失败、磁盘满了——没有任何告警通知

当系统作为产品交付给客户时，自监控是必备能力。本 spec 为 Opsflow 增加内置 Prometheus 监控栈，覆盖 4 个关键告警场景。

## 架构

```
node-exporter ──→ 系统指标 (disk/cpu/mem)
Django /metrics ──→ 应用指标 (API 延迟/错误率/DB 池)
自定义 metrics ──→ 业务指标 (Celery 心跳/Neo4j 连通/同步状态)
     │
     ↓ (scrape 15s)
Prometheus Server → 告警规则评估 → AlertManager
                                       │
                              webhook POST
                                       ↓
                         Django /api/monitor/webhook/prometheus/
                                       │
                               Monitor 模块管线
                                  │       │
                                  ↓       ↓
                             Email 通知   界面告警列表

Grafana ──→ 4 个预置看板 (provisioning)
```

## 组件变更

### 新增 4 个 Docker 容器 (docker-compose.yml)

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| node-exporter | prom/node-exporter:latest | 9100 | 系统指标采集 |
| prometheus | prom/prometheus:latest | 9090 | 时序 DB + 告警 |
| alertmanager | prom/alertmanager:latest | 9093 | 告警路由 → webhook |
| grafana | grafana/grafana:latest | 3000 | 可视化看板 |

依赖：prometheus → node-exporter + backend；backend DSN 通过环境变量传递。

数据持久化：`prometheus_data` + `grafana_data` 两个 named volume。

### 新增配置文件

```
deploy/docker/
├── prometheus/
│   ├── prometheus.yml            # scrape config + 全局配置
│   └── rules/
│       ├── celery.yml            # Celery worker 离线
│       ├── neo4j.yml             # Neo4j 不可用
│       ├── cmdb_sync.yml         # 同步失败 + 同步停滞
│       └── disk.yml              # 磁盘空间 <5% critical / <10% warning
├── alertmanager/
│   └── alertmanager.yml          # webhook → backend:8000
├── grafana/
│   ├── datasources/
│   │   └── prometheus.yml        # Prometheus 数据源 (provisioning)
│   └── dashboards/
│       ├── dashboards.yml        # Dashboard provider (provisioning)
│       ├── opsflow-system-overview.json
│       ├── celery-monitoring.json
│       ├── cmdb-sync-status.json
│       └── neo4j-health.json
```

## Django 端变更

### 新增 `backend/monitoring/` App

独立于已有的 `monitor/` 告警模块。`monitor/` 是用来消费外部 Prometheus 数据的，`monitoring/` 是做 Opsflow **自身** 监控的。

```
backend/monitoring/
├── __init__.py
├── apps.py           # AppConfig, ready() 中启动 APScheduler
├── scheduler.py      # APScheduler 实例 + 3 个定时 job (60s 周期)
├── metrics.py        # Prometheus gauge 定义 (4 个)
└── checks.py         # 健康检查函数 (celery/neo4j/cmdb_sync)
```

### 自定义 Prometheus Gauge

```python
# metrics.py — 注册 4 个 gauge
opsflow_celery_worker_alive(queue)       # 1=存活, 0=离线
opsflow_neo4j_up                          # 1=可达, 0=不可达
opsflow_cmdb_sync_status(provider)        # 1=成功, 0=失败
opsflow_cmdb_sync_last_timestamp(provider) # 上次同步 Unix 时间戳
```

### 健康检查逻辑 (APScheduler 60s 循环)

```
scheduler.check_celery_workers()
  └─ celery inspect ping(timeout=2)
       worker 回应 → gauge=1
       无回应 → gauge=0

scheduler.check_neo4j()
  └─ cypher "RETURN 1"
       成功 → gauge=1
       失败 → gauge=0

scheduler.check_cmdb_sync()
  └─ CloudSyncLog.objects.latest(provider)
       status=success → gauge=1 + 更新时间戳
       status=failure → gauge=0
```

### django-prometheus 集成

```python
# settings.py
INSTALLED_APPS += ['django_prometheus', 'monitoring']
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # 最前
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',   # 最后
]

# urls.py
urlpatterns += [path('monitoring/', include('django_prometheus.urls'))]
```

自动暴露指标：
- `django_http_requests_total{method,status}` — 请求数
- `django_http_requests_latency_seconds{method,status}` — 延迟分布
- `django_db_query_duration_seconds` — SQL 查询耗时

### 预置自监控策略 (seed_reference.py)

4 条 MonitorStrategy + 对应 AlertAssignGroup：

| code | alertname | priority | 说明 |
|------|-----------|----------|------|
| self_celery_worker | CeleryWorkerDown | critical | Celery worker 离线 |
| self_neo4j | Neo4jUnavailable | critical | Neo4j 不可达 |
| self_cmdb_sync | CmdbSyncFailed | warning | CMDB 同步失败 |
| self_disk_space | DiskSpaceCritical | critical | 磁盘空间不足 |

管道匹配逻辑：webhook 进入 → 按 alertname 标签匹配策略 → dispatch → EmailNotify。

邮件接收人通过环境变量配置：`OPSFLOW_ALERT_EMAIL_TO`。

## 告警规则定义

### 1. Celery Worker 离线 (rules/celery.yml)

```yaml
- alert: CeleryWorkerDown
  expr: opsflow_celery_worker_alive < 1
  for: 3m
  labels: { severity: critical }
  annotations:
    summary: 'Celery worker {{ $labels.queue }} 离线超过 3 分钟'
    description: '队列 {{ $labels.queue }} 无 worker 响应心跳。'
```

### 2. Neo4j 不可用 (rules/neo4j.yml)

```yaml
- alert: Neo4jUnavailable
  expr: opsflow_neo4j_up < 1
  for: 1m
  labels: { severity: critical }
```

### 3. CMDB 同步失败 (rules/cmdb_sync.yml)

两条规则：执行报错 (CmdbSyncFailed) + 超过 24 小时未运行 (CmdbSyncStale)。

```yaml
- alert: CmdbSyncFailed
  expr: opsflow_cmdb_sync_status < 1
  for: 5m
  labels: { severity: warning }

- alert: CmdbSyncStale
  expr: (time() - opsflow_cmdb_sync_last_timestamp) > 86400
  for: 0m
  labels: { severity: warning }
```

### 4. 磁盘空间 (rules/disk.yml)

两段阈值：<5% critical / <10% warning，过滤 mountpoint="/"。

## Grafana 看板

| 看板 | 面板 |
|------|------|
| Opsflow 系统总览 | 告警状态摘要、磁盘使用率、API QPS、5xx 率、DB 连接池 |
| Celery 监控 | Worker 存活、队列深度、任务执行速率、失败率 |
| CMDB 同步状态 | 同步成功/失败轮次、上次同步时间、各 provider 状态 |
| Neo4j 健康 | 连通性、查询延迟、节点/关系数量趋势 |

每个看板 4-6 个面板，通过 Grafana Provisioning 自动加载。

## 涉及的文件

### 新增

| 文件 | 说明 |
|------|------|
| `deploy/docker/prometheus/prometheus.yml` | Prometheus 全局配置 |
| `deploy/docker/prometheus/rules/celery.yml` | Celery 告警规则 |
| `deploy/docker/prometheus/rules/neo4j.yml` | Neo4j 告警规则 |
| `deploy/docker/prometheus/rules/cmdb_sync.yml` | CMDB 同步告警规则 |
| `deploy/docker/prometheus/rules/disk.yml` | 磁盘告警规则 |
| `deploy/docker/alertmanager/alertmanager.yml` | AlertManager 配置 |
| `deploy/docker/grafana/datasources/prometheus.yml` | Grafana 数据源 |
| `deploy/docker/grafana/dashboards/dashboards.yml` | Grafana 看板提供者 |
| `deploy/docker/grafana/dashboards/opsflow-system-overview.json` | 系统总览看板 |
| `deploy/docker/grafana/dashboards/celery-monitoring.json` | Celery 看板 |
| `deploy/docker/grafana/dashboards/cmdb-sync-status.json` | 同步看板 |
| `deploy/docker/grafana/dashboards/neo4j-health.json` | Neo4j 看板 |
| `backend/monitoring/__init__.py` | 空 |
| `backend/monitoring/apps.py` | AppConfig + APScheduler 启动 |
| `backend/monitoring/scheduler.py` | APScheduler 实例 + 3 个 job |
| `backend/monitoring/metrics.py` | Prometheus gauge 定义 |
| `backend/monitoring/checks.py` | 3 个健康检查函数 |

### 修改

| 文件 | 变更 |
|------|------|
| `deploy/docker/docker-compose.yml` | +4 个服务 + 2 个 volume |
| `backend/application/settings.py` | +INSTALLED_APPS + MIDDLEWARE |
| `backend/application/urls.py` | +/monitoring/metrics 路由 |
| `backend/requirements.txt` | +django-prometheus |
| `backend/common/management/commands/seed_reference.py` | +4 条自监控策略 |

## 验证方式

1. `docker-compose up` 后访问 `http://localhost:9090` → Prometheus UI 已启动
2. `http://localhost:3000` → Grafana 登录 (admin/admin)，看到 4 个预置看板
3. `http://localhost:8000/monitoring/metrics` → 看到 `opsflow_celery_worker_alive` 等自定义指标
4. 手动停止 Celery worker：`docker stop celery` → 3 分钟后 Prometheus 告警 firing
5. 查看 AlertManager webhook 日志 → 确认请求已发到 Django
6. Django 告警列表中看到对应告警记录
7. POST 到邮箱确认收到告警邮件
