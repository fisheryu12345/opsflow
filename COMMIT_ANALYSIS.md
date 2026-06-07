# 提交记录分析

> 提交日期: 2026-06-07
> 提交 1: `f74f9ed8` — X6 v3 upgrade + real-time node coloring via WebSocket
> 提交 2: `deee0667` — remove outdated debug doc

---

## 解决的问题

### 1. X6 版本废弃 (v2.19.1 → v3.1.7)

**背景：** `@antv/x6 v2.19.1` 已标记为 deprecation（官方废弃），并且 7 个 `@antv/x6-plugin-*` 插件包需要与核心包版本匹配。维护两个版本系统成本高，且社区只维护 v3。

**解决方案：**
- 将所有插件包（Stencil、Snapline、Clipboard、Selection、MiniMap、Keyboard、Dnd）合并到核心 `@antv/x6: ^3.1.7` 中
- 移除手动 CSS 导入（`@antv/x6/dist/index.css` 等），v3 自动注入
- 边动画从 `transition()` + 递归 tick 重写为 `animate()` + `iterations: Infinity`

### 2. 流程编辑器画布无法拖拽

**背景：** X6 v3 升级后，画布拖拽（panning）和节点框选（rubberband）都监听拖拽事件，两者冲突导致画布无法平移。

**解决方案：** 将 `Selection` 插件配置改为 `{ rubberband: true, modifiers: 'shift' }`，按 Shift 拖拽才触发框选，普通拖拽正常平移画布。

### 3. 节点着色滞后于执行速度

**背景：** 早期节点着色完全依赖前端 10s 轮询 `GetExecutionDetail`。快速节点（如 ping_test < 1s）在轮询周期内已完成，颜色更新明显滞后。

**解决方案：** 增加 WebSocket 实时推送路径：

```
信号触发 → DB 持久化 → Channels WS 推送 → websocket.ts 分发
→ mittBus → ExecutionDetail.vue → MonitorCanvas.updateNodeStatus()
→ applyNodeColor() → X6 节点即时着色（<500ms）
```

10s 轮询作为回退机制保留，用于同步 Traces 表格和 Logs。

### 4. Running 节点无视觉反馈

**背景：** 执行中（running）的节点只变色没有动效，用户无法直观判断哪些节点正在执行。

**解决方案：** 添加 0.6s 快速闪烁 CSS 动画（`ops-blink`），running 状态自动激活，其他状态自动清除 CSS class。

### 5. 冗余 ID 映射层

**背景：** 架构中包含 `_build_id_map()` 函数生成 `node_id_map`，在信号处理中做 `id_map.get(node_id, node_id)` 的恒等映射。由于 `elements.py` 已直接将 X6 原始 ID 传给 bamboo-engine `Element(id=nid)`，整个映射层是无意义的。

**解决方案：** 移除 `_build_id_map()`、`node_id_map` context 字段、以及信号处理器中的所有 id_map 查找。X6 ID 直接穿透到 bamboo-engine。

---

## 涉及的文件

| 文件 | 类型 | 改动说明 |
|------|------|----------|
| `backend/opsflow/signals/handlers.py` | 后端 | 新增 `_push_node_status_via_ws()` 函数；信号中调用 WS 推送 |
| `backend/opsflow/signals/state.py` | 后端 | 移除 `id_map` 查找，直接使用 `node_id` |
| `backend/opsflow/core/pipeline_builder/__init__.py` | 后端 | 删除 `_build_id_map()`；Start/End 事件传入 X6 ID；合成网关使用可识别 ID |
| `backend/opsflow/core/flow_engine.py` | 后端 | 移除 `node_id_map` context 字段 |
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

---

## 验证

- 后端 111 个测试全部通过
- 前端 TypeScript 类型检查无错误（仅 TS 配置弃用警告）
- Vite 开发服务器正常启动（<500ms）
- 所有修改文件不包含密钥、凭据或 .env 文件
