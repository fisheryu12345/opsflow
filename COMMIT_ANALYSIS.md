# Commit Analysis Log

<!-- 每次提交在最前面插入新条目，时间倒序排列 -->

## `d2cf3d83`

> 提交日期: 2026-06-10 | 提交信息: refactor: unify SCSS architecture and standardize button styles — SCSS 架构统一 & 按钮风格规范

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `OPSFLOW.md` | 文档 | 更新 SCSS 规范（$g-*/@use styles/global）和按钮风格规范 |
| `web/src/styles/_tokens.scss` | 样式 | **新文件** — 全局设计令牌（$g-* 变量，合并 sys 和 of 两套） |
| `web/src/styles/_mixins.scss` | 样式 | **新文件** — 全局 mixin（g-hover-lift/g-dialog-header 等） |
| `web/src/styles/_components.scss` | 样式 | **新文件** — 全局 class（.g-card/.g-fade-in-up 等） |
| `web/src/styles/global.scss` | 样式 | **新文件** — 统一入口（@forward 三个 partials） |
| `web/src/styles/opsflow-*.scss` | 样式 | **删除** — 旧两套 SCSS 系统（opsflow-global/opsflow-variables） |
| `web/src/views/system/styles/system-global.scss` | 样式 | **删除** — 旧 system-global SCSS |
| `web/` (70+ .vue 文件) | 前端 | 全部 @use 路径改为 `/@/styles/global`；$sys-*/$of-* → $g-*；.sys-*/.of-* → .g-*；mixin 同步改名 |
| `web/` (44 .vue 文件) | 前端 | 按钮规范统一：行内 text type="primary" → text；弹窗移除 size="small"；primary 加图标；工具栏加图标 |

### 解决

- **问题/背景：** 项目有两套并行的 SCSS 系统（opsflow-* 45 文件 + sys-* 7 文件），值几乎相同但命名不同，开发者选择困难、UI 有不一致、维护需改两处。同时按钮风格不统一（大小混用、79% 无图标、行内按钮写法混乱）
- **办法：** 一次性合并为三层架构（tokens + mixins + components），前缀统一 g-；通过自动化脚本批量重命名 70+ 文件的变量/class/mixin；按 OPSFLOW.md 规范统一按钮大小/类型/图标

### 验证

- 改动类型: refactor
- 清理乱码: 有（fix_buttons.py/fix_buttons_v2.py 临时脚本）
- 工作区状态: 干净 ✅
- Vite build 零错误 ✅ (32.92s)

---

## `99c70038`

> 提交日期: 2026-06-09 | 提交信息: chore: remove deprecated USE_L10N setting — 移除 Django 5.0 已废弃的 USE_L10N

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 配置 | 删除 USE_L10N = True 死代码（Django 5.0 已移除） |

### 解决

- **问题/背景：** USE_L10N 在 Django 5.0 已被移除，当前 Django 5.2.15 中该设置不再生效，是死代码
- **办法：** 直接删除该行

### 验证

- 改动类型: chore
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `1094e415`

> 提交日期: 2026-06-09 | 提交信息: feat: enable USE_TZ=True and refactor opsflow SCSS imports — 激活时区支持及样式文件迁移

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 配置 | USE_TZ = False → True，激活 Django 时区感知 |
| `backend/opsflow/core/scheduler_service.py` | 后端 | 删除 _naive() 时区剥离函数，4 处调用直接使用 aware datetime |
| `backend/opsflow/core/flow_engine.py` | 后端 | started_at/ended_at 赋值改用 timezone.now()（3 处） |
| `backend/opsflow/signals/handlers.py` | 后端 | ended_at 赋值改用 timezone.now()（3 处） |
| `backend/opsflow/signals/timeout.py` | 后端 | 超时 deadline 计算改用 timezone.now() + timedelta |
| `backend/opsflow/core/node_timeout_strategy.py` | 后端 | 超时 deadline 计算改用 timezone.now() + timedelta |
| `backend/opsflow/views/dashboard_views/stats.py` | 后端 | 删除 now_naive 兼容代码，直接使用 timezone.now() |
| `backend/opsagent/views/run.py` | 后端 | session_id/ended_at 改用 timezone.now()（3 处） |
| `backend/iam/views.py` | 后端 | reviewed_at 赋值改用 timezone.now()（2 处） |
| `backend/dvadmin/system/views/login.py` | 后端 | 验证码过期比较改用 timezone.now() |
| `backend/common/management/commands/add_mock_neo4j.py` | 后端 | datetime.utcnow() → timezone.now() |
| `backend/opsflow/management/commands/fix_timezone_data.py` | 后端 | **新文件** — 数据迁移命令，对现有 naive 数据减 8h 转换 |
| `web/scripts/migrate_opsflow_styles.py` | 脚本 | **新文件** — SCSS 样式迁移助手 |
| `web/src/styles/opsflow-global.scss` | 样式 | **迁移** — 从 opsflow/styles/ 移至全局 styles/ |
| `web/src/styles/opsflow-variables.scss` | 样式 | **迁移** — 从 opsflow/styles/ 移至全局 styles/ |
| `web/` (44 个 .vue 文件) | 前端 | @use 导入路径更新为 `../../../styles/` 等匹配新路径 |

