# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## `53363292`

> 提交日期: 2026-06-07 | 提交信息: refactor: complete project restructure cleanup

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/doc/*` (已删除) | 文档 | 旧文档已迁移到 `docs/architecture/`，清理残留 |
| `tools` (git 索引条目) | 杂项 | 移除残留的 `tools` 空条目（`backend/scripts/` → `backend/tools/` 重命名产生的） |
| 10 个 `.vue` 文件 | 前端 | 更新 import 路径以匹配组件子目录拆分 |
| `.vite/` | 缓存 | 删除 Vite 缓存目录 |

### 解决

- 完成项目结构重构的收尾清理，消除所有残留文件和索引异常

### 验证

- 改动类型: refactor
- 清理乱码: 有（`tools` 索引条目 + `.vite/` 缓存）
- 工作区状态: 干净 ✅

---

## `592db305` — `3030afef` — `70199fa7` — `99432840` — `de01d17c`

> 提交日期: 2026-06-07 | 项目全面代码结构重构

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `reference/` | 目录 | bk-cmdb, bk-itsm, bk-job, bk-sops, bamboo-engine 移入（.gitignore 排除） |
| `deploy/` | 目录 | docker-compose.yml, Dockerfile, nginx.conf 集中管理 |
| `backend/tools/` | 目录 | 原 `backend/scripts/` 重命名，避免与根目录 `scripts/` 冲突 |
| `docs/` | 目录 | 合并 5 处分散文档（`architecture/`、`design/`、`knowledge/`） |
| `.claude/skills/` | 配置 | 47 个技能从用户级迁移到项目级 |
| `.claude/.gitignore` | 配置 | 仅 `skills/` 可推送，`plans/`、`worktrees/`、`settings.local.json` 排除 |
| `CLAUDE.md` | 文档 | 路径更新（reference/、docs/、deploy/） |
| `OPSFLOW.md` | 文档 | 新增完整项目结构规范（目录职责、后端模板、前端拆分） |
| `opsflow/components/` | 前端 | 21 个组件拆入 8 个子目录（canvas/、dialogs/、panels/ 等） |
| 13 个 `.vue` / `.ts` 文件 | 前端 | 更新组件 import 路径 |

### 解决

- **问题：** 根目录杂乱（蓝鲸源码、部署配置混在一起）；文档分散；技能在用户级，其他开发者用不了；组件平铺 21 个文件
- **办法：** 5 阶段全量规范化，`git mv` 保持历史，分步提交逐步验证

### 验证

- 改动类型: refactor
- 后端测试: 264 passed ✅
- TypeScript: 无类型错误 ✅
- Vite: 241ms 启动，零 Sass 警告 ✅

---

## `a8a0805a`

> 提交日期: 2026-06-07 | 提交信息: fix: silence Sass legacy-js-api deprecation warning on Vite 8

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/vite.config.ts` | 配置 | `api: 'modern-compiler'` → `silenceDeprecations: ['legacy-js-api']` |

### 解决

- **问题/背景：** `api: 'modern-compiler'` 选项在 Vite 8 中被忽略，Sass legacy-js-api 警告依然出现。
- **办法：** 改用 sass 原生 `silenceDeprecations` 选项，兼容所有 Vite 版本的 Sass 警告静默。

### 验证

- 改动类型: fix
- 清理乱码: 有（`提交日期` 空文件 + `.vite/` 缓存目录）
- 工作区状态: 干净 ✅
- Vite 启动零 Sass 警告 ✅

---

## `8c2c3fa7`

> 提交日期: 2026-06-07 | 提交信息: refactor: migrate from Sass @import to @use — 消除全部 Sass 弃用警告

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/vite.config.ts` | 配置 | 添加 `scss.api: 'modern-compiler'` 消除 legacy-js-api 警告 |
| `web/src/**/*.scss` (18 文件) | 样式 | `@import` → `@use ... as *` 迁移 |
| `web/src/**/*.vue` (31 文件) | 样式 | `@import` → `@use ... as *` 迁移 |
| `opsflow-global.scss` | 样式 | 添加 `@forward` 确保变量穿透到 .vue `<style>` |

### 解决

- **问题/背景：** Dart Sass 2.0.0 将移除 `@import`，3.0.0 将移除 legacy JS API。开发服务器启动时产生约 50 行弃用警告，干扰正常日志查看。
- **办法：** 全局批量替换 `@import` → `@use ... as *`，同时配置 Vite 使用 `modern-compiler` API。

### 验证

- 改动类型: refactor
- 清理乱码: 无
- 工作区状态: 干净 ✅
- Vite 启动零 Sass 警告 ✅

---

## `f74f9ed8` — `deee0667` — `7277bf0b`

> 提交日期: 2026-06-07

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/signals/handlers.py` | 后端 | 新增 `_push_node_status_via_ws()` 函数；信号中调用 WS 推送 |
| `backend/opsflow/signals/state.py` | 后端 | 移除 `id_map` 查找，直接使用 `node_id` |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | 删除 `_build_id_map()`；Start/End 事件传入 X6 ID；合成网关使用可识别 ID |
| `backend/opsflow/core/flow_engine.py` | 后端 | 移除 `node_id_map` context 字段 |
| `backend/opsflow/core/layout/layout_adapter.py` | 后端 | 移除残留的 `node_id_map` 死代码 |
| `backend/opsflow/tests/test_gateway_signal.py` | 后端 | 新增 `TestWsNodeStatusPush` 测试类 |
| `backend/opsflow/tests/test_bamboo_builder.py` | 后端 | 更新测试，直接断言原始 ID |
| `backend/opsflow/tests/test_gateway_execution.py` | 后端 | 更新测试 |
| `backend/opsflow/tests/test_parallel_gateway.py` | 后端 | 更新测试 |
| `backend/opsflow/doc/debug/node-coloring-debug.md` | 文档 | 新增详细的节点着色全过程文档 |
| `web/package.json` | 前端 | X6 v3.1.7 + 移除全部插件包 |
| `web/src/utils/websocket.ts` | 前端 | `onmessage` 中自动分发 NODE_STATUS 到 mittBus |
| `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 前端 | 订阅 `nodeStatusChange`；修复日志 limit 参数名 |
| `web/src/views/apps/opsflow/components/MonitorCanvas.vue` | 前端 | 新增 `updateNodeStatus`；running 闪烁动画；边动画改为 animate API |
| `web/src/views/apps/opsflow/composables/useDesignCanvas.ts` | 前端 | 插件导入合并；修复 Selection rubberband 冲突 |
| `web/src/views/apps/opsflow/components/DesignCanvas.vue` | 前端 | 移除 3 行 CSS 导入 |
| `web/src/types/mitt.d.ts` | 前端 | 新增 `nodeStatusChange` 事件类型 |

### 解决

- **X6 版本废弃 (v2.19.1 → v3.1.7):** 合并 7 个插件包到核心包；移除外部 CSS 导入（v3 自动注入）；边动画改用 `animate()` + `iterations: Infinity`
- **画布无法拖拽:** `Selection` 配置加 `modifiers: 'shift'`，解冲突
- **节点着色滞后:** 新增 WebSocket 实时推送 `NODE_STATUS` 消息；websocket.ts 自动分发到 mittBus；10s 轮询保留为回退
- **Running 无反馈:** 0.6s CSS 快速闪烁动画（`ops-blink`）
- **冗余 ID 映射:** 删除 `_build_id_map()` 和 `node_id_map`；X6 ID 直接穿透
- **`layout_adapter.py` 残留:** 移除未使用的 `node_id_map` 局部变量

### 验证

- 后端 111 个测试全部通过 ✅
- 前端 TypeScript 类型检查无错误 ✅
- Vite 开发服务器正常启动 ✅
