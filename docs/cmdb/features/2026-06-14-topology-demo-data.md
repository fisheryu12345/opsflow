# CMDB 拓扑视图演示数据 + 全高布局

> 提交: 4ce858ff | 日期: 2026-06-14
> 涉及 App: cmdb
> 类型: 功能新增

---

## 背景

CMDB 拓扑视图（Tab 3）存在两个问题：
1. **无数据时完全空白** — 用户需要看到拓扑效果时，若 Neo4j 无数据或数据量过大，画布渲染效果很差
2. **画布高度固定** — `.cmdb-topo-body` 使用 `min-height: 560px`，不随视口高度自适应，需滚动才能看到全部

## 实现方案

### 演示数据

在 `index.vue` 中定义了 `DEMO_NODES`（21 个节点）和 `DEMO_EDGES`（20 条边），模拟一个完整的 Biz→Set→Module→Host 层级拓扑：

```
电商平台 (Biz)
  ├── 北京站 (Set) → API网关, 订单服务, MySQL主库, Redis缓存 → 对应 Host
  ├── 上海站 (Set) → API网关, 订单服务 → 对应 Host
  └── 广州站 (Set) → API网关, 商品服务 → 对应 Host
```

数据特点：
- 包含 3 种状态：`normal`（绿点）、`alarm`（红点）、`offline`（灰点）
- Host 节点包含完整属性（IP、OS、CPU、内存、磁盘、地域）供右键菜单展示
- 树形深度 3 层，默认第 2 层折叠

### 演示切换按钮

```vue
<el-button size="small" :type="topoMockMode ? 'warning' : 'default'" @click="toggleTopoMock">
  <el-icon><DataBoard /></el-icon> 演示
</el-button>
```

- 点击后替换 `store.topology` 为演示数据
- 使用 `:key="topoKey"` 驱动 TopologyCanvas 强制重建
- 再次点击切回真实数据

### CSS 全高布局

修改前：
```scss
.cmdb-topo-body { min-height: 560px; position: relative; }
```

修改后：
```scss
.cmdb-topo-body { flex: 1; min-height: 0; position: relative; }
```

与 DR 拓扑的 `.cmdb-topo-canvas` 布局对齐（`flex: 1; min-height: 0`），利用 flex 自动填满剩余垂直空间。

同层父容器也补全了 flex 属性链：
```scss
.cmdb-section.cmdb-section-topo { flex: 1; display: flex; flex-direction: column; min-height: 0; padding-bottom: 0; }
.cmdb-section-topo > .cmdb-topo-card { flex: 1; display: flex; flex-direction: column; min-height: 0; }
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/cmdb/index.vue` | 演示数据定义、toggle 按钮、CSS 全高布局 |
| `web/src/views/apps/cmdb/components/TopologyCanvas.vue` | 通过 `:key` 绑定重建 |

## 使用方式

打开 `/#/cmdb` → 拓扑视图 Tab → 点击工具栏"演示"按钮 → 查看 Biz→Set→Module→Host 层级树，右键查看节点详情

### 关联文档

- 相关架构文档: [G6 v5 迁移重构](architecture/2026-06-14-topology-g6-v5-migration-refactor.md)
- 相关配置变更: [G6 版本升级](config/2026-06-14-g6-upgrade-config.md)