### 解决

- **问题/背景：** 项目 USE_TZ=False 导致所有 datetime 为 naive 值，Django 5.2 对 naive datetime 将触发 RuntimeWarning；多处存在 _naive() 补偿代码。同时 opsflow SCSS 文件位于 views/apps/opsflow/styles/ 下，跨组件引用路径混乱
- **办法：** 分两阶段：(1) 时区：settings.py 切换 + 删除 _naive() + 10 个文件中所有 datetime.now() 替换为 timezone.now() + 创建 fix_timezone_data.py 数据迁移命令；(2) 样式：将 SCSS 文件迁移到 web/src/styles/，全部 44 个 Vue 组件 @use 路径重写

### 验证

- 改动类型: feat
- 清理乱码: 有（`self.image_code.expiration` 0 字节 + `web/resolves` 0 字节）
- 工作区状态: 干净 ✅

---

## `a16dfd3c`

> 提交日期: 2026-06-09 | 提交信息: chore: clean up unused dependencies from requirements — 移除 tqsdk、influxdb、sqlalchemy

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/requirements.txt` | 配置 | 移除未使用的 tqsdk、tqsdk-ctpse、tqsdk-sm、influxdb、influxdb-client、sqlalchemy |
| `backend/requirements_prod.txt` | 配置 | 同步移除，修复 `<blank>` 占位符文本 |

### 解决

- **问题/背景：** requirements.txt 中残留了大量非 opsflow 项目使用的 Python 依赖（tqsdk 期货交易、influxdb 时序数据库、sqlalchemy ORM），增加部署体积和依赖冲突风险
- **办法：** 逐包核查代码引用，确认无 import 后从 requirements 移除并从 venv 卸载

### 验证

- 改动类型: chore
- 清理乱码: 有 — 修复了 Edit 操作遗留的 `<blank>` 占位符文本
- 工作区状态: 干净 ✅

---

## `77c26c51`

> 提交日期: 2026-06-08 | 提交信息: docs: add debug-doc-writer skill and exclusive gateway debug documentation

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `.claude/skills/debug-doc-writer/SKILL.md` | 配置 | 新增 debug-doc-writer 技能，自动提取调试排障过程生成结构化 MD 文档 |
| `docs/opsflow/debug/2026-06-08-exclusive-gateway-condition-output.md` | 文档 | 新增排他网关条件评估与节点输出显示调试全记录，涵盖时序竞态/数据注入/前端显示 3 个根因 |

### 解决

- **问题/背景：** 需要规范化记录调试排障过程到结构化文档；之前 commit 24691761 的调试分析需生成可复用的 debug 文档
- **办法：** 创建 debug-doc-writer 技能（含完整的工作流模板），依据提交历史重新整理排他网关条件评估与节点输出显示的根因分析、解决方案和验证方法

### 验证

- 改动类型: docs
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `24691761`

> 提交日期: 2026-06-08 | 提交信息: feat: implement exclusive gateway condition evaluation and output display

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/opsflow/core/plugin_service_adapter.py` | 后端 | 重写 `_promote_result` → `_promote_results`，支持排他网关条件变量注入 ContextValue 表，同时将 outputs 写入 execution.context |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | build_bamboo_pipeline 返回 auto_vars 映射；传递 execution_id；修复 NodeOutput 变量注入 key 格式 |
| `backend/opsflow/core/pipeline_builder/elements.py` | 后端 | `_create_element` 接收 execution_id 注入到每个节点 inputs |
| `backend/opsflow/core/flow_engine.py` | 后端 | 接收 auto_vars 并存入 execution context |
| `backend/opsflow/plugins/common/test_print_time.py` | 后端 | 添加 test1 随机输出(1-10)和 get_output_schema |
| `backend/opsflow/signals/trace.py` | 后端 | `_capture_node_outputs` 从 execution.context 读取，避开 bamboo-engine 的 ExecutionData 时序问题 |
| `backend/opsflow/serializers.py` | 后端 | get_trace_summary 包含 outputs 字段 |
| `backend/opsflow/core/node_dispatcher.py` | 后端 | get_trace 查询包含 outputs 字段 |
| `backend/application/settings.py` | 配置 | apscheduler 日志降级到 WARNING |
| `web/` (5 个文件) | 前端 | 条件下拉显示节点.变量名；PropertyPanel 通过 getGraphData 获取节点；边 label 持久化；日志/输出样式浅色主题 |

