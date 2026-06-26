# Opsflow — 待办事项与开发路线图

> 记录日期: 2026-06-23 | 后续在完成任务后更新

---

## Phase 0 — 安全底线 + 部署可跑（预计 1 周）

- [ ] **Nginx 配置文件** — `deploy/nginx/nginx.conf` 不存在，docker-compose 启动失败
- [ ] **SECRET_KEY + 数据库密码环境变量化** — 现硬编码在 `conf/env_base.py` 和 `settings.py`
- [ ] **CORS_ORIGIN_ALLOW_ALL = False** — 现为 True，任何网站可调用 API
- [ ] **前端 error boundary** — 无 `onErrorCaptured`，组件报错整个页面白屏
- [ ] **Sentry 接入** — 无错误上报，生产问题只能盲猜
- [ ] **docker-compose 全流程跑通验证** — `git clone → docker compose up` 能完整看到登录页

## Phase 1 — 工程化 + 测试 + 加固（预计 3 周）

- [ ] **GitHub Actions CI** — 无 CI，改动无验证
- [ ] **登录频率限制 + 验证码** — 暴力破解无防护
- [ ] **核心模块测试** — cmdb、opsflow 至少 30% 覆盖率（现为 0）
- [ ] **修复 6 处 bare except** — 生产环境静默吞异常
- [ ] **数据库自动备份脚本** — 无备份策略
- [ ] **环境变量文档 + .env.example** — 部署所需环境变量无文档

## Phase 2 — 业务补齐（预计 6 周）

- [ ] **K8s CMDB 模型 + ACK 同步** — 企业必问场景，当前完全缺失
- [ ] **Agent 自动安装流程完善** — 主机批量纳管
- [ ] **网络设备模型** — Router/Switch/Firewall 纳管
- [ ] **CMDB 导入导出** — Excel/CSV 导入有界面无后端
- [ ] **Prometheus /metrics 端点** — 应用自监控，便于 SRE 团队接管
- [ ] **Neo4j 数据校验 + 迁移机制** — 图数据库无 schema 校验
- [ ] **其他 CMDB 同步实现** — 腾讯云、华为云（当前仅阿里云）

## Phase 3 — 监控 + 文档 + 打磨（预计 6 周）

- [ ] **Prometheus + Grafana 内嵌 docker-compose** — specs 已设计，待实施
- [ ] **4 条告警规则** — Celery worker 离线、Neo4j 不可用、CMDB 同步失败、磁盘空间
- [ ] **Grafana 预置看板** — 系统总览、Celery 监控、CMDB 同步、Neo4j 健康
- [ ] **监控模块自监控策略** — seed_reference 中预置策略
- [ ] **/readiness 加固** — 补充 Redis + Neo4j 连通性检查
- [ ] **部署文档 + 架构文档** — 交付标配产出
- [ ] **运维手册** — 升级、备份、扩容、排障标准流程
- [ ] **前端 i18n 全面检查** — 多页面切换英文仍有中文残留
- [ ] **前端测试（核心页面）** — 保证重构不改坏
- [ ] **API 文档自动化完善** — drf-spectacular 有了但 description 大量缺省
- [ ] **demo data 脚本** — `python manage.py seed_demo` 即可看到完整数据

## 近期修复记录

| 日期 | 内容 | 完成 |
|------|------|------|
| 2026-06-23 | interhub 页面 i18n 修复（+25 key，修复模板+script 硬编码） | ✅ |
| 2026-06-23 | CMDB 实例表列标签 i18n（DynamicTable 列名翻译 + os_version 字段） | ✅ |
| 2026-06-23 | 阿里云 ECS 创建后自动启动（已回退，保留独立 start_instance 插件） | ✅ |
| 2026-06-23 | 自监控 Prometheus 方案设计（spec 已写，未实施） | 📄 |