### 解决

- **问题/背景：** 排他网关条件表达式 `${_gwcond_node_1_test1} > 5` 评估失败（context 为空），节点 outputs 无法显示（No outputs）。根因：1) auto_vars 映射未被返回和持久化；2) bamboo-engine 的 ExecutionData 时序问题（信号在持久化前触发）
- **办法：** pipeline builder 返回 auto_vars 映射存入 execution.context；_promote_results 写入 ContextValue 表（格式化 ${} 匹配引擎 ref）和 execution.context['_node_outputs']；trace 从后者读取 outputs；前端的边 label 持久化修复、条件变量下拉显示节点名

### 验证

- 改动类型: feat
- 清理乱码: 有（`backend/None` 0 字节垃圾文件）
- 工作区状态: 干净 ✅

---

## `3b3666ba`

> 提交日期: 2026-06-07 | 提交信息: fix: correct remaining cross-subdirectory component imports in Vue components

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue` | 前端 | 修复 5 个跨子目录组件引用（./ → ../panels/, ../badges/, ../common/, ../dialogs/） |
| `web/src/views/apps/opsflow/components/gates/ConditionRow.vue` | 前端 | VariablePicker 引用路径 ./ → ../panels/ |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 前端 | ConditionDialog 引用路径 ./ → ../gates/ |

### 解决

- **问题/背景：** 上一轮修复（../ → ../../）遗漏了 components/canvas/、components/gates/ 和 components/panels/ 中跨子目录引用的本地组件（./PropertyPanel 实际在 panels/、./ConditionDialog 实际在 gates/ 等）
- **办法：** 对 3 个文件中 7 处 ./ 跨子目录引用修正为正确的相对路径

### 验证

- 改动类型: fix
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

## `f01b6b1c`

> 提交日期: 2026-06-07 | 提交信息: fix: correct Vue component import paths and simplify DB_HOST config

### 改动

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/application/settings.py` | 后端 | DB_HOST 固定为 127.0.0.1，去掉动态 IP 检测逻辑 |
| `web/src/views/apps/opsflow/components/*/` (20 个 .vue 文件) | 前端 | 修复组件子目录中的相对导入路径（`../` → `../../`），涉及 js import（api/stores/composables/utils）和 scss @use（styles/） |

### 解决

- **问题/背景：** 前端组件目录结构拆分为二级子目录（如 `components/canvas/`、`components/dialogs/` 等）后，`../` 路径错误地指向了 `components/` 而非 `opsflow/`
- **办法：** 将所有 `components/*/` 子目录中的 `from '../xxx/'` 和 `@use '../styles/'` 改为 `from '../../xxx/'` 和 `@use '../../styles/'`

### 验证

- 改动类型: fix
- 清理乱码: 无
- 工作区状态: 干净 ✅

---

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
